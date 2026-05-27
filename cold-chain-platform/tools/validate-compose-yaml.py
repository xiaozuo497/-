from pathlib import Path

import yaml


path = Path(__file__).resolve().parents[1] / "docker-compose.yml"
data = yaml.safe_load(path.read_text(encoding="utf-8"))
required = {"postgres", "redis", "api", "frontend"}
services = set(data.get("services", {}))
missing = required - services

if missing:
    raise SystemExit(f"Missing required services: {', '.join(sorted(missing))}")

for name in required:
    if not isinstance(data["services"][name], dict):
        raise SystemExit(f"Service {name} must be a mapping")

print("compose yaml structure ok:", ", ".join(sorted(services)))

