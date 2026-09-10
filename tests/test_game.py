import unittest
from game import SnakeGame


class GameTests(unittest.TestCase):
    def test_wrap_four_edges(self):
        for head, direction, target in [((0, 1), 'LEFT', (19, 1)), ((19, 1), 'RIGHT', (0, 1)),
                                        ((1, 0), 'UP', (1, 19)), ((1, 19), 'DOWN', (1, 0))]:
            g = SnakeGame(seed=1)
            g.body, g.direction, g.food = [head], direction, (5, 5)
            g.step(direction)
            self.assertEqual(g.head, target)

    def test_reverse_and_invalid_do_not_move(self):
        g = SnakeGame(seed=2)
        before = g.snapshot()
        for action in ('LEFT', 'UP!', None):
            self.assertIsNone(g.step(action).applied)
            self.assertEqual(g.snapshot(), before)

    def test_new_food_never_on_new_head(self):
        for seed in range(100):
            g = SnakeGame(seed=seed)
            g.food = (11, 10)
            self.assertTrue(g.step('RIGHT').ate)
            self.assertEqual(len(g.body), 2)
            self.assertEqual(g.score, 1)
            self.assertNotIn(g.food, g.body)

    def test_full_board_wins(self):
        g = SnakeGame(width=2, height=2, seed=1)
        g.body = [(0, 0), (1, 0), (1, 1)]
        g.direction, g.food = 'DOWN', (0, 1)
        result = g.step('LEFT')
        self.assertEqual(result.reason, 'win')
        self.assertIsNone(g.food)
        self.assertIsNone(g.create_food())
        self.assertEqual(len(g.body), 4)

    def test_collision_and_tail_vacates(self):
        g = SnakeGame(seed=1)
        g.body = [(11, 9), (11, 10), (10, 10)]
        g.food = (0, 0)
        self.assertEqual(g.step('RIGHT').reason, 'collision')
        g = SnakeGame(seed=1)
        g.body = [(11, 10), (11, 9), (10, 9), (10, 10)]
        g.food = (0, 0)
        self.assertIsNone(g.step('RIGHT').reason)
        self.assertEqual(g.head, (11, 10))

    def test_idle_and_step_limits(self):
        for settings, reason in [({'max_idle_steps': 2}, 'idle_limit'), ({'max_steps': 2}, 'step_limit')]:
            g = SnakeGame(seed=1, **settings)
            g.food = (0, 0)
            g.step('RIGHT')
            g.step('RIGHT')
            self.assertEqual(g.reason, reason)
            before = g.snapshot()
            g.step('DOWN')
            self.assertEqual(g.snapshot(), before)

    def test_seed_and_snapshot_isolation(self):
        a, b = SnakeGame(seed=100), SnakeGame(seed=100)
        self.assertEqual(a.snapshot(), b.snapshot())
        state = a.snapshot()
        state['body'][0][0] = 999
        self.assertEqual(a.head, (10, 10))
