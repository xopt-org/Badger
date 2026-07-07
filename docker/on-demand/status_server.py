"""Lightweight HTTP status endpoint reporting VNC client count."""

import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            clients = self._get_vnc_client_count()
            body = json.dumps({"clients": clients, "occupied": clients > 0})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _get_vnc_client_count(self):
        try:
            # Count established TCP connections to VNC port (5900).
            # websockify only connects to x11vnc when a browser client is active.
            result = subprocess.run(
                ["ss", "-tn", "state", "established", "sport", "=", ":5900"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            lines = result.stdout.strip().split("\n")
            # First line is header, remaining are connections
            return max(0, len(lines) - 1)
        except Exception:
            return 0

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), StatusHandler)
    server.serve_forever()
