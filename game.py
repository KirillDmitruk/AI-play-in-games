"""Snake rules without window, network requests or import side effects."""
import random
from dataclasses import dataclass

DIRECTIONS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
OPPOSITE = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}


@dataclass(frozen=True)
class StepResult:
    requested: str
    applied: str | None
    ate: bool = False
    reason: str | None = None


class SnakeGame:
    def __init__(self, width=20, height=20, seed=None, max_steps=2000, max_idle_steps=200):
        if width < 2 or height < 2:
            raise ValueError('Board dimensions must be at least 2')
        self.width, self.height = width, height
        self.seed = seed if seed is not None else random.SystemRandom().randrange(2 ** 32)
        self.rng = random.Random(self.seed)
        self.body = [(width // 2, height // 2)]  # tail -> head
        self.direction = 'RIGHT'
        self.steps = self.idle_steps = self.score = 0
        self.max_steps, self.max_idle_steps = max_steps, max_idle_steps
        self.done = False
        self.reason = None
        self.food = self.create_food()

    @property
    def head(self):
        return self.body[-1]

    def create_food(self):
        occupied = set(self.body)
        free = [(x, y) for y in range(self.height) for x in range(self.width)
                if (x, y) not in occupied]
        return self.rng.choice(free) if free else None

    def finish(self, reason):
        self.done, self.reason = True, reason

    def step(self, action):
        if self.done:
            return StepResult(action, None, reason='finished')
        if action not in DIRECTIONS:
            return StepResult(action, None, reason='invalid_action')
        if action == OPPOSITE[self.direction]:
            return StepResult(action, None, reason='reverse')
        dx, dy = DIRECTIONS[action]
        head = ((self.head[0] + dx) % self.width, (self.head[1] + dy) % self.height)
        ate = head == self.food
        occupied = self.body if ate else self.body[1:]
        self.direction = action
        self.steps += 1
        self.idle_steps += 1
        if head in occupied:
            self.finish('collision')
            return StepResult(action, action, reason=self.reason)
        self.body.append(head)
        if ate:
            self.score += 1
            self.idle_steps = 0
            self.food = self.create_food()  # includes the NEW head
            if self.food is None:
                self.finish('win')
        else:
            self.body.pop(0)
        if not self.done and self.steps >= self.max_steps:
            self.finish('step_limit')
        if not self.done and self.idle_steps >= self.max_idle_steps:
            self.finish('idle_limit')
        return StepResult(action, action, ate, self.reason)

    def snapshot(self):
        return {'grid_width': self.width, 'grid_height': self.height,
                'head': list(self.head), 'body': [list(p) for p in self.body],
                'food': list(self.food) if self.food is not None else None,
                'direction': self.direction, 'steps': self.steps, 'score': self.score,
                'idle_steps': self.idle_steps, 'done': self.done, 'reason': self.reason,
                'seed': self.seed}


if __name__ == '__main__':
    from main import main

    main(['--manual'])
