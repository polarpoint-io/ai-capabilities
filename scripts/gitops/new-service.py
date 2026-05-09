#!/usr/bin/env python3
"""
new-service.py — Generate a self-service GitOps service definition YAML interactively.

Scaffolds a valid service definition file for the ArgoCD ApplicationSet
matrix generator pattern. Prompts for required fields with sensible defaults,
then writes the YAML to the target output directory.

Usage:
    python scripts/gitops/new-service.py \
        --team payments \
        --type api-service \
        --output teams/payments/services/

    # Non-interactive: provide all values as flags
    python scripts/gitops/new-service.py \
        --team payments \
        --name payments-api \
        --type api-service \
        --tier gold \
        --owner payments-team@example.com \
        --output teams/payments/services/ \
        --no-interactive

Exit codes:
    0 — file written successfully
    1 — validation error or write failure

Requires:
    pip install pyyaml
"""

import sys
import os
import argparse
import textwrap
from pathlib import Path
from datetime import date

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# Resource presets by tier
# ---------------------------------------------------------------------------

TIER_PRESETS = {
    "bronze": {
        "dev":        {"replicaCount": 1, "cpu_req": "50m",  "mem_req": "64Mi",  "cpu_lim": "200m",  "mem_lim": "256Mi"},
        "staging":    {"replicaCount": 1, "cpu_req": "100m", "mem_req": "128Mi", "cpu_lim": "500m",  "mem_lim": "512Mi"},
        "production": {"replicaCount": 2, "cpu_req": "100m", "mem_req": "128Mi", "cpu_lim": "500m",  "mem_lim": "512Mi"},
    },
    "silver": {
        "dev":        {"replicaCount": 1, "cpu_req": "100m", "mem_req": "128Mi", "cpu_lim": "500m",  "mem_lim": "512Mi"},
        "staging":    {"replicaCount": 2, "cpu_req": "200m", "mem_req": "256Mi", "cpu_lim": "1000m", "mem_lim": "1Gi"},
        "production": {"replicaCount": 3, "cpu_req": "200m", "mem_req": "256Mi", "cpu_lim": "1000m", "mem_lim": "1Gi"},
    },
    "gold": {
        "dev":        {"replicaCount": 1, "cpu_req": "200m", "mem_req": "256Mi", "cpu_lim": "1000m", "mem_lim": "1Gi"},
        "staging":    {"replicaCount": 2, "cpu_req": "500m", "mem_req": "512Mi", "cpu_lim": "2000m", "mem_lim": "2Gi"},
        "production": {"replicaCount": 5, "cpu_req": "500m", "mem_req": "512Mi", "cpu_lim": "2000m", "mem_lim": "2Gi"},
    },
}

VALID_TIERS  = list(TIER_PRESETS.keys())
VALID_TYPES  = ["api-service", "worker", "cron-job", "web-app", "library"]


# ---------------------------------------------------------------------------
# Template builder
# ---------------------------------------------------------------------------

def build_service_definition(
    name: str,
    team: str,
    svc_type: str,
    tier: str,
    owner: str,
    port: int,
    image_repo: str,
    include_production: bool,
) -> dict:
    presets = TIER_PRESETS[tier]

    def env_block(env: str) -> dict:
        p = presets[env]
        block = {
            "replicaCount": p["replicaCount"],
            "resources": {
                "requests": {"cpu": p["cpu_req"], "memory": p["mem_req"]},
                "limits":   {"cpu": p["cpu_lim"], "memory": p["mem_lim"]},
            },
        }
        # Add HPA for production silver/gold
        if env == "production" and tier in ("silver", "gold"):
            block["hpa"] = {
                "enabled": True,
                "minReplicas": p["replicaCount"],
                "maxReplicas": p["replicaCount"] * 3,
                "targetCPUUtilizationPercentage": 70,
            }
        return block

    environments = {
        "dev":     env_block("dev"),
        "staging": env_block("staging"),
    }
    if include_production:
        environments["production"] = env_block("production")

    doc: dict = {
        "name":  name,
        "team":  team,
        "type":  svc_type,
        "tier":  tier,
        "owner": owner,
    }

    if port and svc_type not in ("worker", "cron-job", "library"):
        doc["port"] = port

    if image_repo:
        doc["image"] = {"repository": image_repo, "tag": "latest"}

    doc["environments"] = environments

    # Add alerts stub for gold tier
    if tier == "gold":
        doc["alerts"] = {
            "errorRateThreshold": "1%",
            "latencyP99Ms": 500,
            "oncall": f"team-{team}",
        }

    return doc


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def prompt(msg: str, default: str = "", choices: list = None) -> str:
    """Prompt for input with an optional default and constrained choices."""
    choices_str = f" [{'/'.join(choices)}]" if choices else ""
    default_str = f" (default: {default})" if default else ""
    while True:
        raw = input(f"  {msg}{choices_str}{default_str}: ").strip()
        value = raw if raw else default
        if choices and value not in choices:
            print(f"    Please choose one of: {', '.join(choices)}")
            continue
        return value


