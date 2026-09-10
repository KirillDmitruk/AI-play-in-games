"""Non-blocking orchestration. All game state mutations happen on the UI thread."""
from collections import deque
from dataclasses import asdict, dataclass
import time
from agent import api_key
from game import SnakeGame
from records import Memory, Recorder
from worker import RequestWorker


@dataclass
class Stats:
    requests: int = 0
    tokens: int = 0
    input: int = 0
    output: int = 0
    thought: int = 0
    unknown_usage: int = 0
    errors: int = 0
    last_seconds: float = 0

    def receive(self, reply):
        self.last_seconds = reply.seconds
        if not reply.usage:
            self.unknown_usage += 1
        for field, key in (('tokens', 'total'), ('input', 'input'), ('output', 'output'), ('thought', 'thought')):
            setattr(self, field, getattr(self, field) + reply.usage.get(key, 0))
        if reply.error:
            self.errors += 1


class Controller:
    def __init__(self, settings, directory, manual=False, seed=None, worker=None):
        self.settings, self.directory, self.manual, self.seed = settings, directory, manual, seed
        self.worker = worker or RequestWorker()
        self.memory = Memory(directory / 'memory.json') if settings.memory and not manual else None
        self.stats = Stats()
        self.best = 0
        self.episode = 0
        self.speed = settings.steps_per_second
        self.recorder = None
        self.storage_failed = False
        self._new_episode()

    def _log(self, event, **data):
        if self.storage_failed:
            return
        try:
            self.recorder.write(event, **data)
        except OSError:
            self.storage_failed = True
            self.paused = True
            self.error = 'Cannot write recording; close app and check disk space/permissions'

    def _new_episode(self):
        self.episode += 1
        self.game = SnakeGame(seed=self.seed, max_steps=self.settings.max_steps,
                              max_idle_steps=self.settings.max_idle_steps)
        self.plan = deque()
        self.history = deque(maxlen=8)
        self.episode_requests = 0
        self.retries = 0
        self.retry_at = 0
        self.paused = False
        self.error = ''
        self.last_action = '-'
        self.last_step = time.monotonic()
        self.single_step = False
        self.ended = self.reflected = False
        self.note = ''
        lessons = self.memory.lessons if self.memory else []
        self.recorder = Recorder(self.directory, self.settings, self.game.snapshot(),
                                 'manual' if self.manual else 'gemini', self.episode, lessons)

    def budget_reason(self):
        if self.stats.requests >= self.settings.max_session_requests:
            return 'session_request_limit'
        if self.episode_requests >= self.settings.max_episode_requests:
            return 'episode_request_limit'
        if self.stats.tokens >= self.settings.max_session_tokens:
            return 'session_token_limit'
        return None

    def _start_request(self, kind='plan'):
        if self.storage_failed:
            return
        if not api_key():
            self.error = 'Set GEMINI_API_KEY, then restart the app. Manual: python game.py'
            self.paused = True
            return
        reason = self.budget_reason()
        if reason:
            if not self.game.done:
                self.game.finish(reason)
            self.note = reason
            return
        try:
            self.worker.start(self.settings, self.game.snapshot(),
                              self.memory.lessons if self.memory else [], kind, list(self.history))
        except Exception:
            self.error = 'Could not start request process'
            self.paused = True
            return
        self.stats.requests += 1
        self.episode_requests += 1
        self._log('request_start', kind=kind, number=self.episode_requests, state=self.game.snapshot())

    def _receive(self, reply):
        self.stats.receive(reply)
        self._log('response', **asdict(reply))
        if reply.kind == 'reflection':
            self.note = 'Memory review failed' if reply.error else 'Memory review complete'
            if not reply.error and self.memory:
                try:
                    self.memory.add(reply.lessons)
                except OSError:
                    self.note = 'Could not save memory'
            return
        if reply.error:
            self.plan.clear()
            self.error = reply.error
            if reply.retryable and self.retries < self.settings.max_retries:
                self.retries += 1
                self.retry_at = time.monotonic() + self.settings.retry_delay_seconds * 2 ** (self.retries - 1)
                self.note = f'Retry {self.retries}/{self.settings.max_retries} scheduled'
            else:
                self.paused = True
                self.retry_at = 0
            return
        self.error = ''
        self.note = ''
        self.retry_at = 0
        self.retries = 0
        self.plan = deque(reply.actions)

    def _move(self, action):
        before = self.game.snapshot()
        result = self.game.step(action)
        self.last_action = f'{action} -> {result.applied or "rejected"}'
        transition = {'before': before, 'result': asdict(result), 'state': self.game.snapshot()}
        self.history.append(transition)
        self._log('step', **transition)
        self.last_step = time.monotonic()
        self.single_step = False
        self.best = max(self.best, self.game.score)
        if result.applied is None:
            self.plan.clear()
            self.stats.errors += 1
            self.error = f'Illegal action ({result.reason}); no move applied. C: new plan'
            self.paused = True
        if result.ate or self.game.done:
            self.plan.clear()

    def update(self):
        reply = self.worker.poll()
        if reply is not None:
            self._receive(reply)
        if self.storage_failed:
            return
        if self.game.done:
            if not self.ended:
                self._log('end', state=self.game.snapshot(), session_stats=asdict(self.stats))
                self.ended = True
            if (self.memory and not self.reflected and not self.paused
                    and self.game.reason in ('collision', 'idle_limit', 'step_limit', 'win')):
                self.reflected = True
                self._start_request('reflection')
            return
        if self.paused and not self.single_step:
            return
        if self.manual:
            if self.single_step or time.monotonic() - self.last_step >= 1 / self.speed:
                self._move(self.plan.popleft() if self.plan else self.game.direction)
            return
        if self.worker.busy:
            return
        # Budget applies to new requests; already paid plans can finish.
        if not self.plan:
            if self.error and not self.retry_at:
                return
            if time.monotonic() < self.retry_at:
                return
            self._start_request()
        elif self.single_step or time.monotonic() - self.last_step >= 1 / self.speed:
            self._move(self.plan.popleft())

    def toggle_pause(self):
        # Pausing lets a request finish, but does not execute its result.
        self.paused = not self.paused
        self.single_step = False
        self.last_step = time.monotonic()

    def step_once(self):
        self.paused = True
        if not self.error or self.retry_at:
            self.single_step = True

    def retry(self):
        if self.worker.busy or self.game.done or self.storage_failed:
            return
        self.plan.clear()
        self.error = ''
        self.note = ''
        self.retries = 0
        self.retry_at = 0
        self.paused = False

    def manual_turn(self, action):
        from game import OPPOSITE
        if self.manual and not self.game.done and action != OPPOSITE[self.game.direction]:
            self.plan = deque([action])  # at most one direction change per actual step

    def restart(self):
        self._cancel_pending()
        if not self.ended:
            self.game.finish('restarted')
            self._log('end', state=self.game.snapshot(), session_stats=asdict(self.stats))
        self.recorder.close()
        if not self.storage_failed:
            self._new_episode()  # session budgets deliberately do not reset

    def _cancel_pending(self):
        if self.worker.busy:
            self.worker.cancel()
            self.stats.unknown_usage += 1
            self._log('request_cancelled', note='Server may still bill this request; usage unknown')

    def close(self):
        self._cancel_pending()
        if self.recorder:
            if not self.ended:
                self.game.finish('closed')
                self._log('end', state=self.game.snapshot(), session_stats=asdict(self.stats))
                self.ended = True
            if not self.recorder.stream.closed:
                self._log('summary', session_stats=asdict(self.stats))
            self.recorder.close()
