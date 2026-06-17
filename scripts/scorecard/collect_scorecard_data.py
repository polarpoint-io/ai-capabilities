"""
Collect all six platform scorecard metrics via GitHub + PagerDuty.

Usage:
    GITHUB_TOKEN=<token> GITHUB_REPO=org/repo PAGERDUTY_TOKEN=<token> \
        python collect_scorecard_data.py

Output written to /tmp/scorecard-data.json (override with SCORECARD_DATA env var).
The generate_scorecard.py step reads from this file.

Metrics collected:
    - Deployment frequency (deployments per week)
    - P95 lead time (hours, first commit to production)
    - Change failure rate (%)
    - MTTR median (minutes)
    - Platform request backlog (open GitHub Issues with 'platform-request' label)
    - Open P1 incidents
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

# Allow sibling imports when called from repo root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "metrics"))

from lead_time import calculate_lead_time
from change_failure_rate import calculate_cfr
from mttr import calculate_mttr


@dataclass
class ScorecardData:
    period_start: str
    period_end: str
    deployment_frequency: float       # deployments per week
    lead_time_p95_hours: float
    change_failure_rate_pct: float
    mttr_median_minutes: float
    platform_backlog_count: int
    open_p1_incidents: int
    slo_attainment_pct: float         # provide via PROMETHEUS_URL or set manually


def count_open_platform_requests() -> int:
    """Count open GitHub Issues labelled 'platform-request'."""
    from github import Github

    g = Github(os.environ["GITHUB_TOKEN"])
    repo = g.get_repo(os.environ["GITHUB_REPO"])
    return repo.get_issues(state="open", labels=["platform-request"]).totalCount


def query_slo_attainment(start: datetime, end: datetime) -> float:
    """Query SLO attainment from Prometheus/Grafana if configured, else return 0."""
    prometheus_url = os.environ.get("PROMETHEUS_URL")
    if not prometheus_url:
        return 0.0

    import requests

    # Example: query overall error budget remaining across all SLOs
    query = 'avg(slo:sli_error:ratio_rate30d) * 100'
    resp = requests.get(
        f"{prometheus_url}/api/v1/query",
        params={"query": query, "time": end.isoformat()},
        timeout=10,
    )
    result = resp.json().get("data", {}).get("result", [])
    if result:
        return round(float(result[0]["value"][1]), 1)
    return 0.0


def collect_monthly_data(months_back: int = 1) -> ScorecardData:
    """Collect all scorecard metrics for the last N months."""
    end = datetime.utcnow()
    start = end - timedelta(days=30 * months_back)

    lead_time = calculate_lead_time(os.environ["GITHUB_REPO"], days_back=30 * months_back)
    cfr = calculate_cfr(days_back=30 * months_back)
    mttr = calculate_mttr(days_back=30 * months_back)

    backlog = count_open_platform_requests()
    slo = query_slo_attainment(start, end)

    return ScorecardData(
        period_start=start.strftime("%Y-%m-%d"),
        period_end=end.strftime("%Y-%m-%d"),
        deployment_frequency=round(cfr["deployments"] / (30 * months_back / 7), 1),
        lead_time_p95_hours=lead_time["p95_hours"],
        change_failure_rate_pct=cfr["rate_pct"],
        mttr_median_minutes=mttr["median_minutes"],
        platform_backlog_count=backlog,
        open_p1_incidents=mttr["open_p1"],
        slo_attainment_pct=slo,
    )


if __name__ == "__main__":
    current = collect_monthly_data(months_back=1)
    previous = collect_monthly_data(months_back=2)

    output = {
        "current": asdict(current),
        "previous": asdict(previous),
    }

    output_path = os.environ.get("SCORECARD_DATA", "/tmp/scorecard-data.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Scorecard data written to {output_path}")
    print(json.dumps(asdict(current), indent=2))
