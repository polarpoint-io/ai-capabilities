"""
Collect all six platform scorecard metrics via Azure DevOps + PagerDuty.

Usage:
    ADO_PAT=<token> ADO_ORG_URL=https://dev.azure.com/your-org \
        ADO_PROJECT=YourProject ADO_PLATFORM_AREA=YourProject\\PlatformRequests \
        PAGERDUTY_TOKEN=<token> \
        python collect_scorecard_data_ado.py

Output written to /tmp/scorecard-data.json (override with SCORECARD_DATA env var).
The generate_scorecard.py step reads from this file — the output contract is
identical to collect_scorecard_data.py, so you can swap either collector into
the monthly-scorecard.yml workflow without changing downstream steps.

Required packages:
    pip install azure-devops msrest requests
"""

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from azure.devops.connection import Connection
from azure.devops.v7_1.build.build_client import BuildClient
from azure.devops.v7_1.work_item_tracking.work_item_tracking_client import (
    WorkItemTrackingClient,
)
from msrest.authentication import BasicAuthentication

# Re-use the same dataclass — output contract is identical to the GitHub variant
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_scorecard_data import ScorecardData

# MTTR is provider-agnostic — comes from PagerDuty regardless of Git provider
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "metrics"))
from mttr import calculate_mttr


def ado_client(client_class):
    """Return an authenticated ADO client for the given client class."""
    credentials = BasicAuthentication("", os.environ["ADO_PAT"])
    connection = Connection(
        base_url=os.environ["ADO_ORG_URL"],
        creds=credentials,
    )
    return connection.clients.get_client(client_class)


def collect_monthly_data_ado(months_back: int = 1) -> ScorecardData:
    """Collect all scorecard metrics from Azure DevOps + PagerDuty."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30 * months_back)
    project = os.environ["ADO_PROJECT"]

    build_client = ado_client(BuildClient)

    # Deployment frequency — successful pipeline runs in the window
    builds = build_client.get_builds(
        project=project,
        min_finish_time=start,
        max_finish_time=end,
        result="succeeded",
        reason="individualCI,batchedCI,pullRequest",
    )
    deployments = list(builds)
    deployment_frequency = round(len(deployments) / (30 * months_back / 7), 1)

    # Lead time P95 — queue time to finish across successful builds
    # Note: queue-to-finish is an approximation; true lead time (first commit to prod)
    # requires correlating with PR creation times via Repos API.
    durations = sorted([
        (b.finish_time - b.queue_time).total_seconds() / 3600
        for b in deployments
        if b.finish_time and b.queue_time
    ])
    p95_idx = min(int(len(durations) * 0.95), len(durations) - 1) if durations else 0
    lead_time_p95 = round(durations[p95_idx], 1) if durations else 0.0

    # Change failure rate — failed builds / total builds
    all_builds = list(build_client.get_builds(
        project=project,
        min_finish_time=start,
        max_finish_time=end,
    ))
    failed = sum(1 for b in all_builds if b.result == "failed")
    cfr = round((failed / len(all_builds) * 100), 1) if all_builds else 0.0

    # Platform request backlog — Azure Boards work items in designated area
    wit_client = ado_client(WorkItemTrackingClient)
    area_path = os.environ["ADO_PLATFORM_AREA"]
    wiql = {
        "query": f"""
            SELECT [System.Id] FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.AreaPath] UNDER '{area_path}'
            AND [System.State] NOT IN ('Closed', 'Resolved', 'Done')
        """
    }
    result = wit_client.query_by_wiql(wiql, project=project)
    backlog_count = len(result.work_items)

    # MTTR still comes from PagerDuty
    mttr = calculate_mttr(days_back=30 * months_back)

    return ScorecardData(
        period_start=start.strftime("%Y-%m-%d"),
        period_end=end.strftime("%Y-%m-%d"),
        deployment_frequency=deployment_frequency,
        lead_time_p95_hours=lead_time_p95,
        change_failure_rate_pct=cfr,
        mttr_median_minutes=mttr["median_minutes"],
        platform_backlog_count=backlog_count,
        open_p1_incidents=mttr["open_p1"],
        slo_attainment_pct=0.0,  # wire up from your observability stack
    )


if __name__ == "__main__":
    current = collect_monthly_data_ado(months_back=1)
    previous = collect_monthly_data_ado(months_back=2)

    output = {
        "current": asdict(current),
        "previous": asdict(previous),
    }

    output_path = os.environ.get("SCORECARD_DATA", "/tmp/scorecard-data.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Scorecard data written to {output_path}")
    print(json.dumps(asdict(current), indent=2))
