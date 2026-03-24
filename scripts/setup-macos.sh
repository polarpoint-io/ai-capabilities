#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Please run as a normal user (not root)."
  exit 1
fi

command_exists() { command -v "$1" >/dev/null 2>&1; }

if ! command_exists brew; then
  echo "Homebrew not found. Install it first: https://brew.sh"
  exit 1
fi

echo "==> Checking Tailscale"
if ! command_exists tailscale; then
  brew install --cask tailscale
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

if [[ -n "${TAILSCALE_FUNNEL_PORT:-}" ]]; then
  echo "==> Enabling Tailscale Funnel on port ${TAILSCALE_FUNNEL_PORT}"
  sudo tailscale funnel "${TAILSCALE_FUNNEL_PORT}"
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
