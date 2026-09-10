"""Pygame presentation only. The renderer never calls the network."""
import time
import pygame
from game import DIRECTIONS

BG = (19, 23, 29)
BOARD = (26, 32, 40)
GRID = (34, 42, 51)
TEXT = (226, 232, 235)
MUTED = (145, 158, 170)
GREEN = (81, 190, 139)
GOLD = (234, 181, 101)
RED = (231, 112, 111)


class View:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1060, 700))
        pygame.display.set_caption('AI Snake 0.2.0 - Gemini laboratory')
        self.font = pygame.font.SysFont('dejavusans,consolas,arial', 17)
        self.small = pygame.font.SysFont('dejavusans,consolas,arial', 14)
        self.title = pygame.font.SysFont('dejavusans,consolas,arial', 27, bold=True)
        self.buttons = {
            'pause': pygame.Rect(652, 510, 180, 38),
            'step': pygame.Rect(844, 510, 188, 38),
            'restart': pygame.Rect(652, 560, 180, 38),
            'retry': pygame.Rect(844, 560, 188, 38),
        }

    def text(self, text, x, y, color=TEXT, font=None):
        self.screen.blit((font or self.font).render(str(text), True, color), (x, y))

    def wrapped(self, text, x, y, width=374, color=TEXT, max_lines=3):
        lines, line = [], ''
        for word in str(text).split():
            if self.small.size((line + ' ' + word).strip())[0] > width and line:
                lines.append(line)
                line = word
            else:
                line = (line + ' ' + word).strip()
        lines.append(line)
        for index, line in enumerate(lines[:max_lines]):
            self.text(line, x, y + index * 20, color, self.small)

    def draw(self, state, controller=None, replay=None, paused=False, speed=5):
        self.screen.fill(BG)
        self.text('AI SNAKE', 20, 14, font=self.title)
        self.text('GEMINI / OBSERVE / REPLAY', 222, 24, MUTED, self.small)
        board = pygame.Rect(20, 60, 600, 600)
        pygame.draw.rect(self.screen, BOARD, board, border_radius=8)
        cw, ch = 600 / state['grid_width'], 600 / state['grid_height']
        def center(p):
            return (int(20 + (p[0] + .5) * cw), int(60 + (p[1] + .5) * ch))
        for i in range(1, state['grid_width']):
            pygame.draw.line(self.screen, GRID, (int(20 + i * cw), 60), (int(20 + i * cw), 660))
        for i in range(1, state['grid_height']):
            pygame.draw.line(self.screen, GRID, (20, int(60 + i * ch)), (620, int(60 + i * ch)))
        for p in state['body']:
            rect = pygame.Rect(int(20 + p[0] * cw + 2), int(60 + p[1] * ch + 2), max(2, int(cw - 4)), max(2, int(ch - 4)))
            pygame.draw.rect(self.screen, GREEN if p != state['head'] else (145, 232, 173), rect, border_radius=5)
        if state['food'] is not None:
            pygame.draw.circle(self.screen, RED, center(state['food']), max(2, int(min(cw, ch) * .3)))
        if controller and controller.plan:
            p = state['head'][:]
            for n, action in enumerate(controller.plan, 1):
                dx, dy = DIRECTIONS[action]
                p = [(p[0] + dx) % state['grid_width'], (p[1] + dy) % state['grid_height']]
                pygame.draw.circle(self.screen, GOLD, center(p), max(3, int(min(cw, ch) * .23)), 2)
                self.text(n, center(p)[0] - 4, center(p)[1] - 10, GOLD, self.small)
        x = 652
        mode = 'OFFLINE REPLAY' if replay else ('MANUAL' if controller.manual else controller.settings.model)
        self.text(mode, x, 24, GREEN)
        self.text(f'Score {state["score"]}    Length {len(state["body"])}', x, 65, font=self.title)
        self.text(f'Steps {state["steps"]}    Idle {state["idle_steps"]}', x, 110)
        self.text(f'Seed {state["seed"]}', x, 140, MUTED)
        if controller:
            s = controller.stats
            self.text(f'Episode {controller.episode}    Session best {controller.best}', x, 170)
            self.text(f'Requests {s.requests}/{controller.settings.max_session_requests}', x, 208)
            self.text(f'Tokens {s.tokens:,} / {controller.settings.max_session_tokens:,}', x, 238)
            self.text(f'Input {s.input:,}  Output {s.output:,}  Think {s.thought:,}', x, 268, MUTED, self.small)
            self.text(f'Last request {s.last_seconds:.2f}s   Errors {s.errors}', x, 292, MUTED, self.small)
            self.text(f'Unknown usage: {s.unknown_usage} request(s)', x, 315, MUTED, self.small)
            if controller.worker.busy:
                status = f'Waiting for Gemini... {time.monotonic() - controller.worker.started:.1f}s'
            elif controller.game.done:
                status = f'Finished: {controller.game.reason}'
            elif controller.paused:
                status = 'Paused'
            elif controller.retry_at:
                status = f'Retrying in {max(0, controller.retry_at - time.monotonic()):.1f}s'
            else:
                status = 'Running'
            self.text(status, x, 346, GOLD)
            self.wrapped(controller.error or controller.note or f'Last action: {controller.last_action}', x, 381,
                         color=RED if controller.error else TEXT)
            self.text(f'Memory: {"ON" if controller.memory else "OFF"}    Speed: {controller.speed:g} steps/s', x, 453, MUTED, self.small)
            self.text('Plan: ' + (' '.join(controller.plan) or '-'), x, 480, GOLD, self.small)
            self.text('Recording: ' + controller.recorder.path.name, 20, 674, MUTED, self.small)
        else:
            self.text(f'Frame {replay.index + 1}/{len(replay.frames)}', x, 180)
            self.text('No API calls. No tokens.', x, 220, GREEN)
            self.text('Paused' if paused else 'Playing', x, 270, GOLD)
            self.text(f'Speed: {speed:g} frames/s', x, 305)
            self.wrapped(replay.warning or 'Left / Right: previous / next frame', x, 360, color=MUTED)
        labels = {'pause': 'Space: pause/play', 'step': 'N: one step', 'restart': 'R: restart', 'retry': 'C: retry plan'}
        for name, rect in self.buttons.items():
            if replay and name == 'retry':
                continue
            pygame.draw.rect(self.screen, (40, 49, 60), rect, border_radius=7)
            self.text(labels[name], rect.x + 10, rect.y + 9, TEXT, self.small)
        self.text('+ / - : speed     Esc: quit', x, 622, MUTED, self.small)
        self.text('Manual: WASD / arrow keys', x, 647, MUTED, self.small)
        pygame.display.flip()


