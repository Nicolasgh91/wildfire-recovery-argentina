#!/usr/bin/env python3
"""
Static server for local storage thumbnails.

Commands:
  - Default (serve ./storage on http://127.0.0.1:9000):
      python scripts/serve_storage.py
  - Custom root and port:
      python scripts/serve_storage.py --root storage --port 9100
  - Custom host:
      python scripts/serve_storage.py --host 0.0.0.0 --port 9000
"""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class StorageHandler(SimpleHTTPRequestHandler):
    """Simple static file handler with permissive CORS header."""

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description="Serve local storage files.")
    parser.add_argument("--root", default="storage", help="Root directory to serve")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=9000, help="Bind port")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Root directory not found: {root}")

    handler = lambda *h_args, **h_kwargs: StorageHandler(
        *h_args, directory=str(root), **h_kwargs
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving {root} at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
