from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from agent import Reply
from controller import Controller
from records import Replay, Memory
from settings import Settings


class FakeWorker:
    def __init__(self):
        self.busy = False
        self.reply = None
        self.started = 0
        self.starts = 0
        self.cancelled = False

    def start(self, *args):
        assert not self.busy
        self.busy = True
        self.starts += 1

    def poll(self):
        result = self.reply
        if result is not None:
            self.reply = None
            self.busy = False
        return result

    def cancel(self):
        self.busy = False
        self.reply = None
        self.cancelled = True


@patch.dict('os.environ', {'GEMINI_API_KEY': 'test-only'})
class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.worker = FakeWorker()
        self.c = Controller(replace(Settings(), retry_delay_seconds=0), self.root, seed=42, worker=self.worker)

    def tearDown(self):
        self.c.close()
        self.temp.cleanup()

    def test_waiting_and_paused_response_do_not_move(self):
        before = self.c.game.snapshot()
        self.c.update()
        for _ in range(10):
            self.c.update()
        self.assertEqual(self.worker.starts, 1)
        self.assertEqual(self.c.game.snapshot(), before)
        self.c.toggle_pause()
        self.worker.reply = Reply(actions=['UP', 'UP'], usage={'total': 12})
        self.c.update()
        self.assertEqual(self.c.game.snapshot(), before)
        self.c.step_once()
        self.c.update()
        self.assertEqual(self.c.game.steps, 1)
        self.c.update()
        self.assertEqual(self.c.game.steps, 1)
        self.assertTrue(self.c.paused)

    def test_bad_response_counted_and_retry_bounded(self):
        for i in range(3):
            self.c.update()
            self.worker.reply = Reply(error='bad format', retryable=True, usage={'total': 10})
            self.c.update()
        self.assertEqual(self.c.stats.requests, 3)
        self.assertEqual(self.c.stats.tokens, 30)
        self.assertTrue(self.c.paused)
        self.assertEqual(self.c.game.steps, 0)
        for _ in range(10):
            self.c.update()
        self.assertEqual(self.worker.starts, 3)

    def test_reverse_rejected_and_food_discards_plan(self):
        self.c.plan.extend(['LEFT', 'DOWN'])
        self.c.step_once()
        self.c.update()
        self.assertEqual(self.c.game.steps, 0)
        self.assertTrue(self.c.error)
        self.c.retry()
        self.c.game.food = (11, 10)
        self.c.plan.extend(['RIGHT', 'RIGHT', 'RIGHT'])
        self.c.step_once()
        self.c.update()
        self.assertEqual(self.c.game.score, 1)
        self.assertFalse(self.c.plan)

    def test_restart_cancels_and_preserves_session_budget(self):
        self.c.settings = replace(self.c.settings, max_session_requests=1)
        self.c.update()
        self.c.restart()
        self.assertTrue(self.worker.cancelled)
        self.assertEqual(self.c.stats.unknown_usage, 1)
        self.c.update()
        self.assertEqual(self.worker.starts, 1)
        self.assertEqual(self.c.game.reason, 'session_request_limit')

    def test_token_threshold_blocks_next_request(self):
        self.c.settings = replace(self.c.settings, max_session_tokens=10)
        self.c.update()
        self.worker.reply = Reply(actions=['RIGHT'], usage={'total': 12})
        self.c.update()
        self.c.step_once()
        self.c.update()
        self.c.toggle_pause()
        self.c.update()
        self.assertEqual(self.c.game.reason, 'session_token_limit')
        self.assertEqual(self.worker.starts, 1)

    def test_replay_round_trip_and_no_calls(self):
        self.c.plan.extend(['RIGHT'])
        self.c.step_once()
        self.c.update()
        state = self.c.game.snapshot()
        path = self.c.recorder.path
        self.c.recorder.stream.flush()
        replay = Replay(path)
        replay.advance()
        self.assertEqual(replay.state, state)
        self.assertEqual(self.worker.starts, 0)

    def test_memory_persistence_and_bounded_lessons(self):
        memory = Memory(self.root / 'memory.json')
        memory.add([f'Lesson {n}' for n in range(5)])
        memory.add(['Lesson 5'])
        self.assertEqual(len(Memory(memory.path).lessons), 5)
        self.c.memory = memory
        self.c.game.finish('collision')
        self.c.update()
        self.assertEqual(self.worker.starts, 1)
        self.worker.reply = Reply(kind='reflection', lessons=['Keep space'], usage={'total': 40})
        self.c.update()
        self.assertIn('Keep space', Memory(memory.path).lessons)
        self.assertEqual(self.c.stats.tokens, 40)

    def test_partial_last_replay_line(self):
        self.c.recorder.stream.flush()
        path = self.root / 'partial.jsonl'
        path.write_text(self.c.recorder.path.read_text() + '{"eve', encoding='utf-8')
        self.assertTrue(Replay(path).warning)
