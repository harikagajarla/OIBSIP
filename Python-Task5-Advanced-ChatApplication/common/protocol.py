"""Newline-delimited JSON protocol validation and framing."""
import json

MAX_MESSAGE_BYTES = 16_384
VALID_ACTIONS = {"register", "login", "logout", "rooms", "create_room", "join_room", "chat", "ping"}

class ProtocolError(ValueError):
    pass

def encode(message: dict) -> bytes:
    if not isinstance(message, dict):
        raise ProtocolError("Message must be an object")
    return (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

def decode_line(data: bytes) -> dict:
    if len(data) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Message is too large")
    try:
        message = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Malformed JSON") from exc
    if not isinstance(message, dict) or not isinstance(message.get("action"), str):
        raise ProtocolError("A message needs a string action")
    if message["action"] not in VALID_ACTIONS:
        raise ProtocolError("Unsupported action")
    return message
