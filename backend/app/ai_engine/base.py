from typing import Protocol


class AIEngineError(Exception):
    pass


class ProviderUnavailableError(AIEngineError):
    """The provider itself couldn't be reached/run at all (missing binary,
    auth failure, rate limit, timeout) -- as opposed to it running fine and
    just producing a response the caller didn't like. Kept distinct so the
    caller can fall through to the next provider in the chain."""
    pass


class AIProvider(Protocol):
    name: str

    def complete(self, prompt: str) -> str:
        """Send a plain-text prompt, get a plain-text response back."""
        ...
