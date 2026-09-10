import os
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame
from app import run
from controller import Controller
from records import Replay
from settings import Settings


class AppTests(unittest.TestCase):
    def test_quit_event_does_not_apply_an_extra_step(self):
        with tempfile.TemporaryDirectory() as directory:
            c = Controller(Settings(), Path(directory), manual=True, seed=42)
            c.paused = True
            c.single_step = True
            def hook(frame, view):
                self.assertEqual(c.game.steps, 1)
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            frames = run(controller=c, frame_hook=hook, max_frames=4)
            self.assertEqual(frames, 1)
            self.assertEqual(c.game.steps, 1)

    @patch.dict('os.environ', {'SDL_VIDEODRIVER': 'dummy', 'SDL_AUDIODRIVER': 'dummy'}, clear=True)
    def test_missing_key_window_and_replay_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            c = Controller(Settings(), Path(directory), seed=-1)
            path = c.recorder.path
            frames = run(controller=c, max_frames=3)
            self.assertEqual(frames, 3)
            self.assertIn('GEMINI_API_KEY', c.error)
            self.assertEqual(c.stats.requests, 0)
            self.assertEqual(c.game.steps, 0)
            self.assertEqual(run(replay=Replay(path), max_frames=3), 3)

    def test_mouse_pause_and_single_step(self):
        with tempfile.TemporaryDirectory() as directory:
            c = Controller(Settings(), Path(directory), manual=True)
            def hook(frame, view):
                if frame == 0:
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=view.buttons['pause'].center))
                elif frame == 1:
                    self.assertTrue(c.paused)
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_n))
                elif frame == 2:
                    self.assertEqual(c.game.steps, 1)
                    self.assertTrue(c.paused)
            run(controller=c, frame_hook=hook, max_frames=4)
            self.assertEqual(c.game.steps, 1)
