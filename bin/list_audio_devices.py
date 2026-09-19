#!/usr/bin/env python3
"""Lista dispositivos de entrada de áudio disponíveis."""

from __future__ import annotations

import json

from audio_devices import list_input_devices


def main() -> None:
    devices = list_input_devices()
    print(json.dumps(devices, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
