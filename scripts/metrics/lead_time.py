"""
Lead time for changes — time from first commit on a branch to production deployment.

Usage:
    GITHUB_TOKEN=<token> GITHUB_REPO=org/repo python lead_time.py

Returns a dict with avg_hours, p95_hours, and per-deployment raw data.
"""

import os
from datetime import datetime, timezone

from github import Github


def calculate_lead_time(repo_name: str, days_back: int = 30) -> dict:
    """Calculate lead time from first commit to production deployment.

    Walks recent production deployments, finds the PR associated with each
    deployment SHA, and measures the gap from the oldest commit on that PR
    to the deployment timestamp.
    """
    g = Github(os.environ["GITHUB_TOKEN"])
    repo = g.get_repo(repo_name)

    cutoff = datetime.now(timezone.utc).replace(
        day=max(1, datetime.now().day - days_back)
    )

    deployments = list(repo.get_deployments(environment="production"))

    lead_times = []
    for deployment in deployments[:50]:  # last 50 deployments
        if deployment.created_at < cutoff:
            break

        commit = repo.get_commit(deployment.sha)
        pulls = list(commit.get_pulls())
        if not pulls:
            continue

        pr = pulls[0]
        # Oldest commit on the PR branch = when work actually started
        first_commit_time = list(pr.get_commits())[-1].commit.author.date
        deploy_time = deployment.created_at

        lead_time_hours = (deploy_time - first_commit_time).total_seconds() / 3600
        lead_times.append(
            {
                "sha": deployment.sha[:7],
                "pr": pr.number,
                "lead_time_hours": round(lead_time_hours, 1),
                "first_commit": first_commit_time.isoformat(),
                "deployed_at": deploy_time.isoformat(),
            }
        )

    if lead_times:
        avg = sum(lt["lead_time_hours"] for lt in lead_times) / len(lead_times)
        p95 = sorted(lt["lead_time_hours"] for lt in lead_times)[
            int(len(lead_times) * 0.95)
        ]
    else:
        avg = p95 = 0.0

    return {
        "metric": "lead_time",
        "avg_hours": round(avg, 1),
        "p95_hours": round(p95, 1),
        "sample_count": len(lead_times),
        "raw": lead_times,
    }


if __name__ == "__main__":
    import json

    repo = os.environ["GITHUB_REPO"]
    result = calculate_lead_time(repo)
    print(json.dumps(result, indent=2))
