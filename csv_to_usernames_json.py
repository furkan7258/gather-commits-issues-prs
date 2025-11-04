#!/usr/bin/env python3
import argparse
import csv
import json
import sys
from pathlib import Path

def get_args():
    p = argparse.ArgumentParser(description="Convert a CSV with student/user data to github-usernames.json mapping")
    p.add_argument("csv", help="Path to input CSV file")
    p.add_argument("-o", "--output", default="github-usernames.json", help="Output JSON path (default: github-usernames.json)")
    p.add_argument("--username-column", default="GitHub username", help="Header name for the GitHub username column (case-insensitive)")
    p.add_argument("--first-name-column", default="First name", help="Header name for the first name column (case-insensitive)")
    p.add_argument("--last-name-column", default="Last name", help="Header name for the last name column (case-insensitive)")
    return p.parse_args()


def normalize_header(name: str) -> str:
    return (name or "").strip().lower()


def main():
    args = get_args()
    src = Path(args.csv)
    if not src.exists():
        print(f"ERROR: CSV not found: {src}", file=sys.stderr)
        sys.exit(1)

    # Read CSV with UTF-8 BOM tolerance
    with src.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("ERROR: CSV has no header row", file=sys.stderr)
            sys.exit(1)

        # Build a case-insensitive header map
        header_map = {normalize_header(h): h for h in reader.fieldnames}

        uname_key_norm = normalize_header(args.username_column)
        first_key_norm = normalize_header(args.first_name_column)
        last_key_norm = normalize_header(args.last_name_column)

        # Try to find actual header keys present in CSV
        uname_key = header_map.get(uname_key_norm)
        first_key = header_map.get(first_key_norm)
        last_key = header_map.get(last_key_norm)

        if not uname_key:
            print(f"ERROR: Username column '{args.username_column}' not found in CSV headers: {reader.fieldnames}", file=sys.stderr)
            sys.exit(1)
        if not first_key or not last_key:
            print(f"WARNING: First/Last name columns not found exactly as specified; attempting to infer common variants...", file=sys.stderr)
            # Attempt simple inference
            for h in reader.fieldnames:
                h_norm = normalize_header(h)
                if not first_key and h_norm in ("firstname", "first name", "given name", "givenname"):
                    first_key = h
                if not last_key and h_norm in ("lastname", "last name", "surname", "family name", "familyname"):
                    last_key = h
            if not first_key or not last_key:
                print(f"ERROR: Could not locate first/last name columns. Headers: {reader.fieldnames}", file=sys.stderr)
                sys.exit(1)

        mapping = {}
        for row in reader:
            uname = (row.get(uname_key) or "").strip()
            if not uname:
                continue
            if uname.startswith("@"):  # clean @username
                uname = uname[1:]
            first = (row.get(first_key) or "").strip()
            last = (row.get(last_key) or "").strip()
            full = (first + " " + last).strip() or uname
            mapping[uname] = full

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(mapping)} mappings to {out}")


if __name__ == "__main__":
    main()
