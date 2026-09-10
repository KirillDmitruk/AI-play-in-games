"""Append-only episode logs, bounded local lessons, and offline replay."""
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid


class Recorder:
    def __init__(self, directory, settings, state, mode, episode, lessons):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        self.path = directory / f'{stamp}_{uuid.uuid4().hex[:8]}.jsonl'
        self.stream = self.path.open('x', encoding='utf-8')
        self.write('start', version=1, settings=settings.as_dict(), state=state,
                   mode=mode, episode=episode, lessons=lessons)

    def write(self, event, **data):
        self.stream.write(json.dumps({'event': event, **data}, ensure_ascii=False) + '\n')
        self.stream.flush()

    def close(self):
        self.stream.close()


class Memory:
    def __init__(self, path):
        self.path = Path(path)
        self.lessons = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if (not isinstance(data, list) or len(data) > 5
                    or any(not isinstance(x, str) or not 1 <= len(x) <= 140 for x in data)):
                raise ValueError('Invalid memory file; rename or remove memory.json')
            self.lessons = data

    def add(self, lessons):
        merged = list(dict.fromkeys(self.lessons + lessons))[-5:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.path)
        self.lessons = merged


def validate_state(state):
    if not isinstance(state, dict):
        raise ValueError('Replay state must be an object')
    w, h = state.get('grid_width'), state.get('grid_height')
    if type(w) is not int or type(h) is not int or not 2 <= w <= 100 or not 2 <= h <= 100:
        raise ValueError('Invalid replay board')
    def cell(p):
        return (isinstance(p, list) and len(p) == 2 and all(type(x) is int for x in p)
                and 0 <= p[0] < w and 0 <= p[1] < h)
    body = state.get('body')
    if not isinstance(body, list) or not 1 <= len(body) <= w * h or not all(cell(p) for p in body):
        raise ValueError('Invalid replay body')
    if state.get('head') != body[-1] or (state.get('food') is not None and not cell(state['food'])):
        raise ValueError('Invalid replay head or food')
    from game import DIRECTIONS
    if state.get('direction') not in DIRECTIONS:
        raise ValueError('Invalid replay direction')
    if type(state.get('seed')) is not int:
        raise ValueError('Invalid replay seed')
    for name in ('score', 'steps', 'idle_steps'):
        if type(state.get(name)) is not int or state[name] < 0:
            raise ValueError(f'Invalid replay {name}')
    return state


class Replay:
    def __init__(self, path):
        path = Path(path)
        if path.stat().st_size > 25 * 1024 * 1024:
            raise ValueError('Replay is too large (limit: 25 MiB)')
        self.frames = []
        self.warning = ''
        self.header = None
        self.index = 0
        lines = path.read_text(encoding='utf-8').splitlines()
        for n, line in enumerate(lines):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                if n == len(lines) - 1:
                    self.warning = 'Incomplete final log line was skipped'
                    break
                raise ValueError('Invalid replay JSON') from None
            if not isinstance(entry, dict):
                raise ValueError('Invalid replay record')
            if n == 0:
                if entry.get('event') != 'start' or entry.get('version') != 1:
                    raise ValueError('Unsupported replay version')
                self.header = entry
            if entry.get('event') in ('start', 'step', 'end'):
                self.frames.append(validate_state(entry.get('state')))
        if not self.header or not self.frames:
            raise ValueError('Replay contains no frames')

    @property
    def state(self):
        return self.frames[self.index]

    def advance(self, delta=1):
        self.index = max(0, min(len(self.frames) - 1, self.index + delta))
