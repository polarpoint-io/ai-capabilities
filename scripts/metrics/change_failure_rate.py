"""
Change failure rate — percentage of deployments that caused an incident within 1 hour.

Usage:
    GITHUB_TOKEN=<token> GITHUB_REPO=org/repo PAGERDUTY_TOKEN=<token> \
        python change_failure_rate.py

Returns a dict with rate_pct, failure count, deployment count, and incident count.
"""

import os
import requests
from datetime import datetime, timedelta

from github import Github


def calculate_cfr(days_back: int = 30) -> dict:
    """Calculate change failure rate from GitHub deployments and PagerDuty incidents.

    A deployment is considered a failure if a PagerDuty incident was created
    within 1 hour of the deployment completing.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=days_back)

    # --- PagerDuty incidents ---
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

    # --- GitHub deployments ---
    g = Github(os.environ["GITHUB_TOKEN"])
    repo = g.get_repo(os.environ["GITHUB_REPO"])

    deployments = [
        d
        for d in repo.get_deployments(environment="production")
        if d.created_at > start.replace(tzinfo=None)
    ]

    # --- Correlation: incident within 1 hour of a deployment = failure ---
    failure_count = 0
    for incident in incidents:
        incident_time = datetime.fromisoformat(
            incident["created_at"].replace("Z", "")
        )
        for deployment in deployments:
            deploy_time = deployment.created_at.replace(tzinfo=None)
            if 0 <= (incident_time - deploy_time).total_seconds() <= 3600:
                failure_count += 1
                break

    cfr = (failure_count / len(deployments) * 100) if deployments else 0.0

    return {
        "metric": "change_failure_rate",
        "rate_pct": round(cfr, 1),
        "failures": failure_count,
        "deployments": len(deployments),
        "incidents": len(incidents),
    }


if __name__ == "__main__":
    import json

    result = calculate_cfr()
    print(json.dumps(result, indent=2))
