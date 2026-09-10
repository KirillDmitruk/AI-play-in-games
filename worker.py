"""One cancellable process: UI never waits for network or SDK shutdown."""
import multiprocessing as mp
import time
from agent import Reply, request


def _run(connection, settings, state, lessons, kind, history):
    try:
        connection.send(request(settings, state, lessons, kind, history))
    except Exception:
        connection.send(Reply(error='Request worker failed', kind=kind))
    finally:
        connection.close()


class RequestWorker:
    def __init__(self, target=_run):
        self.target = target
        self.process = self.connection = None
        self.started = 0
        self.timeout = 0
        self.kind = 'plan'

    @property
    def busy(self):
        return self.process is not None

    def start(self, settings, state, lessons=(), kind='plan', history=()):
        if self.busy:
            raise RuntimeError('A request is already running')
        context = mp.get_context('spawn')
        receive, send = context.Pipe(duplex=False)
        process = context.Process(target=self.target,
            args=(send, settings, state, lessons, kind, history), daemon=True)
        try:
            process.start()
        except Exception:
            receive.close()
            send.close()
            raise
        send.close()
        self.process, self.connection = process, receive
        self.started, self.timeout, self.kind = time.monotonic(), settings.timeout_seconds, kind

    def poll(self):
        if not self.busy:
            return None
        elapsed = time.monotonic() - self.started
        if self.connection.poll():
            try:
                reply = self.connection.recv()
                if not isinstance(reply, Reply):
                    raise ValueError('Invalid worker result')
            except (EOFError, OSError, ValueError):
                reply = Reply(error='Request worker stopped unexpectedly', kind=self.kind)
            self.cancel()
            return reply
        if elapsed >= self.timeout or not self.process.is_alive():
            reply = Reply(error='Request timed out or worker stopped; usage unknown',
                          seconds=elapsed, retryable=True, kind=self.kind)
            self.cancel()
            return reply
        return None

    def cancel(self):
        if self.process:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=0.1)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=0.1)
            self.process.close()
            self.connection.close()
        self.process = self.connection = None
