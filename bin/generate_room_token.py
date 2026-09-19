#!/usr/bin/env python3
"""Gera links/tokens de acesso para uma sala Legenda."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

from room_auth import RoomTokenManager


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("room")
    parser.add_argument("--role", default="viewer", choices=["viewer", "presenter", "admin"])
    parser.add_argument("--ttl", type=int, default=3600, help="Validade em segundos")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--web-url", default="")
    parser.add_argument("--language", default="")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    manager = RoomTokenManager(str(config["room_auth_secret"]))
    token = manager.create(args.room, role=args.role, ttl_seconds=args.ttl)

    print(token)

    if args.web_url:
        params = {"room": args.room}
        if args.language:
            params["lang"] = args.language
        sep = "&" if "?" in args.web_url else "?"
        print(args.web_url + sep + urlencode(params) + "#token=" + token)


if __name__ == "__main__":
    main()
