"""Check the reviewable Sprint 2 documentation bundle, not forecast accuracy."""
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ML_FILES = (
    "README.md", "forecasting-methodology.md", "weather-provider-assumptions.md",
    "model-registry.md", "feature-pipeline.md", "quality-metrics.md",
    "ml-operations-checklist.md", "provider-failover.md", "forecast-validation.md",
    "weather-provider-integration.md", "ml-ops-checklist.md", "forecast-quality-qa.md",
)
TRACKING = ("README.md", "STATUS.md", "SOURCES.md", "ACCEPTANCE.md")
paths = [ROOT / "docs/ml" / name for name in ML_FILES]
paths += [ROOT / "sprint-02" / name for name in TRACKING]
errors = []
for path in paths:
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        errors.append(f"Missing or empty: {path.relative_to(ROOT)}")
        continue
    content = path.read_text(encoding="utf-8")
    if "#10" not in content:
        errors.append(f"Missing epic traceability: {path.relative_to(ROOT)}")
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith("#"):
            continue
        resolved = (path.parent / unquote(parsed.path)).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.is_file():
            errors.append(f"Broken local link: {path.relative_to(ROOT)} -> {target}")

manifest_path = ROOT / "sprint-02/source-manifest.json"
try:
    documents = json.loads(manifest_path.read_text(encoding="utf-8"))["documents"]
    expected = {f"HEDS-{n}" for n in ("010", "011", "012", "018", "022", "023")}
    if len(documents) != 6 or {d["document_id"] for d in documents} != expected:
        errors.append("Source manifest must contain each of the six HEDS documents once")
    coverage = (ROOT / "sprint-02/SOURCES.md").read_text(encoding="utf-8")
    for document in documents:
        if document["document_id"] not in coverage:
            errors.append(f"Missing coverage row: {document['document_id']}")
        for field in ("archive_sha256", "markdown_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", document[field]):
                errors.append(f"Invalid {field}: {document['document_id']}")
        if not document["markdown_entry"].startswith("releases/md/"):
            errors.append(f"Missing primary source entry: {document['document_id']}")
        if not document["url"].startswith("https://drive.google.com/file/d/"):
            errors.append(f"Missing source URL: {document['document_id']}")
        if not document["version"] or not document["reviewed"]:
            errors.append(f"Missing source version/review date: {document['document_id']}")
except (OSError, ValueError, KeyError, TypeError) as error:
    errors.append(f"Invalid source manifest or coverage: {error}")

if errors:
    raise SystemExit("\n".join(errors))
print(f"Validated {len(paths)} documentation files, local links and six source records.")
print("Archive bytes were checked at intake; CI validates manifest structure only.")
print("Forecast runtime, historical accuracy and sign-off are separate acceptance gates.")