def prompt_bool(msg: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    raw = input(f"  {msg} [{d}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "1", "true")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Generate a GitOps self-service service definition YAML")
    parser.add_argument("--team",           required=True, help="Team name (e.g. payments)")
    parser.add_argument("--name",           help="Service name (default: interactive prompt)")
    parser.add_argument("--type",           choices=VALID_TYPES, help="Service type")
    parser.add_argument("--tier",           choices=VALID_TIERS, help="Service tier (bronze/silver/gold)")
    parser.add_argument("--owner",          help="Owner email or Slack handle")
    parser.add_argument("--port",           type=int, default=8080, help="Container port (default: 8080)")
    parser.add_argument("--image-repo",     help="Container image repository (e.g. registry.example.com/payments/payments-api)")
    parser.add_argument("--output",         required=True, help="Output directory for the generated YAML")
    parser.add_argument("--no-interactive", action="store_true", help="Non-interactive mode — fail if required fields are missing")
    return parser.parse_args()


def main():
    if not HAS_YAML:
        print("Error: 'pyyaml' package required. pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    args = parse_args()
    interactive = not args.no_interactive

    print(f"\n{'─' * 60}")
    print(f"  GitOps Service Definition Generator")
    print(f"  Team: {args.team}")
    print(f"{'─' * 60}\n")

    # Collect values — prompt if not provided and interactive
    name = args.name
    if not name:
        if not interactive:
            print("Error: --name is required in non-interactive mode", file=sys.stderr)
            sys.exit(1)
        name = prompt("Service name (alphanumeric + hyphens)", default=f"{args.team}-api")

    svc_type = args.type
    if not svc_type:
        if not interactive:
            print("Error: --type is required in non-interactive mode", file=sys.stderr)
            sys.exit(1)
        svc_type = prompt("Service type", default="api-service", choices=VALID_TYPES)

    tier = args.tier
    if not tier:
        if not interactive:
            print("Error: --tier is required in non-interactive mode", file=sys.stderr)
            sys.exit(1)
        tier = prompt("Tier", default="silver", choices=VALID_TIERS)

    owner = args.owner
    if not owner:
        if not interactive:
            owner = f"{args.team}@example.com"
        else:
            owner = prompt("Owner (email or Slack handle)", default=f"{args.team}@example.com")

    port = args.port
    if interactive and svc_type not in ("worker", "cron-job", "library"):
        port_str = prompt("Container port", default=str(args.port))
        try:
            port = int(port_str)
        except ValueError:
            port = args.port

    image_repo = args.image_repo
    if not image_repo and interactive:
        image_repo = prompt(
            "Image repository",
            default=f"registry.example.com/{args.team}/{name}",
        )

    include_production = True
    if interactive:
        include_production = prompt_bool("Include production environment?", default=True)

    # Build the definition
    definition = build_service_definition(
        name=name,
        team=args.team,
        svc_type=svc_type,
        tier=tier,
        owner=owner,
        port=port,
        image_repo=image_repo or "",
        include_production=include_production,
    )

    # Write the output file
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{name}.yaml"

    header = textwrap.dedent(f"""\
        # Service definition for {name}
        # Generated by scripts/gitops/new-service.py on {date.today().isoformat()}
        # Team: {args.team} | Tier: {tier} | Type: {svc_type}
        #
        # Commit this file and open a PR. The ApplicationSet matrix generator
        # will create ArgoCD Applications for each environment automatically.
        #
        # Validate before committing:
        #   python scripts/gitops/validate-service.py --file {output_file}
        #
    """)

    yaml_content = yaml.dump(definition, default_flow_style=False, sort_keys=False, allow_unicode=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(yaml_content)

    print(f"\n  ✓ Written: {output_file}")
    print(f"\n  Summary:")
    print(f"    Service:  {name}")
    print(f"    Team:     {args.team}")
    print(f"    Type:     {svc_type}")
    print(f"    Tier:     {tier}")
    print(f"    Owner:    {owner}")
    envs = list(definition["environments"].keys())
    print(f"    Envs:     {', '.join(envs)}")
    print(f"\n  Next steps:")
    print(f"    1. Review {output_file}")
    print(f"    2. python scripts/gitops/validate-service.py --file {output_file}")
    print(f"    3. git add {output_file} && git commit -m 'feat: add {name} service definition'")
    print(f"    4. Open a PR — ApplicationSets will deploy automatically on merge")


if __name__ == "__main__":
    main()
