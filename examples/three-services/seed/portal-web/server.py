"""Static web app and same-origin proxy for the local three-service demo."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

API_PATH = "/ops/api/v1/campaigns"
PUBLIC = Path(__file__).with_name("public")
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


def make_server(port, api_port):
    class WebServer(BaseHTTPRequestHandler):
        def respond(self, status, content_type, payload):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == API_PATH:
                self.proxy_campaigns()
            elif path in FILES:
                filename, content_type = FILES[path]
                self.respond(200, content_type, (PUBLIC / filename).read_bytes())
            else:
                self.send_error(404)

        def proxy_campaigns(self):
            request = Request(
                f"http://127.0.0.1:{api_port}{self.path}",
                headers={"Authorization": "Bearer demo-tenant-a"},
            )
            try:
                with urlopen(request, timeout=3) as response:
                    status, payload = response.status, response.read()
            except HTTPError as error:
                with error:
                    status, payload = error.code, error.read()
            except (URLError, TimeoutError):
                status, payload = 502, b'{"error":{"code":"API_UNAVAILABLE"}}'
            self.respond(status, "application/json; charset=utf-8", payload)

    return ThreadingHTTPServer(("127.0.0.1", port), WebServer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4280)
    parser.add_argument("--api-port", type=int, default=4281)
    args = parser.parse_args()
    with make_server(args.port, args.api_port) as server:
        print(f"Web http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
