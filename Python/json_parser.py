import re
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any

# =========================
# HARD CODED FILE PATHS
# =========================
INPUT_EXCEL_FILE = r"C:\Users\YourName\Documents\Calico\calico_logs.xlsx"
OUTPUT_JSON_FILE = r"C:\Users\YourName\Documents\Calico\calico_logs_parsed.json"

# Name of the Excel column that contains the raw log lines
INPUT_COLUMN = "raw_log"

# Optional: sheet name
SHEET_NAME = 0   # first sheet
# SHEET_NAME = "Sheet1"  # use this instead if you want a sheet by name


# Example Calico log:
# 2026-02-12 22:56:51.716 [INFO][57971] cni-plugin/k8s.go 659: Releasing IP address(es) ContainerID="abc123"

LOG_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)'
    r'\s+\[(?P<level>[A-Z]+)\]'
    r'\[(?P<pid>\d+)\]'
    r'\s+(?P<source>\S+)'
    r'\s+(?P<source_line>\d+):'
    r'\s+(?P<rest>.*)$'
)

KV_PATTERN = re.compile(
    r'(?P<key>[A-Za-z0-9_.-]+)='
    r'(?P<value>"(?:[^"\\]|\\.)*"|\S+)'
)


def try_convert_value(value: str) -> Any:
    if isinstance(value, str):
        lower = value.lower()

        if lower == "true":
            return True
        if lower == "false":
            return False
        if lower == "null":
            return None

        if re.fullmatch(r"-?\d+", value):
            try:
                return int(value)
            except ValueError:
                pass

        if re.fullmatch(r"-?\d+\.\d+", value):
            try:
                return float(value)
            except ValueError:
                pass

    return value


def extract_kv_pairs(text: str) -> Dict[str, Any]:
    parsed = {}

    for match in KV_PATTERN.finditer(text):
        key = match.group("key")
        value = match.group("value")

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
            value = value.replace('\\"', '"')

        parsed[key] = try_convert_value(value)

    return parsed


def remove_kv_pairs_from_message(text: str) -> str:
    cleaned = KV_PATTERN.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def parse_calico_line(line: str) -> Dict[str, Any]:
    line = str(line).strip()

    if not line:
        return {
            "parse_status": "empty",
            "raw_log": line
        }

    match = LOG_PATTERN.match(line)
    if not match:
        return {
            "parse_status": "unparsed",
            "raw_log": line
        }

    timestamp = match.group("timestamp")
    level = match.group("level")
    pid = int(match.group("pid"))
    source = match.group("source")
    source_line = int(match.group("source_line"))
    rest = match.group("rest")

    kv_pairs = extract_kv_pairs(rest)
    message = remove_kv_pairs_from_message(rest)

    record = {
        "parse_status": "parsed",
        "timestamp": timestamp,
        "level": level,
        "process_id": pid,
        "component_file": source,
        "component_line": source_line,
        "message": message,
        "raw_log": line
    }

    for key, value in kv_pairs.items():
        if key in record:
            record[f"calico_{key}"] = value
        else:
            record[key] = value

    return record


def main():
    input_path = Path(INPUT_EXCEL_FILE)
    output_path = Path(OUTPUT_JSON_FILE)

    if not input_path.exists():
        raise FileNotFoundError(f"Input Excel file not found: {input_path}")

    # Read Excel
    df = pd.read_excel(input_path, sheet_name=SHEET_NAME)

    if INPUT_COLUMN not in df.columns:
        raise ValueError(
            f"Column '{INPUT_COLUMN}' not found in Excel file. "
            f"Available columns: {list(df.columns)}"
        )

    parsed_records = []

    for raw_line in df[INPUT_COLUMN]:
        if pd.isna(raw_line):
            continue
        parsed_records.append(parse_calico_line(raw_line))

    # Write full JSON array output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed_records, f, indent=2, ensure_ascii=False)

    total = len(parsed_records)
    parsed = sum(1 for r in parsed_records if r.get("parse_status") == "parsed")
    unparsed = sum(1 for r in parsed_records if r.get("parse_status") == "unparsed")
    empty = sum(1 for r in parsed_records if r.get("parse_status") == "empty")

    print(f"Input Excel file: {input_path}")
    print(f"Output JSON file: {output_path}")
    print(f"Total records processed: {total}")
    print(f"Parsed: {parsed}")
    print(f"Unparsed: {unparsed}")
    print(f"Empty: {empty}")


if __name__ == "__main__":
    main()