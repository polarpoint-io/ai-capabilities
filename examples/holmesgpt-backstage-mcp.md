# Example: HolmesGPT + Backstage MCP Integration

**Goal:** Wire HolmesGPT to Backstage's Catalog and Scaffolder via TeraSky's MCP backend plugins — giving Holmes service ownership context during investigations and the ability to trigger Scaffolder templates for time-bound access provisioning.

Related blog post: [From Alert to Root Cause: HolmesGPT in Production](https://www.polarpoint.io/blog/2026/04/07/holmesgpt-incident-triage/)

## Problem

HolmesGPT can investigate cluster state and cloud infrastructure, but without Backstage context it's missing half the picture: who owns this service, what SLO is attached, who's on-call, and what provisioning templates exist for access requests. And when an incident requires emergency access, that provisioning still goes through someone's ad-hoc `kubectl apply` instead of your platform's standard path.

## What this example covers

- Installing TeraSky's Catalog and Scaffolder MCP backend plugins into Backstage
- Connecting HolmesGPT to both via URL-based MCP config
- A Scaffolder template for time-bound namespace access with auto-revocation
- The Slack approval loop that gates Scaffolder template execution

## Prerequisites

- A running Backstage instance (v1.x)
- HolmesGPT deployed via Robusta Helm chart
- TeraSky plugin packages: `@terasky/backstage-plugin-catalog-mcp-backend` and `@terasky/plugin-scaffolder-mcp-backend`

## Install the TeraSky plugins into Backstage

```bash
# In your Backstage repo
yarn workspace backend add @terasky/backstage-plugin-catalog-mcp-backend
yarn workspace backend add @terasky/plugin-scaffolder-mcp-backend
```

Register both in `packages/backend/src/index.ts`:

```typescript
backend.add(import('@terasky/backstage-plugin-catalog-mcp-backend'));
backend.add(import('@terasky/plugin-scaffolder-mcp-backend'));
```

Once deployed, Backstage exposes HTTP MCP endpoints. Verify they're live:

```bash
curl -H "Authorization: Bearer $BACKSTAGE_TOKEN" \
  https://backstage.internal/api/catalog-mcp/health
```

## Holmes MCP configuration

```yaml
# holmes-config.yaml
mcpServers:
  - name: backstage-catalog
    url: https://backstage.internal/api/catalog-mcp/sse
    headers:
      Authorization: "Bearer ${BACKSTAGE_TOKEN}"

  - name: backstage-scaffolder
    url: https://backstage.internal/api/scaffolder-mcp/sse
    headers:
      Authorization: "Bearer ${BACKSTAGE_TOKEN}"
```

Note: these use `url` (HTTP SSE transport), not `command: uvx`. The MCP server runs inside Backstage — Holmes connects to it, not the other way around. Verify the exact endpoint paths from the [TeraSky plugin READMEs](https://github.com/terasky-oss/backstage-plugins).

## Environment variables required

```bash
BACKSTAGE_TOKEN=<service-account-token-with-catalog-read-and-scaffolder-execute>
BACKSTAGE_URL=https://backstage.internal
```

Create a dedicated Backstage service account for Holmes — don't reuse a personal token.

## What Catalog MCP gives Holmes

During any investigation, Holmes can call Catalog MCP to retrieve:

- Service owner (team + individual on-call)
- Dependencies and dependency owners
- SLO definition and current burn rate
- Deployed environment config

This happens automatically. If Holmes is investigating `payments-api`, it queries the Catalog for that component before forming a hypothesis — so the root cause summary includes ownership context without you prompting for it.

```bash
holmes ask "What's causing elevated error rates on payments-api?"
# Holmes automatically: queries k8s, Prometheus, AND Backstage catalog
# Output includes: "Owner: payments-team, on-call: @sarah, SLO: 99.9% (currently 99.2%)"
```

## What Scaffolder MCP gives Holmes

Holmes can trigger any Scaffolder template by name with structured inputs:

```bash
holmes ask "Grant @alice view access to prod-payments namespace for 4 hours"
```

Holmes calls the Scaffolder MCP with the `namespace-access-request` template:

```
Template: namespace-access-request (v1.2)
Inputs:
  user: alice@company.com
  namespace: prod-payments
  role: view
  duration: 4h

Actions taken:
  RoleBinding created: alice-prod-payments-view
  Auto-revocation job scheduled: 4h
  PR #847 opened (audit trail)
  Slack notification sent to #access-log
```

## Scaffolder template: time-bound namespace access

```yaml
# backstage/templates/namespace-access/template.yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: namespace-access-request
  title: Namespace Access Request
  description: Time-bound RoleBinding with auto-revocation
spec:
  owner: platform-team
  type: access

  parameters:
    - title: Access details
      required: [user, namespace, role, duration]
      properties:
        user:
          type: string
          description: User email address
        namespace:
          type: string
          description: Target namespace
        role:
          type: string
          enum: [view, edit]
          default: view
        duration:
          type: string
          enum: [1h, 4h, 8h, 24h]
          default: 4h

  steps:
    - id: create-rolebinding
      name: Create RoleBinding
      action: kubernetes:apply
      input:
        manifest:
          apiVersion: rbac.authorization.k8s.io/v1
          kind: RoleBinding
          metadata:
            name: "${{ parameters.user | replace('@', '-') | replace('.', '-') }}-${{ parameters.role }}"
            namespace: ${{ parameters.namespace }}
            annotations:
              expires-at: "${{ '' | now | date_modify(parameters.duration) | date('c') }}"
          subjects:
            - kind: User
              name: ${{ parameters.user }}
          roleRef:
            kind: ClusterRole
            name: ${{ parameters.role }}
            apiGroup: rbac.authorization.k8s.io

    - id: open-pr
      name: Open audit PR
      action: publish:github:pull-request
      input:
        title: "Access: ${{ parameters.user }} → ${{ parameters.namespace }} (${{ parameters.role }}, ${{ parameters.duration }})"
        branchName: "access/${{ parameters.namespace }}-${{ '' | now | date('Ymd-His') }}"
```

## Slack approval gate

Holmes won't trigger Scaffolder templates without an approval step. Configure in `holmes-config.yaml`:

```yaml
slackConfig:
  accessRequestChannel: "#access-requests"
  approvalTimeout: 30m
  requireApproverInChannel: true

approvalPolicies:
  - match:
      tool: backstage-scaffolder
      template: namespace-access-request
    require:
      - slack_approval
      - approver_is_owner_or_lead
```

## Inputs

- Backstage instance with TeraSky plugins installed
- `holmes-config.yaml` with `mcpServers` block for both catalog and scaffolder
- Scaffolder templates registered in Backstage catalog
- Slack bot token + access request channel

## Outputs

- Holmes investigations enriched with service ownership, SLOs, and on-call data
- Time-bound RoleBindings created through Backstage Scaffolder (not ad-hoc kubectl)
- GitHub PR audit trail for every provisioning action
- Auto-revocation job per access grant
