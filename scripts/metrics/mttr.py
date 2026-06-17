"""
MTTR (Mean Time to Restore) — time from incident creation to resolution.

Usage:
    PAGERDUTY_TOKEN=<token> python mttr.py

Returns a dict with avg_minutes, median_minutes, sample count, and open P1 count.
This script is provider-agnostic: it reads from PagerDuty regardless of whether
your Git provider is GitHub or Azure DevOps.
"""

import os
import requests
from datetime import datetime, timedelta


def calculate_mttr(days_back: int = 30) -> dict:
    """Calculate MTTR from PagerDuty incident created_at to resolved_at.

    Also returns the count of currently-open P1 (high urgency) incidents
    so callers can surface it in scorecards.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=days_back)

    headers = {
        "Authorization": f"Token token={os.environ['PAGERDUTY_TOKEN']}",
        "Accept": "application/vnd.pagerduty+json;version=2",
    }

    incidents = []
    offset = 0
    while True:
        resp = requests.get(
            "https://api.pagerduty.com/incidents",
            headers=headers,
            params={
                "since": start.isoformat(),
                "until": end.isoformat(),
                "offset": offset,
                "limit": 100,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        incidents.extend(data["incidents"])
        if not data.get("more"):
            break
        offset += 100

    resolution_times = []
    for incident in incidents:
        if incident["status"] == "resolved" and incident.get("resolved_at"):
            created = datetime.fromisoformat(
                incident["created_at"].replace("Z", "")
            )
            resolved = datetime.fromisoformat(
                incident["resolved_at"].replace("Z", "")
            )
            mttr_minutes = (resolved - created).total_seconds() / 60
            resolution_times.append(mttr_minutes)

    if resolution_times:
        sorted_times = sorted(resolution_times)
        avg = sum(sorted_times) / len(sorted_times)
        p50 = sorted_times[len(sorted_times) // 2]
    else:
        avg = p50 = 0.0

    # Open P1s (high urgency, not yet resolved) as at query time
    open_p1 = sum(
        1
        for i in incidents
        if i["status"] != "resolved" and i.get("urgency") == "high"
    )

    return {
        "metric": "mttr",
        "avg_minutes": round(avg, 0),
        "median_minutes": round(p50, 0),
        "sample_count": len(resolution_times),
        "open_p1": open_p1,
    }


if __name__ == "__main__":
    import json

    result = calculate_mttr()
    print(json.dumps(result, indent=2))
