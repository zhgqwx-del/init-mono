import argparse
import json
from pathlib import Path
from threading import Event

from services import services

parser = argparse.ArgumentParser()
parser.add_argument("projects", type=Path)
parser.add_argument("--web-port", type=int, default=4280)
parser.add_argument("--campaign-port", type=int, default=4281)
parser.add_argument("--capacity-port", type=int, default=4282)
args = parser.parse_args()
with services(args.projects, ports=(args.web_port, args.campaign_port, args.capacity_port)) as urls:
    print(json.dumps(urls), flush=True)
    try:
        Event().wait()
    except KeyboardInterrupt:
        pass
