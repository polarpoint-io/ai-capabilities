#!/usr/bin/env python3
"""
AGENTS.md drift detector

Checks every repo in a GitHub org (or a supplied list) for Zone 1 drift
against the platform-standards template.

Usage:
  python detect-drift.py \
    --org my-org \
    --token $GITHUB_TOKEN \
    --schema https://raw.githubusercontent.com/your-org/platform-standards/main/schema.json

  # Or against a specific repo list:
  python detect-drift.py \
    --repos repo-a,repo-b,repo-c \
    --org my-org \
    --token $GITHUB_TOKEN \
    --schema ./schema.json

  # Output JSON for piping into dashboards / Slack:
  python detect-drift.py ... --output json
"""

import argparse
import base64
import hashlib
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Zone parser ───────────────────────────────────────────────────────────────

ZONE_START = re.compile(r'<!--\s*zone:(\d+):start\s*-->')
ZONE_END   = re.compile(r'<!--\s*zone:(\d+):end\s*-->')


def parse_zones(content: str) -> dict[int, str]:
    zones: dict[int, list[str]] = {}
    current = None
    buffer: list[str] = []
    for line in content.splitlines():
        ms = ZONE_START.match(line.strip())
        me = ZONE_END.match(line.strip())
        if ms:
            current = int(ms.group(1))
            buffer = []
        elif me and current == int(me.group(1)):
            zones[current] = '\n'.join(buffer).strip()
            current = None
        elif current is not None:
            buffer.append(line)
    return {k: v for k, v in zones.items()}


def zone1_hash(zone_content: str) -> str:
    normalised = re.sub(r'\s+', ' ', zone_content).strip()
    return hashlib.sha256(normalised.encode()).hexdigest()[:16]


# ── GitHub API ────────────────────────────────────────────────────────────────

def gh_get(url: str, token: str) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def list_org_repos(org: str, token: str) -> list[str]:
    repos = []
    page = 1
    while True:
        url = f'https://api.github.com/orgs/{org}/repos?per_page=100&page={page}&type=all'
        data = gh_get(url, token)
        if not data:
            break
        repos.extend(r['name'] for r in data)
        if len(data) < 100:
            break
        page += 1
    return repos


def fetch_agents_md(org: str, repo: str, token: str) -> tuple[str | None, str | None]:
    """Returns (content, last_pushed_at) or (None, None) if not found."""
    # try AGENTS.md and .github/AGENTS.md
    for path in ['AGENTS.md', '.github/AGENTS.md']:
        url = f'https://api.github.com/repos/{org}/{repo}/contents/{path}'
        data = gh_get(url, token)
        if data and 'content' in data:
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            # also fetch last commit date for this file
            commits_url = f'https://api.github.com/repos/{org}/{repo}/commits?path={path}&per_page=1'
            commits = gh_get(commits_url, token)
            last_sync = None
            if commits:
                last_sync = commits[0]['commit']['committer']['date'][:10]
            return content, last_sync
    return None, None


def fetch_schema(schema_arg: str, token: str | None) -> dict | None:
    if schema_arg.startswith('http://') or schema_arg.startswith('https://'):
        req = urllib.request.Request(schema_arg)
        if token and 'raw.githubusercontent.com' in schema_arg:
            req.add_header('Authorization', f'Bearer {token}')
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except Exception as e:
            print(f'Warning: could not fetch schema: {e}', file=sys.stderr)
            return None
    try:
        with open(schema_arg) as f:
            return json.load(f)
    except Exception as e:
        print(f'Warning: could not read schema file: {e}', file=sys.stderr)
        return None


# ── Status determination ──────────────────────────────────────────────────────

def determine_status(content: str | None, template_hash: str | None) -> tuple[str, str, str | None]:
    """Returns (status, zone1_hash_or_dash, template_version)."""
    if content is None:
        return 'MISSING', '—', None

    zones = parse_zones(content)
    if 1 not in zones:
        return 'NO_ZONES', '—', None

    z1h = zone1_hash(zones[1])

    if template_hash is None:
        return 'UNKNOWN', z1h, None

    if z1h == template_hash:
        return 'IN_SYNC', z1h, None
    else:
        return 'DRIFTED', z1h, None


STATUS_COLOUR = {
    'IN_SYNC' : '\033[32m',   # green
    'DRIFTED' : '\033[33m',   # yellow
    'MISSING' : '\033[31m',   # red
    'NO_ZONES': '\033[31m',   # red
    'UNKNOWN' : '\033[90m',   # grey
}
RESET = '\033[0m'


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Detect AGENTS.md drift across repos')
    parser.add_argument('--org',    required=True,  help='GitHub organisation')
    parser.add_argument('--token',  required=True,  help='GitHub personal access token')
    parser.add_argument('--schema', default=None,   help='URL or path to schema.json')
    parser.add_argument('--repos',  default=None,   help='Comma-separated list of repo names (default: all org repos)')
    parser.add_argument('--output', default='table', choices=['table', 'json'], help='Output format')
    parser.add_argument('--fail-on-drift', action='store_true', help='Exit 1 if any repo is DRIFTED or MISSING')
    args = parser.parse_args()

    schema = fetch_schema(args.schema, args.token) if args.schema else None
    template_hash    = schema.get('zone1Hash')    if schema else None
    template_version = schema.get('templateVersion', 'unknown') if schema else 'unknown'

    if args.repos:
        repos = [r.strip() for r in args.repos.split(',')]
    else:
        print(f'Fetching repo list for {args.org}...', file=sys.stderr)
        repos = list_org_repos(args.org, args.token)

    results = []
    for repo in repos:
        content, last_sync = fetch_agents_md(args.org, repo, args.token)
        status, z1h, _ = determine_status(content, template_hash)
        results.append({
            'repo':             repo,
            'template_version': template_version,
            'last_sync':        last_sync or '—',
            'zone1_hash':       z1h,
            'status':           status,
        })

    if args.output == 'json':
        print(json.dumps(results, indent=2))
    else:
        # Table output
        col_repo = max(len(r['repo']) for r in results) + 2
        print(
            f"\n{'repo':<{col_repo}} {'template_version':<18} {'last_sync':<12} "
            f"{'zone1_hash':<18} status"
        )
        print('─' * (col_repo + 18 + 12 + 18 + 12))
        for r in results:
            colour = STATUS_COLOUR.get(r['status'], '')
            print(
                f"{r['repo']:<{col_repo}} {r['template_version']:<18} {r['last_sync']:<12} "
                f"{r['zone1_hash']:<18} {colour}{r['status']}{RESET}"
            )
        print()

        in_sync = sum(1 for r in results if r['status'] == 'IN_SYNC')
        drifted = sum(1 for r in results if r['status'] == 'DRIFTED')
        missing = sum(1 for r in results if r['status'] in ('MISSING', 'NO_ZONES'))
        print(f"  {in_sync} in sync  ·  {drifted} drifted  ·  {missing} missing\n")

    if args.fail_on_drift:
        if any(r['status'] in ('DRIFTED', 'MISSING', 'NO_ZONES') for r in results):
            sys.exit(1)


if __name__ == '__main__':
    main()
