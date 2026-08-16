import os
import shutil

from app.settings_store import get_setting
from midgard_ai_engine import (
    AIEngineError,
    AIProvider,
    AnthropicAPIProvider,
    ClaudeCLIProvider,
    CodexCLIProvider,
    ProviderUnavailableError,
    complete_via_chain,
)

__all__ = [
    "AIProvider",
    "AIEngineError",
    "ProviderUnavailableError",
    "complete",
    "get_provider_chain",
    "ai_status",
]


def _claude_cli() -> AIProvider | None:
    return ClaudeCLIProvider() if shutil.which("claude") else None


def _codex_cli() -> AIProvider | None:
    return CodexCLIProvider() if shutil.which("codex") else None


def _anthropic_api() -> AIProvider | None:
    api_key = get_setting("ai_anthropic_api_key") or os.environ.get("MIMIR_ANTHROPIC_API_KEY", "")
    return AnthropicAPIProvider(api_key) if api_key else None


def get_provider_chain() -> list[AIProvider]:
    """Candidate providers in priority order. Mode "auto" (default) tries
    whatever's actually available on this host/container -- CLI logins
    reuse an existing subscription at no extra cost, the API key is only
    a fallback for hosts without claude/codex installed."""
    mode = get_setting("ai_provider_mode") or os.environ.get("MIMIR_AI_PROVIDER_MODE", "auto")

    if mode == "claude_cli":
        candidates = [_claude_cli()]
    elif mode == "codex_cli":
        candidates = [_codex_cli()]
    elif mode == "anthropic_api":
        candidates = [_anthropic_api()]
    else:
        candidates = [_claude_cli(), _codex_cli(), _anthropic_api()]

    return [p for p in candidates if p is not None]


def complete(prompt: str) -> tuple[str, str]:
    """Runs `prompt` through the provider chain, falling through to the
    next candidate when one is unavailable (was previously always just
    chain[0] with no fallback -- a provider going down meant every AI
    feature failed even when a working fallback was configured right
    behind it). Returns (response_text, provider_name)."""
    return complete_via_chain(get_provider_chain(), prompt)


def ai_status() -> dict:
    chain = get_provider_chain()
    if not chain:
        return {"available": False, "provider": None}
    return {"available": True, "provider": chain[0].name}
