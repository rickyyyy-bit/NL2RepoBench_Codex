"""Credential redaction and diagnostic-only Codex event summaries."""
import json


def redact_bytes(value, secret):
    for token in {secret.encode(), json.dumps(secret)[1:-1].encode()}:
        if token:
            value = value.replace(token, b"[REDACTED]")
    return value


def summarize_events(path):
    totals, errors, malformed = {}, [], 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
            if event.get("type") == "turn.completed":
                for key, value in (event.get("usage") or {}).items():
                    if type(value) is int:
                        totals[key] = totals.get(key, 0) + value
            if event.get("type") in {"error", "turn.failed"}:
                errors.append(event)
        except (ValueError, AttributeError):
            malformed += 1
    return {"token_usage": totals or None, "event_errors": errors, "non_json_lines": malformed}
