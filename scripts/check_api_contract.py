"""Validate documented examples and security-sensitive Sprint 1 contract rules.

This does not test a running server or prove tenant isolation.
"""
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
spec = yaml.safe_load((ROOT / "docs/api/openapi.yaml").read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validator(schema):
    # Local component refs resolve against the complete OpenAPI document.
    return Draft202012Validator({**spec, **schema})


health = spec["paths"]["/health"]["get"]
plants = spec["paths"]["/plants"]["get"]
forecast_run = spec["paths"]["/forecast-runs/{run_id}"]["get"]
require(health.get("security") == [], "Liveness must explicitly be public")
require(plants.get("security") == [{"bearerAuth": []}], "Plants must require authentication")
require(forecast_run.get("security") == [{"bearerAuth": []}], "Forecast reads must require authentication")
require({"400", "401", "403", "500"} <= plants["responses"].keys(), "Missing error responses")
require({"200", "400", "401", "403", "404", "500"} <= forecast_run["responses"].keys(), "Missing forecast responses")

count = 0
for path, item in spec["paths"].items():
    for method, operation in item.items():
        if method not in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}:
            continue
        for status, response in operation["responses"].items():
            for media in response.get("content", {}).values():
                require("example" in media, f"Missing example: {method} {path} {status}")
                validator(media["schema"]).validate(media["example"])
                count += 1

plant = validator({"$ref": "#/components/schemas/Plant"})
for invalid in [
    {"id": "p", "name": "Plant", "capacityKw": -1},
    {"id": "p", "name": "Plant", "tenant_id": "private"},
    {"id": "", "name": "Plant"},
    {"id": "p"},
]:
    require(not plant.is_valid(invalid), f"Unsafe/invalid plant accepted: {invalid}")

page = validator({"$ref": "#/components/schemas/PlantList"})
page.validate({"data": [], "limit": 50, "offset": 0})
for parameter in plants["parameters"]:
    check = validator(parameter["schema"])
    check.validate(parameter["schema"]["default"])
    require(not check.is_valid(-1), "Negative pagination must be rejected")
    require(not check.is_valid(1.5), "Fractional pagination must be rejected")
    if parameter["name"] == "limit":
        require(not check.is_valid(0), "Zero limit must be rejected")
        require(not check.is_valid(101), "Limit above 100 must be rejected")

print(f"Validated {count} response examples, empty page, security and negative contract cases.")
