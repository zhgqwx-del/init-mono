"""Local campaign API for the three-service sample."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

API_PATH = "/ops/api/v1/campaigns"
STATUS_VALUES = {"DRAFT", "ACTIVE", "ENDED"}
# Demo-only identities. The query string cannot change the caller's tenant.
DEMO_IDENTITIES = {"Bearer demo-tenant-a": "A", "Bearer demo-tenant-b": "B"}


def query_value(query, name, default):
    values = query.get(name, [default])
    if len(values) != 1:
        raise ValueError(f"{name} must appear at most once")
    return values[0]


def positive_int(value, name, maximum):
    if not re.fullmatch(r"[0-9]{1,9}", value) or not 1 <= int(value) <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return int(value)


def make_server(port, capacity_port):
    fixtures = json.loads(Path(__file__).with_name("fixtures.json").read_text(encoding="utf-8"))
    fixtures.sort(key=lambda campaign: campaign["id"])

    class CampaignAPI(BaseHTTPRequestHandler):
        def respond(self, status, value):
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path != API_PATH:
                self.respond(404, {"error": {"code": "NOT_FOUND", "message": "Unknown path"}})
                return

            tenant = DEMO_IDENTITIES.get(self.headers.get("Authorization"))
            if tenant is None:
                self.respond(401, {"error": {"code": "UNAUTHORIZED", "message": "Demo identity required"}})
                return

            try:
                query = parse_qs(url.query, keep_blank_values=True, max_num_fields=32)
                status = query_value(query, "status", None)
                if status is not None and status not in STATUS_VALUES:
                    raise ValueError("status must be DRAFT, ACTIVE, or ENDED")
                keyword = query_value(query, "keyword", "").strip().casefold()
                page = positive_int(query_value(query, "page", "1"), "page", 1_000_000)
                page_size = positive_int(query_value(query, "pageSize", "20"), "pageSize", 100)
            except ValueError as error:
                self.respond(400, {"error": {"code": "INVALID_QUERY", "message": str(error)}})
                return

            matches = [
                {key: item[key] for key in ("id", "name", "status")}
                for item in fixtures
                if item["tenant"] == tenant
                and keyword in item["name"].casefold()
                and (status is None or item["status"] == status)
            ]
            start = (page - 1) * page_size
            self.respond(200, {"items": matches[start:start + page_size], "total": len(matches)})

    return ThreadingHTTPServer(("127.0.0.1", port), CampaignAPI)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4281)
    parser.add_argument("--capacity-port", type=int, default=4282)
    args = parser.parse_args()
    with make_server(args.port, args.capacity_port) as server:
        print(f"API http://127.0.0.1:{server.server_port}{API_PATH}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
