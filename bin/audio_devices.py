"""Descoberta de dispositivos de entrada de áudio."""

from __future__ import annotations

from typing import Any

import pyaudio


def list_input_devices() -> list[dict[str, Any]]:
    audio = pyaudio.PyAudio()
    devices: list[dict[str, Any]] = []

    try:
        default_index = None
        try:
            default_index = int(audio.get_default_input_device_info()["index"])
        except Exception:
            pass

        for index in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(index)
            max_inputs = int(info.get("maxInputChannels", 0) or 0)
            if max_inputs <= 0:
                continue

            devices.append({
                "index": index,
                "name": str(info.get("name", f"Device {index}")),
                "max_input_channels": max_inputs,
                "default_sample_rate": int(float(info.get("defaultSampleRate", 0) or 0)),
                "is_default": index == default_index,
            })
    finally:
        audio.terminate()

    return devices
