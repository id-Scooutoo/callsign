from enum import Enum


class State(Enum):
    SLEEPING = "sleeping"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class DialogFSM:
    """Wake -> open dialog window -> sleep on silence timeout.

    Callers pass a monotonic ``now`` (seconds) so behaviour is testable.
    """

    def __init__(self, timeout: float):
        self.timeout = timeout
        self.state = State.SLEEPING
        self._deadline: float | None = None

    def on_wake(self, now: float) -> None:
        self.state = State.LISTENING
        self._deadline = now + self.timeout

    def on_utterance(self, now: float) -> None:
        self.state = State.THINKING
        self._deadline = now + self.timeout

    def on_reply_start(self) -> None:
        self.state = State.SPEAKING

    def on_reply_done(self, now: float) -> None:
        self.state = State.LISTENING
        self._deadline = now + self.timeout

    def tick(self, now: float) -> State:
        if (
            self.state == State.LISTENING
            and self._deadline is not None
            and now >= self._deadline
        ):
            self.state = State.SLEEPING
            self._deadline = None
        return self.state
