#!/usr/bin/env python3
"""
KRX Post-Market Review Script
Evaluates morning brief against actual market outcomes.
Run after KRX market close (15:30 KST / 06:30 UTC).
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path

# KRX 2026 holidays
KRX_HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-02",
    "2026-02-16", "2026-02-17", "2026-02-18",
    "2026-03-01",
    "2026-05-01", "2026-05-05",
    "2026-06-06",
    "2026-08-15",
    "2026-09-28", "2026-09-29", "2026-09-30",
    "2026-10-03", "2026-10-05",
    "2026-12-25", "2026-12-31",
}

def get_kst_date():
    """Get current date in KST (UTC+9)"""
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    return now.strftime("%Y-%m-%d")

def is_krx_open(date_str):
    """Check if KRX is open on given date"""
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    weekday = dt.weekday()
    if weekday >= 5:  # Saturday=5, Sunday=6
        return False, f"Weekend ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][weekday]})"
    if date_str in KRX_HOLIDAYS_2026:
        return False, f"Holiday ({date_str})"
    return True, "Trading day"

def find_brief(date_str):
    """Find morning brief file for the date"""
    paths = [
        f"/tmp/krx-news/briefs/{date_str}.md",
        f"/tmp/korean-exchange-market-news/briefs/{date_str}.md",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def git_setup():
    """Ensure git auth is configured"""
    gh_path = os.path.expanduser("~/.local/bin/gh")
    if os.path.exists(gh_path):
        subprocess.run([gh_path, "auth", "setup-git", "--hostname", "github.com"], 
                      capture_output=True)

def git_push_review(review_path, date_str, score):
    """Commit and push review to GitHub"""
    repo_path = "/tmp/krx-news"
    os.chdir(repo_path)
    
    # Setup git auth
    git_setup()
    
    # Add, commit, push
    subprocess.run(["git", "add", review_path], capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", f"Post-market review: {date_str} — Score: {score}/100"],
        capture_output=True, text=True
    )
    if result.returncode != 0 and "nothing to commit" not in result.stderr:
        print(f"Git commit warning: {result.stderr}")
    
    push_result = subprocess.run(["git", "push", "origin", "main"], 
                                  capture_output=True, text=True)
    if push_result.returncode != 0:
        print(f"Push failed: {push_result.stderr}")
        return False
    return True

def main():
    # Get KST date
    kst_date = get_kst_date()
    print(f"KST Date: {kst_date}")
    
    # Check if KRX was open
    is_open, reason = is_krx_open(kst_date)
    if not is_open:
        print(f"SKIP: KRX closed today — {reason}")
        sys.exit(0)
    
    # Find morning brief
    brief_path = find_brief(kst_date)
    if not brief_path:
        print(f"SKIP: Morning brief not found for {kst_date}")
        sys.exit(0)
    
    print(f"Found brief: {brief_path}")
    
    # Read brief content
    with open(brief_path, 'r') as f:
        brief_content = f.read()
    
    # Ensure reviews directory exists
    reviews_dir = Path("/tmp/krx-news/reviews")
    reviews_dir.mkdir(parents=True, exist_ok=True)
    
    review_path = reviews_dir / f"{kst_date}.md"
    
    # The actual review generation is done by the LLM in the cron prompt
    # This script just handles the pre-checks and post-processing
    print(f"Brief ready for review. Output path: {review_path}")
    print(f"Brief length: {len(brief_content)} chars")
    
    # Return info for the LLM to use
    print(f"\nBRIEF_PATH={brief_path}")
    print(f"REVIEW_PATH={review_path}")
    print(f"KST_DATE={kst_date}")
    print(f"KRX_STATUS=OPEN")

if __name__ == "__main__":
    main()
