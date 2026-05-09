# Example: MCP in Production

**Goal:** Run MCP servers safely in shared team environments — with proper authentication, per-user tool scoping, rate limiting, audit logging, and prompt injection defences.

Related blog post: [MCP in the Real World: Security, Permissions, and Operations](/blog/2026/04/07/mcp-in-the-real-world-security-permissions-and-operations/)

## Problem

MCP is easy to demo on a laptop. Shared team infrastructure is different: five engineers with different access levels, production clusters, tool calls that retry on timeout, and GitHub issue bodies that contain text that looks like instructions. None of this is handled by default MCP transport. You have to build it.

## What this example covers

- API key authentication per service account
- Per-caller tool permission scoping (read-only vs read-write vs admin)
- Rate limiting per caller with exponential backoff guidance
- Structured audit logging (inputs, outputs, caller identity, latency)
- Prompt injection detection in tool responses

## Scripts

```bash
# Start the MCP gateway with auth and rate limiting
ANTHROPIC_API_KEY=<key> python scripts/mcp/mcp-gateway.py \
  --config scripts/mcp/gateway-config.yaml \
  --port 8080

# Test authentication with a sample tool call
python scripts/mcp/test-auth.py --server http://localhost:8080 \
  --api-key <service-account-key>

# Review the audit log
python scripts/mcp/read-audit-log.py --log /var/log/mcp-audit.jsonl \
  --since 1h --caller <service-account-name>
```

## Environment variables required

```bash
ANTHROPIC_API_KEY=<key>
MCP_GATEWAY_SECRET=<signing-secret-for-api-keys>
MCP_AUDIT_LOG=/var/log/mcp-audit.jsonl
MCP_RATE_LIMIT_RPS=10           # requests per second per caller
MCP_RATE_LIMIT_BURST=20         # burst allowance
```

## Tool permission model

```yaml
# gateway-config.yaml
service_accounts:
  - name: ci-pipeline
    key_hash: "<bcrypt-hash>"
    allowed_tools:
      - argocd_get_app
      - argocd_sync_app
      - kubectl_get
    denied_tools:
      - kubectl_delete
      - argocd_delete_app

  - name: on-call-engineer
    key_hash: "<bcrypt-hash>"
    allowed_tools: ["*"]           # all tools
    require_confirmation:
      - kubectl_delete
      - argocd_delete_app
      - kubectl_scale

  - name: readonly-dashboard
    key_hash: "<bcrypt-hash>"
    allowed_tools:
      - argocd_get_app
      - argocd_list_apps
      - kubectl_get
      - kubectl_describe
```

## Audit log format

Every tool call — inputs and outputs, not just the invocation — is logged:

```json
{
  "timestamp": "2026-05-04T14:32:01Z",
  "caller": "ci-pipeline",
  "tool": "argocd_sync_app",
  "inputs": {"app_name": "payments-api", "revision": "HEAD"},
  "output_summary": "Sync triggered: payments-api → HEAD (healthy after 23s)",
  "latency_ms": 2341,
  "status": "success",
  "trace_id": "tr_01HXYZ..."
}
```

## Prompt injection detection

Tool responses that contain instruction-like text are flagged before being returned to the model:

```python
# Patterns that trigger a warning log and response sanitisation
INJECTION_PATTERNS = [
    r"ignore (previous|all|above) instructions",
    r"you are now",
    r"new (system|persona|role)",
    r"disregard (your|the) (rules|guidelines|constraints)",
    r"(print|output|reveal) (your |the )?(system prompt|instructions)",
]
```

Flagged responses are still returned (blocking breaks agent workflows) but the injection attempt is logged with full context for review.

## Rate limiting behaviour

| Scenario | Gateway behaviour |
|----------|------------------|
| Under limit | Pass through immediately |
| Burst exceeded | 429 with `Retry-After` header |
| Timeout on upstream | Return error, do NOT auto-retry (caller decides) |
| Caller not found | 401 — log the attempt |

The gateway never retries upstream tool calls. Retry logic belongs in the caller, not the gateway, because the caller knows whether the operation is idempotent.

## Inputs

- MCP server (ArgoCD, kubectl, GitHub, or any MCP-compatible server)
- `gateway-config.yaml` — service accounts, tool permissions, rate limits
- Caller API key (per service account)

## Outputs

- Proxied tool responses with caller identity injected into metadata
- JSONL audit log (one line per tool call)
- Prometheus metrics: `mcp_tool_calls_total`, `mcp_tool_latency_seconds`, `mcp_injection_attempts_total`
