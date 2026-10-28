#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py

Rules (see README):
  * Lines that can't be parsed, and events without a txn_id, are ignored.
  * A payment can be attempted several times under the same txn_id; only the
    latest attempt (by `ts`, not by position in the file) counts.
  * A payment is collected only if its latest attempt is `success`.
  * Amounts may be numbers or strings with thousands separators ("4,804.15").
"""
import json
import os
from datetime import datetime
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))


def parse_amount(value):
    """Return the amount as a Decimal, handling numbers and '1,234.56' strings."""
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    return Decimal(str(value))


def parse_ts(value):
    """Parse an ISO-8601 UTC timestamp such as 2026-09-21T15:30:26Z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# txn_id -> (timestamp, event) for the latest attempt seen so far
latest = {}

with open(os.path.join(HERE, "payments.jsonl"), encoding="utf-8") as f:
    for line in f:
        try:
            event = json.loads(line)
        except ValueError:
            continue  # truncated / corrupt line
        if not isinstance(event, dict):
            continue

        txn_id = event.get("txn_id")
        if not txn_id:
            continue  # no transaction id to attach it to

        ts = parse_ts(event["ts"])
        # The export is not in chronological order, so compare timestamps.
        if txn_id not in latest or ts >= latest[txn_id][0]:
            latest[txn_id] = (ts, event)

total = Decimal(0)
count = 0
for _, event in latest.values():
    if event["status"] == "success":
        total += parse_amount(event["amount"])
        count += 1

with open(os.path.join(HERE, "expected.txt")) as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")
