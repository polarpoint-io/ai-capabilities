#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Please run as a normal user (not root)."
  exit 1
fi

command_exists() { command -v "$1" >/dev/null 2>&1; }

echo "==> Checking Tailscale"
if ! command_exists tailscale; then
  echo "Tailscale not found. Installing..."
  curl -fsSL https://tailscale.com/install.sh | sh
fi

if ! command_exists tailscale; then
  echo "Tailscale install failed. Please install manually: https://tailscale.com/download"
  exit 1
fi

if ! tailscale status >/dev/null 2>&1; then
  if [[ -n "${TAILSCALE_AUTHKEY:-}" ]]; then
    sudo tailscale up --authkey "${TAILSCALE_AUTHKEY}"
  else
    echo "Launching interactive Tailscale login..."
    sudo tailscale up
  fi
fi

echo "==> Checking OpenClaw"
if ! command_exists openclaw; then
  echo "OpenClaw CLI not found. Install it first, then re-run this script:"
  echo "https://docs.openclaw.ai"
  exit 1
fi

openclaw gateway start
openclaw gateway status

echo "✅ Tailscale + OpenClaw should be running."
