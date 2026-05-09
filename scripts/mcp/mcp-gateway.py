#!/usr/bin/env python3
"""
mcp-gateway.py — A lightweight HTTP gateway for MCP servers with authentication,
per-caller tool scoping, rate limiting, audit logging, and prompt injection detection.

Usage:
    python scripts/mcp/mcp-gateway.py --config scripts/mcp/gateway-config.yaml --port 8080

    # Test with curl
    curl -X POST http://localhost:8080/tool \
      -H "X-API-Key: <your-service-account-key>" \
      -H "Content-Type: application/json" \
      -d '{"tool": "kubectl_get", "inputs": {"resource": "pods", "namespace": "default"}}'

Environment variables:
    MCP_GATEWAY_SECRET      Secret for key derivation (required)
    MCP_AUDIT_LOG           Path for JSONL audit log (default: /tmp/mcp-audit.jsonl)
    MCP_RATE_LIMIT_RPS      Requests per second per caller (default: 10)
    MCP_RATE_LIMIT_BURST    Burst allowance (default: 20)

Requires:
    pip install pyyaml bcrypt
"""

import os
import sys
import json
import time
import re
import hashlib
import hmac
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "service_accounts": [],
    "rate_limit": {
        "rps": int(os.environ.get("MCP_RATE_LIMIT_RPS", "10")),
        "burst": int(os.environ.get("MCP_RATE_LIMIT_BURST", "20")),
    },
    "audit_log": os.environ.get("MCP_AUDIT_LOG", "/tmp/mcp-audit.jsonl"),
}

# Patterns that suggest prompt injection in tool responses
INJECTION_PATTERNS = [
    r"ignore (previous|all|above) instructions",
    r"you are now",
    r"new (system|persona|role)",
    r"disregard (your|the) (rules|guidelines|constraints)",
    r"(print|output|reveal) (your |the )?(system prompt|instructions)",
    r"act as (if|though)",
    r"pretend (you are|to be)",
    r"forget (all|everything|your) (previous|prior)",
]

