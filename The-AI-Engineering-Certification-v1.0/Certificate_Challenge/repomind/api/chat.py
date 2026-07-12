from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

# Ensure the project root (which contains the `rag` package) is importable.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rag.agent import run_agent


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            body = json.loads(raw_body or "{}")
            message = body.get("message")
            history = body.get("history") or []
            # session_id lets the server accumulate persistent memory per user
            session_id: str = str(body.get("sessionId") or "")

            if not isinstance(message, str) or not message.strip():
                self._send_json(400, {"error": "message is required"})
                return
            if not isinstance(history, list):
                history = []

            self._send_json(200, run_agent(message.strip(), history, session_id))
        except Exception as exc:
            msg = str(exc)
            safe = (
                "AI Gateway API key is not configured. Add AI_GATEWAY_API_KEY to your environment."
                if "AI_GATEWAY_API_KEY" in msg
                else "The agent encountered an error. Please try again."
            )
            self._send_json(500, {"error": safe})

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Allow", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
