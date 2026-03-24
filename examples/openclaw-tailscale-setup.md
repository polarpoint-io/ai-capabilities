# Example: OpenClaw + Tailscale Setup

**Goal:** Bring up OpenClaw and Tailscale consistently.

## Linux
```
./scripts/setup-linux.sh
```

## macOS
```
./scripts/setup-macos.sh
```

## Notes
- Set `TAILSCALE_AUTHKEY` for non‑interactive auth.
- `openclaw gateway status` confirms the daemon is running.