COMPILED_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class ServiceAccount:
    def __init__(self, config: dict):
        self.name = config["name"]
        self.key_hash = config["key_hash"]
        self.allowed_tools = set(config.get("allowed_tools", []))
        self.denied_tools = set(config.get("denied_tools", []))
        self.require_confirmation = set(config.get("require_confirmation", []))

    def verify_key(self, api_key: str) -> bool:
        """Constant-time key comparison using HMAC."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return hmac.compare_digest(key_hash, self.key_hash)

    def can_call_tool(self, tool_name: str) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        if tool_name in self.denied_tools:
            return False, f"Tool '{tool_name}' is explicitly denied for this service account"

        if "*" in self.allowed_tools:
            return True, "wildcard"

        if tool_name in self.allowed_tools:
            return True, "permitted"

        return False, f"Tool '{tool_name}' is not in the allowed tools list for this service account"

    def needs_confirmation(self, tool_name: str) -> bool:
        return tool_name in self.require_confirmation


# ---------------------------------------------------------------------------
# Rate limiting (token bucket per caller)
# ---------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, rps: float, burst: int):
        self.rps = rps
        self.burst = burst
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": burst, "last_refill": time.monotonic()}
        )

    def check(self, caller: str) -> tuple[bool, float]:
        """Returns (allowed, retry_after_seconds)."""
        bucket = self._buckets[caller]
        now = time.monotonic()
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rps)
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, 0.0
        else:
            retry_after = (1 - bucket["tokens"]) / self.rps
            return False, retry_after


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

class AuditLogger:
    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        caller: str,
        tool: str,
        inputs: dict,
        output_summary: str,
        status: str,
        latency_ms: int,
        trace_id: Optional[str] = None,
        injection_detected: bool = False,
    ):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "caller": caller,
            "tool": tool,
            "inputs": inputs,
            "output_summary": output_summary[:500],  # truncate for log size
            "status": status,
            "latency_ms": latency_ms,
            "trace_id": trace_id,
        }
        if injection_detected:
            entry["injection_detected"] = True

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Prompt injection detection
# ---------------------------------------------------------------------------

def detect_injection(text: str) -> Optional[str]:
    """Return the matching pattern if injection is detected, else None."""
    for pattern in COMPILED_INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def summarise_output(output: any) -> str:
    """Produce a short summary of tool output for logging."""
    if isinstance(output, str):
        return output[:200] + ("..." if len(output) > 200 else "")
    elif isinstance(output, dict):
        keys = list(output.keys())[:5]
        return f"dict with keys: {keys}"
    elif isinstance(output, list):
        return f"list with {len(output)} items"
    return str(output)[:200]


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

class MCPGateway:
    def __init__(self, config: dict):
        self.accounts: dict[str, ServiceAccount] = {}
        for sa_config in config.get("service_accounts", []):
            sa = ServiceAccount(sa_config)
            self.accounts[sa.name] = sa

        rl_config = config.get("rate_limit", {})
        self.rate_limiter = RateLimiter(
            rps=rl_config.get("rps", 10),
            burst=rl_config.get("burst", 20),
        )

        self.audit_logger = AuditLogger(config.get("audit_log", "/tmp/mcp-audit.jsonl"))

        # In a real implementation, this would proxy to actual MCP servers
        # For the example, we simulate tool dispatch
        self.mcp_backends: dict[str, str] = config.get("backends", {})

    def authenticate(self, api_key: str) -> Optional[ServiceAccount]:
        """Find the service account matching this API key."""
        for sa in self.accounts.values():
            if sa.verify_key(api_key):
                return sa
        return None

    def handle_tool_call(
        self,
        api_key: str,
        tool_name: str,
        inputs: dict,
        trace_id: Optional[str] = None,
    ) -> dict:
        """
        Process a tool call through auth, rate limiting, injection detection, and dispatch.
        Returns a response dict with 'status', 'result' or 'error', and 'metadata'.
        """
        start = time.monotonic()

        # 1. Authenticate
        sa = self.authenticate(api_key)
        if not sa:
            self.audit_logger.log(
                caller="unknown",
                tool=tool_name,
                inputs=inputs,
                output_summary="Authentication failed",
                status="auth_failed",
                latency_ms=int((time.monotonic() - start) * 1000),
                trace_id=trace_id,
            )
            return {"status": 401, "error": "Invalid API key"}

        # 2. Rate limiting
        allowed, retry_after = self.rate_limiter.check(sa.name)
        if not allowed:
            return {
                "status": 429,
                "error": "Rate limit exceeded",
                "retry_after": retry_after,
            }

        # 3. Tool permission check
        can_call, reason = sa.can_call_tool(tool_name)
        if not can_call:
            self.audit_logger.log(
                caller=sa.name,
                tool=tool_name,
                inputs=inputs,
                output_summary=f"Permission denied: {reason}",
                status="permission_denied",
                latency_ms=int((time.monotonic() - start) * 1000),
                trace_id=trace_id,
            )
            return {"status": 403, "error": reason}

        # 4. Confirmation required check
        if sa.needs_confirmation(tool_name):
            # In a real implementation, this would pause and wait for approval
            # For the example, we surface it as a warning in the response
            logging.warning(f"Tool '{tool_name}' called by '{sa.name}' requires confirmation")

        # 5. Dispatch to MCP backend (simulated here — wire to real MCP server)
        try:
            result = self._dispatch_tool(tool_name, inputs)
        except Exception as e:
            self.audit_logger.log(
                caller=sa.name,
                tool=tool_name,
                inputs=inputs,
                output_summary=f"Tool error: {str(e)}",
                status="tool_error",
                latency_ms=int((time.monotonic() - start) * 1000),
                trace_id=trace_id,
            )
            return {"status": 500, "error": f"Tool execution failed: {str(e)}"}

        # 6. Prompt injection detection on output
        result_text = json.dumps(result) if not isinstance(result, str) else result
        injection_match = detect_injection(result_text)
        injection_detected = injection_match is not None

        if injection_detected:
            logging.warning(
                f"Potential prompt injection detected in '{tool_name}' response "
                f"for caller '{sa.name}': {injection_match!r}"
            )

        # 7. Audit log
        latency_ms = int((time.monotonic() - start) * 1000)
        self.audit_logger.log(
            caller=sa.name,
            tool=tool_name,
            inputs=inputs,
            output_summary=summarise_output(result),
            status="success",
            latency_ms=latency_ms,
            trace_id=trace_id,
            injection_detected=injection_detected,
        )

        response = {
            "status": 200,
            "result": result,
            "metadata": {
                "caller": sa.name,
                "tool": tool_name,
                "latency_ms": latency_ms,
            },
        }

        if injection_detected:
            response["warnings"] = ["potential_prompt_injection_in_response"]

        return response

    def _dispatch_tool(self, tool_name: str, inputs: dict) -> any:
        """
        Dispatch to the actual MCP server backend.

        In production, replace this with real MCP client calls:
            from mcp import ClientSession, StdioServerParameters
            # ... wire to your actual MCP server process or HTTP endpoint

        For the example, we return a simulated response.
        """
        return {
            "tool": tool_name,
            "inputs": inputs,
            "result": f"[Simulated response for {tool_name}]",
            "note": "Replace _dispatch_tool() with real MCP client calls",
        }


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def load_config(config_path: Optional[str]) -> dict:
    if not config_path:
        return DEFAULT_CONFIG

    if not HAS_YAML:
        print("Warning: pyyaml not installed, using default config. pip install pyyaml", file=sys.stderr)
        return DEFAULT_CONFIG

    with open(config_path) as f:
        loaded = yaml.safe_load(f)
    return {**DEFAULT_CONFIG, **loaded}


def parse_args():
    parser = argparse.ArgumentParser(description="MCP Gateway — auth, rate limiting, audit logging")
    parser.add_argument("--config", help="Path to gateway-config.yaml")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a demo tool call instead of starting the HTTP server",
    )
    return parser.parse_args()


def run_demo(gateway: MCPGateway):
    """Demonstrate a tool call through the gateway."""
    print("=== MCP Gateway Demo ===\n")

    # Simulate a service account key (in production, use bcrypt-hashed keys)
    demo_key = "demo-api-key-12345"

    # For demo purposes, add a test account directly
    gateway.accounts["demo-ci"] = ServiceAccount({
        "name": "demo-ci",
        "key_hash": hashlib.sha256(demo_key.encode()).hexdigest(),
        "allowed_tools": ["kubectl_get", "argocd_get_app"],
        "denied_tools": ["kubectl_delete"],
        "require_confirmation": [],
    })

    # Test 1: Authorised tool call
    print("Test 1: Authorised tool call (kubectl_get)")
    result = gateway.handle_tool_call(
        api_key=demo_key,
        tool_name="kubectl_get",
        inputs={"resource": "pods", "namespace": "default"},
        trace_id="demo-trace-001",
    )
    print(json.dumps(result, indent=2))

    # Test 2: Denied tool
    print("\nTest 2: Denied tool (kubectl_delete)")
    result = gateway.handle_tool_call(
        api_key=demo_key,
        tool_name="kubectl_delete",
        inputs={"resource": "pod", "name": "my-pod", "namespace": "default"},
        trace_id="demo-trace-002",
    )
    print(json.dumps(result, indent=2))

    # Test 3: Bad API key
    print("\nTest 3: Invalid API key")
    result = gateway.handle_tool_call(
        api_key="bad-key",
        tool_name="kubectl_get",
        inputs={"resource": "pods"},
        trace_id="demo-trace-003",
    )
    print(json.dumps(result, indent=2))

    print(f"\nAudit log written to: {gateway.audit_logger.log_path}")


def main():
    args = parse_args()
    config = load_config(args.config)
    gateway = MCPGateway(config)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.demo:
        run_demo(gateway)
        return

    # In production, wire this gateway into a real HTTP server
    # For example with FastAPI:
    #   from fastapi import FastAPI, Header, HTTPException
    #   app = FastAPI()
    #   @app.post("/tool")
    #   def call_tool(body: ToolCallRequest, x_api_key: str = Header(...)):
    #       return gateway.handle_tool_call(x_api_key, body.tool, body.inputs)
    #   uvicorn.run(app, host="0.0.0.0", port=args.port)

    print(f"MCP Gateway ready — run with --demo to test, or wire into your HTTP server")
    print(f"Loaded {len(gateway.accounts)} service accounts")
    print(f"Rate limit: {gateway.rate_limiter.rps} RPS, burst {gateway.rate_limiter.burst}")
    print(f"Audit log: {gateway.audit_logger.log_path}")


if __name__ == "__main__":
    main()
