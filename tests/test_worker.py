from dataclasses import replace
import time
import unittest
from agent import Reply
from game import SnakeGame
from settings import Settings
from worker import RequestWorker


def delayed_result(pipe, settings, state, lessons, kind, history):
    time.sleep(2)
    pipe.send(Reply(actions=['UP']))
    pipe.close()


class WorkerTests(unittest.TestCase):
    def test_timeout_cleans_up_and_poll_does_not_block(self):
        worker = RequestWorker(target=delayed_result)
        worker.start(replace(Settings(), timeout_seconds=1), SnakeGame().snapshot())
        started = time.monotonic()
        self.assertIsNone(worker.poll())
        self.assertLess(time.monotonic() - started, .2)
        result = None
        deadline = time.monotonic() + 4
        while result is None and time.monotonic() < deadline:
            result = worker.poll()
            time.sleep(.01)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.error)
        self.assertFalse(worker.busy)

    def test_cancel_discards_late_result_and_releases_process(self):
        worker = RequestWorker(target=delayed_result)
        worker.start(Settings(), SnakeGame().snapshot())
        process = worker.process
        worker.cancel()
        self.assertFalse(worker.busy)
        self.assertIsNone(worker.poll())
        self.assertTrue(process._closed)
