"""Local capacity service. Baseline supports one campaign per request."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

DEMO_IDENTITIES = {"Bearer demo-tenant-a": "A", "Bearer demo-tenant-b": "B"}


def make_server(port):
    records = json.loads(Path(__file__).with_name("fixtures.json").read_text(encoding="utf-8"))

    class CapacityAPI(BaseHTTPRequestHandler):
        def respond(self, status, value):
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            tenant = DEMO_IDENTITIES.get(self.headers.get("Authorization"))
            if tenant is None:
                self.respond(401, {"error": {"code": "UNAUTHORIZED"}})
                return
            path = urlsplit(self.path).path
            prefix = "/internal/capacities/"
            campaign_id = path[len(prefix):] if path.startswith(prefix) else ""
            record = next((item for item in records
                           if item["id"] == campaign_id and item["tenant"] == tenant), None)
            if record is None:
                self.respond(404, {"error": {"code": "NOT_FOUND"}})
                return
            self.respond(200, {key: record[key] for key in ("id", "capacity", "reserved")})

    return ThreadingHTTPServer(("127.0.0.1", port), CapacityAPI)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4282)
    with make_server(parser.parse_args().port) as server:
        print(f"Capacity http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
