"""
Aggregate all four DORA metrics in a single run and write to JSON.

Usage:
    GITHUB_TOKEN=<token> GITHUB_REPO=org/repo PAGERDUTY_TOKEN=<token> \
        python collect_all.py

Output is written to /tmp/dora-metrics.json (override with METRICS_OUTPUT env var).
Downstream steps (Slack posting, dashboards) read from that file.
"""

import json
import os
import sys
from datetime import datetime

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lead_time import calculate_lead_time
from change_failure_rate import calculate_cfr
from mttr import calculate_mttr


def collect_all(repo_name: str = None, days_back: int = 30) -> dict:
    """Collect all four DORA metrics and return a combined result dict."""
    repo = repo_name or os.environ["GITHUB_REPO"]

    print(f"Collecting DORA metrics for {repo} (last {days_back} days)...")

    lead_time = calculate_lead_time(repo, days_back=days_back)
    cfr = calculate_cfr(days_back=days_back)
    mttr = calculate_mttr(days_back=days_back)

    # Deployment frequency: deployments per week derived from CFR's deployment count
    deployment_frequency_per_week = round(cfr["deployments"] / (days_back / 7), 1)

    result = {
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "period_days": days_back,
        "repo": repo,
        "metrics": {
            "deployment_frequency_per_week": deployment_frequency_per_week,
            "lead_time_avg_hours": lead_time["avg_hours"],
            "lead_time_p95_hours": lead_time["p95_hours"],
            "change_failure_rate_pct": cfr["rate_pct"],
            "mttr_avg_minutes": mttr["avg_minutes"],
            "mttr_median_minutes": mttr["median_minutes"],
            "open_p1_incidents": mttr["open_p1"],
        },
        "raw": {
            "lead_time": lead_time,
            "cfr": cfr,
            "mttr": mttr,
        },
    }

    output_path = os.environ.get("METRICS_OUTPUT", "/tmp/dora-metrics.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Metrics written to {output_path}")
    return result


if __name__ == "__main__":
    result = collect_all()
    print(json.dumps(result["metrics"], indent=2))