def run(controller=None, replay=None, frame_hook=None, max_frames=None):
    view = View()
    clock = pygame.time.Clock()
    running, paused, speed = True, False, 5
    last = time.monotonic()
    frame = 0
    key_actions = {pygame.K_SPACE: 'pause', pygame.K_n: 'step', pygame.K_r: 'restart', pygame.K_c: 'retry'}
    turns = {pygame.K_w: 'UP', pygame.K_UP: 'UP', pygame.K_s: 'DOWN', pygame.K_DOWN: 'DOWN',
             pygame.K_a: 'LEFT', pygame.K_LEFT: 'LEFT', pygame.K_d: 'RIGHT', pygame.K_RIGHT: 'RIGHT'}
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                    break
                action = None
                if event.type == pygame.KEYDOWN:
                    action = key_actions.get(event.key)
                    if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        if controller:
                            controller.speed = min(30, controller.speed + 1)
                        else:
                            speed = min(30, speed + 1)
                    if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        if controller:
                            controller.speed = max(1, controller.speed - 1)
                        else:
                            speed = max(1, speed - 1)
                    if controller and event.key in turns:
                        controller.manual_turn(turns[event.key])
                    if replay and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        paused = True
                        replay.advance(-1 if event.key == pygame.K_LEFT else 1)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = next((name for name, rect in view.buttons.items() if rect.collidepoint(event.pos)), None)
                if controller:
                    handlers = {'pause': controller.toggle_pause, 'step': controller.step_once,
                                'restart': controller.restart, 'retry': controller.retry}
                    if action in handlers:
                        handlers[action]()
                elif action == 'pause':
                    paused = not paused
                elif action == 'step':
                    paused = True
                    replay.advance()
                elif action == 'restart':
                    replay.index = 0
                    last = time.monotonic()
            if not running:
                break  # no extra movement or network call after QUIT
            if controller:
                controller.update()
                state = controller.game.snapshot()
            else:
                if not paused and time.monotonic() - last >= 1 / speed:
                    replay.advance()
                    last = time.monotonic()
                state = replay.state
            view.draw(state, controller, replay, paused, speed)
            if frame_hook:
                frame_hook(frame, view)
            frame += 1
            if max_frames and frame >= max_frames:
                break
            clock.tick(60)
    finally:
        if controller:
            controller.close()
        pygame.quit()
    return frame
