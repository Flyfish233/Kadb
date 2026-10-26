#!/usr/bin/env python3
"""Choose an installed iPhone simulator and record its actual runtime/UDID."""
import json
import subprocess
from pathlib import Path

data = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "available", "--json"]))
choices = [(runtime, device) for runtime, devices in data["devices"].items()
           if ".iOS-" in runtime for device in devices if device["name"].startswith("iPhone")]
if not choices:
    raise SystemExit("No available iPhone simulator runtime; no simulator coverage can be claimed")
runtime, device = sorted(choices, key=lambda item: (item[0], item[1]["name"]), reverse=True)[0]
initial_state = device["state"]
if device["state"] != "Booted":
    subprocess.run(["xcrun", "simctl", "boot", device["udid"]], check=True)
subprocess.run(["xcrun", "simctl", "bootstatus", device["udid"], "-b"], check=True)
observed = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "available", "--json"]))
device = next(item for item in observed["devices"][runtime] if item["udid"] == device["udid"])
if device["state"] != "Booted":
    raise SystemExit("Simulator bootstatus completed without an observed Booted device")
Path("evidence").mkdir(exist_ok=True)
Path("evidence/simulator.json").write_text(json.dumps({"runtime": runtime, "initial_state": initial_state, **device}, indent=2) + "\n")
Path("evidence/simulator-udid.txt").write_text(device["udid"] + "\n")
print(f"Booted {device['name']} ({runtime}), UDID {device['udid']}")
