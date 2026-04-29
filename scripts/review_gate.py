#!/usr/bin/env python3
"""
KRX Post-Market Review — STRICT DATE GATE
Prevents review generation before market close.
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# KRX closes at 15:30 KST (06:30 UTC)
KRX_CLOSE_HOUR_KST = 15
KRX_CLOSE_MIN_KST = 30
KRX_CLOSE_HOUR_UTC = 6
KRX_CLOSE_MIN_UTC = 30

# KRX 2026 holidays
KRX_HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-02",
    "2026-02-16", "2026-02-17", "2026-02-18",
    "2026-03-01", "2026-05-01", "2026-05-05",
    "2026-06-06", "2026-08-15",
    "2026-09-28", "2026-09-29", "2026-09-30",
    "2026-10-03", "2026-10-05",
    "2026-12-25", "2026-12-31",
}

def now_kst():
    return datetime.now(timezone.utc) + timedelta(hours=9)

def is_krx_open(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = dt.weekday()
    if weekday >= 5:
        return False, f"Weekend ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][weekday]})"
    if date_str in KRX_HOLIDAYS_2026:
        return False, f"Holiday ({date_str})"
    return True, "Trading day"

def can_review_today():
    """
    Returns (ok, kst_date, reason)
    ok = True only if:
      1. Today is a KRX trading day
      2. Current UTC time >= 06:30 (KRX close)
      3. Brief file exists for today
    """
    kst_now = now_kst()
    kst_date = kst_now.strftime("%Y-%m-%d")
    utc_now = datetime.now(timezone.utc)

    # Gate 1: Is KRX open today?
    open_ok, open_reason = is_krx_open(kst_date)
    if not open_ok:
        return False, kst_date, f"KRX closed today — {open_reason}"

    # Gate 2: Has KRX closed for the day?
    # KRX closes at 06:30 UTC. Before that, NO REVIEW.
    utc_close = utc_now.replace(hour=KRX_CLOSE_HOUR_UTC, minute=KRX_CLOSE_MIN_UTC, second=0, microsecond=0)
    if utc_now < utc_close:
        minutes_until = int((utc_close - utc_now).total_seconds() / 60)
        return False, kst_date, f"KRX market still open. Review allowed in {minutes_until} minutes (at 06:30 UTC / 15:30 KST). Current UTC: {utc_now.strftime('%H:%M')}."

    # Gate 3: Does morning brief exist?
    brief_paths = [
        f"/tmp/krx-news/briefs/{kst_date}.md",
        f"/tmp/korean-exchange-market-news/briefs/{kst_date}.md",
    ]
    brief_found = None
    for p in brief_paths:
        if os.path.exists(p):
            brief_found = p
            break
    if not brief_found:
        return False, kst_date, f"Morning brief not found for {kst_date} (checked {brief_paths})"

    return True, kst_date, f"All gates passed. Brief: {brief_found}"

if __name__ == "__main__":
    ok, kst_date, reason = can_review_today()
    print(f"KST_DATE={kst_date}")
    print(f"STATUS={'PASS' if ok else 'BLOCK'}")
    print(f"REASON={reason}")
    if ok:
        brief_paths = [
            f"/tmp/krx-news/briefs/{kst_date}.md",
            f"/tmp/korean-exchange-market-news/briefs/{kst_date}.md",
        ]
        for p in brief_paths:
            if os.path.exists(p):
                print(f"BRIEF_PATH={p}")
                break
        print(f"REVIEW_PATH=/tmp/krx-news/reviews/{kst_date}.md")
        sys.exit(0)
    else:
        sys.exit(1)
