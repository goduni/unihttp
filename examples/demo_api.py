"""Local API for the backend quickstarts; run with python examples/demo_api.py."""

import json
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class DemoAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        found = self.path == "/users/1"
        data = {"id": 1, "name": "Ada"} if found else {"error": "User not found"}
        body = json.dumps(data).encode()
        self.send_response(200 if found else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    with ThreadingHTTPServer(("127.0.0.1", 8000), DemoAPIHandler) as server:
        print("Demo API: http://127.0.0.1:8000/users/1 (Ctrl+C to stop)")
        with suppress(KeyboardInterrupt):
            server.serve_forever()


if __name__ == "__main__":
    main()
