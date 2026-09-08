"""Export locally stored UI feedback to CSV or JSONL.

Usage:
    python -m backend.export_feedback --format csv --output feedback.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ActiLab feedback.")
    parser.add_argument("--input", default=str(Path(os.getenv("APP_DATA_DIR", "/tmp/actigraphy-ui-data")) / "feedback.jsonl"))
    parser.add_argument("--format", choices=["csv", "jsonl"], default="csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.input)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    records = _read_records(source)

    if args.format == "jsonl":
        with target.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    else:
        fields = sorted({key for record in records for key in record})
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for record in records:
                row = dict(record)
                for key, value in list(row.items()):
                    if isinstance(value, (dict, list)):
                        row[key] = json.dumps(value, ensure_ascii=False, default=str)
                writer.writerow(row)

    print(f"Exported {len(records)} feedback record(s) from {source} to {target}.")


if __name__ == "__main__":
    main()
