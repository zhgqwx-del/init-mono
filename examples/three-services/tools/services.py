"""Launch three independent repositories with real loopback HTTP connections."""
from contextlib import contextmanager, ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import runpy
import socket
from threading import Thread


@contextmanager
def services(projects, capacity_mode="real", ports=(0, 0, 0)):
    projects = Path(projects).resolve()
    with ExitStack() as resources:
        servers = []
        if capacity_mode == "offline":
            reserved = resources.enter_context(socket.socket())
            reserved.bind(("127.0.0.1", 0))
            capacity_port = reserved.getsockname()[1]
        else:
            if capacity_mode == "malformed":
                class MalformedCapacity(BaseHTTPRequestHandler):
                    def do_GET(self):
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"items": []}')
                capacity = ThreadingHTTPServer(("127.0.0.1", ports[2]), MalformedCapacity)
            else:
                factory = runpy.run_path(str(projects / "capacity-api/server.py"))["make_server"]
                capacity = factory(ports[2])
            resources.enter_context(capacity)
            servers.append(capacity)
            capacity_port = capacity.server_port
        campaign_factory = runpy.run_path(str(projects / "campaign-api/server.py"))["make_server"]
        campaign = resources.enter_context(campaign_factory(ports[1], capacity_port))
        web_factory = runpy.run_path(str(projects / "portal-web/server.py"))["make_server"]
        web = resources.enter_context(web_factory(ports[0], campaign.server_port))
        servers.extend([campaign, web])
        threads = []
        try:
            for server in servers:
                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()
                threads.append((server, thread))
            yield {
                "web": f"http://127.0.0.1:{web.server_port}",
                "campaign": f"http://127.0.0.1:{campaign.server_port}",
                "capacity": f"http://127.0.0.1:{capacity_port}",
            }
        finally:
            for server, thread in reversed(threads):
                server.shutdown()
                thread.join()
