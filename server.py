#!/usr/bin/env python3
"""Simple HTTP server to serve podcast RSS feed and audio files."""

import argparse
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Podcast RSS Feed Server")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    args = parser.parse_args()

    config = load_config(args.config)
    server_cfg = config.get("server", {})
    host = server_cfg.get("host", "0.0.0.0")
    port = server_cfg.get("port", 8080)
    output_dir = config.get("output_dir", "./output")

    # Ensure output dir exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    handler = partial(SimpleHTTPRequestHandler, directory=output_dir)
    server = HTTPServer((host, port), handler)

    print(f"Serving podcast feed at http://{host}:{port}/feed.xml")
    print(f"Serving from: {Path(output_dir).resolve()}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
