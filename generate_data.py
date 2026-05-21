#!/usr/bin/env python3
"""
Fetch Google Sheets data and generate per-partner JSON files.
Each partner gets a unique token-named JSON file containing only their data.
Token mapping is stored in PARTNER_TOKENS GitHub Secret.
"""
import csv
import io
import json
import os
import urllib.request

SHEET_ID = "1TtkspzT2Ng9Mm9Kp7EOPBx-ns2eDY5Mbvixt5tL_LcU"
SHEET_GID = "1331996880"


def fetch_sheet():
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&gid={SHEET_GID}&headers=1"
    )
    with urllib.request.urlopen(url) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    # Clean header names: strip whitespace, remove extra text after known headers
    clean = []
    for f in reader.fieldnames:
        c = f.strip()
        # Handle headers with appended content (e.g. "No 관리자 대시보드" → "No")
        for known in ["No", "\ub300\uc2dc\ubcf4\ub4dc URL", "\ub300\uc2dc\ubcf4\ub4dc \uc804\ub2ec"]:
            if c.startswith(known) and len(c) > len(known):
                c = known
                break
        clean.append(c)
    reader.fieldnames = clean
    rows = []
    for row in reader:
        name = row.get("\ud30c\ud2b8\ub108\uba85", "").strip()
        if name:
            rows.append(dict(row))
    return rows


def main():
    tokens_json = os.environ.get("PARTNER_TOKENS", "{}")
    tokens = json.loads(tokens_json)  # {partner_name: token}

    # Reverse map: token -> partner_name
    token_to_name = {v: k for k, v in tokens.items()}

    rows = fetch_sheet()

    os.makedirs("data", exist_ok=True)

    # Remove columns that shouldn't be exposed to partners
    hidden_cols = {
        "\ub300\uc2dc\ubcf4\ub4dc URL",
        "\ub300\uc2dc\ubcf4\ub4dc \uc804\ub2ec",
    }

    generated = 0
    for token, partner_name in token_to_name.items():
        matched = [r for r in rows if r.get("\ud30c\ud2b8\ub108\uba85", "").strip() == partner_name]
        if not matched:
            print(f"  WARN: no data for '{partner_name}', skipping")
            continue

        partner_data = {}
        for k, v in matched[0].items():
            if k and k not in hidden_cols:
                partner_data[k] = v.strip() if isinstance(v, str) else v

        out_path = os.path.join("data", f"{token}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(partner_data, f, ensure_ascii=False, indent=2)

        generated += 1
        print(f"  OK: {partner_name} -> data/{token}.json")

    # Write a minimal index for validation (no partner info)
    meta = {"count": generated, "status": "ok"}
    with open(os.path.join("data", "meta.json"), "w") as f:
        json.dump(meta, f)

    print(f"\nGenerated {generated} partner files")


if __name__ == "__main__":
    main()
