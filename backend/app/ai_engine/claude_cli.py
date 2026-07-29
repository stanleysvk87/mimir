import json
import subprocess

from .base import AIEngineError, ProviderUnavailableError

UNAVAILABLE_API_STATUSES = {401, 403, 429, 500, 502, 503, 529}


class ClaudeCLIProvider:
    name = "claude_cli"

    def complete(self, prompt: str) -> str:
        # Prompt must come immediately after -p. --disallowedTools stops
        # claude from occasionally interpreting a prompt as "write a file"
        # instead of just returning text (same fix as Sindri's).
        try:
            proc = subprocess.run(
                [
                    "claude", "-p", prompt,
                    "--output-format", "json",
                    "--disallowedTools", "Write,Edit,Bash,Read",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise ProviderUnavailableError(f"claude -p failed: {exc}") from exc

        if proc.returncode != 0:
            try:
                error_envelope = json.loads(proc.stdout)
            except json.JSONDecodeError:
                error_envelope = None
            if error_envelope and error_envelope.get("api_error_status") in UNAVAILABLE_API_STATUSES:
                raise ProviderUnavailableError(
                    f"claude -p API error {error_envelope.get('api_error_status')}: "
                    f"{error_envelope.get('result')}"
                )
            raise AIEngineError(f"claude -p returned an error: {proc.stderr[:500]}")

        try:
            outer = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise AIEngineError(f"claude -p returned invalid JSON envelope: {exc}") from exc

        result_text = outer.get("result") or ""
        if not result_text:
            raise AIEngineError("claude -p returned an empty response")
        return result_text
