"""Entry point. Safe for multiprocessing spawn on Windows."""
import argparse
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description='Observe Gemini playing Snake; replay recorded games offline.')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--manual', action='store_true', help='Play with WASD or arrow keys; no key needed')
    mode.add_argument('--replay', type=Path, help='Replay a logs/*.jsonl file; no API calls')
    parser.add_argument('--config', type=Path, default=ROOT / 'settings.json')
    parser.add_argument('--logs', type=Path, default=ROOT / 'logs')
    parser.add_argument('--seed', type=int, help='Repeatable random seed; reused on R')
    parser.add_argument('--memory', action='store_true', help='Enable lessons; adds up to one review request per completed game')
    args = parser.parse_args(argv)
    try:
        from app import run
        if args.replay:
            from records import Replay
            run(replay=Replay(args.replay))
        else:
            from settings import Settings
            from controller import Controller
            settings = Settings.load(args.config)
            if args.memory:
                settings = replace(settings, memory=True)
            run(controller=Controller(settings, args.logs, manual=args.manual, seed=args.seed))
    except (ValueError, TypeError, OSError) as error:
        parser.exit(1, f'Cannot start: {error}\n')
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
