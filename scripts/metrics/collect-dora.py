#!/usr/bin/env python3
"""
Collect DORA metrics from GitHub and PagerDuty.

Usage:
    python scripts/metrics/collect-dora.py --days 30

Requires:
    GITHUB_TOKEN, GITHUB_REPO, PAGERDUTY_TOKEN environment variables.

Output:
    /tmp/dora-metrics.json
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta, timezone


def parse_args():
    parser = argparse.ArgumentParser(description="Collect DORA metrics")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyse")
    parser.add_argument("--output", default="/tmp/dora-metrics.json", help="Output file path")
    return parser.parse_args()


def github_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable required")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def pagerduty_headers() -> dict:
    token = os.environ.get("PAGERDUTY_TOKEN")
    if not token:
        raise ValueError("PAGERDUTY_TOKEN environment variable required")
    return {
        "Authorization": f"Token token={token}",
        "Accept": "application/vnd.pagerduty+json;version=2",
    }


def get_production_deployments(repo: str, since: datetime) -> list:
    """Get all production deployments in the time window."""
    headers = github_headers()
    deployments = []
    page = 1

    while True:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/deployments",
            headers=headers,
            params={"environment": "production", "per_page": 100, "page": page},
        )
        resp.raise_for_status()
        page_data = resp.json()
        if not page_data:
            break

        for d in page_data:
            created = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
            if created < since:
                return deployments
            deployments.append(d)

        page += 1

    return deployments


def get_lead_time(repo: str, deployments: list) -> dict:
    """Calculate lead time from first commit to production deployment."""
    headers = github_headers()
    lead_times = []

    for deployment in deployments[:30]:  # cap at 30 to avoid rate limits
        sha = deployment["sha"]
        deploy_time = datetime.fromisoformat(
            deployment["created_at"].replace("Z", "+00:00")
        )

        # Get the commit date as a proxy for first commit
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/commits/{sha}",
            headers=headers,
        )
        if resp.status_code != 200:
            continue

        commit_data = resp.json()
        commit_time_str = commit_data["commit"]["author"]["date"]
        commit_time = datetime.fromisoformat(commit_time_str.replace("Z", "+00:00"))

        lead_time_hours = (deploy_time - commit_time).total_seconds() / 3600
        if lead_time_hours > 0:
            lead_times.append(lead_time_hours)

    if not lead_times:
        return {"avg_hours": 0, "p95_hours": 0, "sample_count": 0}

    sorted_times = sorted(lead_times)
    avg = sum(lead_times) / len(lead_times)
    p95_idx = int(len(sorted_times) * 0.95)
    p95 = sorted_times[min(p95_idx, len(sorted_times) - 1)]

    return {
        "avg_hours": round(avg, 1),
        "p95_hours": round(p95, 1),
        "sample_count": len(lead_times),
    }


def get_pagerduty_incidents(since: datetime, until: datetime) -> list:
    """Get all PagerDuty incidents in the time window."""
    headers = pagerduty_headers()
    incidents = []
    offset = 0

    while True:
        resp = requests.get(
            "https://api.pagerduty.com/incidents",
            headers=headers,
            params={
                "since": since.isoformat(),
                "until": until.isoformat(),
                "offset": offset,
                "limit": 100,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        incidents.extend(data.get("incidents", []))

        if not data.get("more"):
            break
        offset += 100

    return incidents


def calculate_change_failure_rate(deployments: list, incidents: list) -> dict:
    """
    Estimate CFR by checking if an incident was created within 1 hour of a deployment.
    This is an approximation - precise CFR requires deployment-incident correlation in your tooling.
    """
    failure_count = 0

    for incident in incidents:
        incident_time_str = incident.get("created_at", "")
        if not incident_time_str:
            continue
        incident_time = datetime.fromisoformat(incident_time_str.replace("Z", "+00:00"))

        for deployment in deployments:
            deploy_time = datetime.fromisoformat(
                deployment["created_at"].replace("Z", "+00:00")
            )
            delta_seconds = (incident_time - deploy_time).total_seconds()
            if 0 <= delta_seconds <= 3600:  # within 1 hour of deployment
                failure_count += 1
                break

    total = len(deployments)
    rate = (failure_count / total * 100) if total > 0 else 0.0

    return {
        "rate_pct": round(rate, 1),
        "failures": failure_count,
        "deployments": total,
        "incidents_total": len(incidents),
    }


def calculate_mttr(incidents: list) -> dict:
    """Calculate MTTR from incident created_at to resolved_at."""
    resolution_times = []

    for incident in incidents:
        if incident.get("status") != "resolved":
            continue
        resolved_at = incident.get("resolved_at")
        if not resolved_at:
            continue

        created = datetime.fromisoformat(incident["created_at"].replace("Z", "+00:00"))
        resolved = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        minutes = (resolved - created).total_seconds() / 60
        if minutes > 0:
            resolution_times.append(minutes)

    if not resolution_times:
        return {"avg_minutes": 0, "median_minutes": 0, "sample_count": 0}

    sorted_times = sorted(resolution_times)
    avg = sum(resolution_times) / len(resolution_times)
    median = sorted_times[len(sorted_times) // 2]

    return {
        "avg_minutes": round(avg, 0),
        "median_minutes": round(median, 0),
        "sample_count": len(resolution_times),
    }


def main():
    args = parse_args()

    repo = os.environ.get("GITHUB_REPO")
    if not repo:
        print("ERROR: GITHUB_REPO environment variable required (format: org/repo)")
        sys.exit(1)

    until = datetime.now(timezone.utc)
    since = until - timedelta(days=args.days)

    print(f"Collecting DORA metrics for {repo}")
    print(f"Period: {since.date()} to {until.date()}")
    print()

    print("Fetching production deployments...")
    deployments = get_production_deployments(repo, since)
    print(f"  Found {len(deployments)} deployments")

    print("Fetching PagerDuty incidents...")
    incidents = get_pagerduty_incidents(since, until)
    print(f"  Found {len(incidents)} incidents")

    print("Calculating lead time...")
    lead_time = get_lead_time(repo, deployments)

    print("Calculating change failure rate...")
    cfr = calculate_change_failure_rate(deployments, incidents)

    print("Calculating MTTR...")
    mttr = calculate_mttr(incidents)

    weeks = args.days / 7
    freq_per_week = len(deployments) / weeks if weeks > 0 else 0

    result = {
        "period": {
            "start": since.date().isoformat(),
            "end": until.date().isoformat(),
            "days": args.days,
        },
        "lead_time": lead_time,
        "deployment_frequency": {
            "per_week": round(freq_per_week, 1),
            "total": len(deployments),
        },
        "change_failure_rate": cfr,
        "mttr": mttr,
    }

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print()
    print("=== DORA Metrics Summary ===")
    print(f"Lead time (avg):        {lead_time['avg_hours']}h  (p95: {lead_time['p95_hours']}h)")
    print(f"Deployment frequency:   {freq_per_week:.1f}/week")
    print(f"Change failure rate:    {cfr['rate_pct']}%")
    print(f"MTTR (median):          {mttr['median_minutes']} minutes")
    print()
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
