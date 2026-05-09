#!/usr/bin/env python3
"""
gemma-edge-agent.py — Run agentic tasks locally using Gemma 4 via Ollama.

Runs completely offline — no external API calls.

Usage:
    # Document classification
    python scripts/edge/gemma-edge-agent.py \
        --model gemma4:4b-q4_K_M \
        --task classify-document \
        --input /path/to/document.txt

    # System monitor (logs resource stats every N seconds)
    python scripts/edge/gemma-edge-agent.py \
        --model gemma4:4b-q4_K_M \
        --task system-monitor \
        --interval 60

    # Benchmark latency on this hardware
    python scripts/edge/gemma-edge-agent.py \
        --task benchmark \
        --runs 20

Environment variables:
    GEMMA_ENDPOINT      Ollama server URL (default: http://localhost:11434)
    GEMMA_MODEL         Model tag (default: gemma4:4b-q4_K_M)
    AUDIT_LOG           Audit log path (default: /tmp/edge-agent.jsonl)

Requires:
    pip install requests
    ollama installed and running (https://ollama.ai)
"""

import os
import sys
import json
import time
import argparse
import platform
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------

DOCUMENT_CATEGORIES = ["PII", "FINANCIAL", "TECHNICAL", "PUBLIC", "INTERNAL"]


class OllamaClient:
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.endpoint}/api/health", timeout=5)
            return resp.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    def generate(self, prompt: str, system: str = "", temperature: float = 0.1) -> tuple[str, float]:
        """Returns (response_text, latency_seconds)."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 512,
            },
        }

        start = time.monotonic()
        resp = requests.post(f"{self.endpoint}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        latency = time.monotonic() - start

        data = resp.json()
        return data.get("response", ""), latency

    def chat(self, messages: list[dict], system: str = "", temperature: float = 0.1) -> tuple[str, float]:
        """Chat completion with message history."""
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages if system else messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        start = time.monotonic()
        resp = requests.post(f"{self.endpoint}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        latency = time.monotonic() - start

        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return content, latency

    def list_models(self) -> list[str]:
        resp = requests.get(f"{self.endpoint}/api/tags", timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

class AuditLogger:
    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, task: str, inputs: dict, output: str, latency_s: float, model: str):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "task": task,
            "inputs_summary": {k: str(v)[:100] for k, v in inputs.items()},
            "output_summary": output[:300],
            "latency_s": round(latency_s, 3),
            "hardware": platform.machine(),
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def task_classify_document(client: OllamaClient, logger: AuditLogger, input_path: str) -> dict:
    """Classify a document into a predefined category using structured output."""
    path = Path(input_path)
    if not path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    content = path.read_text(encoding="utf-8", errors="replace")
    # Truncate to avoid context overflow on small models
    if len(content) > 4000:
        content = content[:4000] + "\n[... truncated ...]"

    system = (
        "You are a document classifier. Classify documents accurately and concisely. "
        "Always respond with valid JSON only — no markdown, no explanation outside the JSON."
    )

    prompt = f"""Classify this document. Respond with JSON only:

{{
  "category": "<one of: {', '.join(DOCUMENT_CATEGORIES)}>",
  "confidence": <0.0 to 1.0>,
  "reason": "<one sentence explaining the classification>",
  "contains_pii": <true or false>,
  "sensitivity": "<low|medium|high>"
}}

Document:
{content}"""

    response, latency = client.generate(prompt, system=system)

    logger.log(
        task="classify-document",
        inputs={"file": str(path), "size_chars": len(content)},
        output=response,
        latency_s=latency,
        model=client.model,
    )

    # Parse JSON response
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        result = json.loads(text)
        print(f"\nDocument: {path.name}")
        print(f"Category: {result.get('category')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Contains PII: {result.get('contains_pii')}")
        print(f"Sensitivity: {result.get('sensitivity')}")
        print(f"Reason: {result.get('reason')}")
        print(f"Latency: {latency:.2f}s")
        return result
    except json.JSONDecodeError:
        print(f"Raw response: {response}")
        return {"error": "Could not parse JSON response", "raw": response}


def task_system_monitor(client: OllamaClient, logger: AuditLogger, interval: int):
    """Periodically summarise system state using the local model."""
    import subprocess

    system = (
        "You are a concise system status analyst. "
        "Given raw system metrics, produce a 2-3 sentence plain English summary. "
        "Flag anything that looks unusual. Be direct."
    )

    print(f"System monitor running every {interval}s. Ctrl+C to stop.\n")

    while True:
        try:
            # Collect basic system metrics
            metrics = {}

            # Memory
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith(("MemTotal", "MemFree", "MemAvailable")):
                            key, val = line.split(":")
                            metrics[key.strip()] = val.strip()
            except FileNotFoundError:
                metrics["memory"] = "unavailable on this platform"

            # Load average
            try:
                with open("/proc/loadavg") as f:
                    load = f.read().strip().split()
                    metrics["load_1m"] = load[0]
                    metrics["load_5m"] = load[1]
                    metrics["load_15m"] = load[2]
            except FileNotFoundError:
                metrics["load"] = "unavailable on this platform"

            # Disk
            try:
                result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    if len(lines) > 1:
                        metrics["disk_root"] = lines[-1]
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

            prompt = f"System metrics at {datetime.now().strftime('%H:%M:%S')}:\n{json.dumps(metrics, indent=2)}"
            response, latency = client.generate(prompt, system=system)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] {response.strip()}")
            print(f"  (latency: {latency:.2f}s)\n")

            logger.log(
                task="system-monitor",
                inputs=metrics,
                output=response,
                latency_s=latency,
                model=client.model,
            )

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break


def task_benchmark(client: OllamaClient, logger: AuditLogger, runs: int):
    """Benchmark inference latency for this model on this hardware."""
    prompts = [
        "What is 2 + 2? Answer with just the number.",
        "List 3 colours. One per line.",
        "Summarise: The cat sat on the mat. The mat was red.",
        "Is this a valid JSON object? {\"key\": \"value\"} Answer yes or no.",
        "What is the capital of France? One word only.",
    ]

    print(f"Benchmarking {client.model} — {runs} runs\n")
    latencies = []

    for i in range(runs):
        prompt = prompts[i % len(prompts)]
        _, latency = client.generate(prompt)
        latencies.append(latency)
        print(f"  Run {i+1:2d}: {latency:.3f}s")

    avg = sum(latencies) / len(latencies)
    min_l = min(latencies)
    max_l = max(latencies)
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]

    print(f"\nResults ({runs} runs):")
    print(f"  Model:   {client.model}")
    print(f"  Average: {avg:.3f}s")
    print(f"  Min:     {min_l:.3f}s")
    print(f"  Max:     {max_l:.3f}s")
    print(f"  P95:     {p95:.3f}s")
    print(f"  Hardware: {platform.machine()} / {platform.system()}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Gemma 4 edge agent — offline agentic tasks")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("GEMMA_ENDPOINT", "http://localhost:11434"),
        help="Ollama server endpoint",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMMA_MODEL", "gemma4:4b-q4_K_M"),
        help="Ollama model tag",
    )
    parser.add_argument(
        "--task",
        choices=["classify-document", "system-monitor", "benchmark"],
        required=True,
        help="Task to run",
    )
    parser.add_argument("--input", help="Input file path (for classify-document)")
    parser.add_argument("--interval", type=int, default=60, help="Monitor interval in seconds")
    parser.add_argument("--runs", type=int, default=10, help="Number of benchmark runs")
    parser.add_argument(
        "--audit-log",
        default=os.environ.get("AUDIT_LOG", "/tmp/edge-agent.jsonl"),
        help="Audit log path",
    )
    return parser.parse_args()


def main():
    if not HAS_REQUESTS:
        print("Error: 'requests' package required. pip install requests", file=sys.stderr)
        sys.exit(1)

    args = parse_args()

    client = OllamaClient(endpoint=args.endpoint, model=args.model)
    logger = AuditLogger(log_path=args.audit_log)

    # Check Ollama is running
    if not client.is_available():
        print(f"Error: Ollama server not responding at {args.endpoint}", file=sys.stderr)
        print("Start it with: ollama serve", file=sys.stderr)
        sys.exit(1)

    # Check model is available
    available_models = client.list_models()
    if args.model not in available_models and args.task != "benchmark":
        print(f"Warning: model '{args.model}' not found. Available: {available_models}", file=sys.stderr)
        print(f"Pull it with: ollama pull {args.model}", file=sys.stderr)

    # Dispatch task
    if args.task == "classify-document":
        if not args.input:
            print("Error: --input required for classify-document task", file=sys.stderr)
            sys.exit(1)
        task_classify_document(client, logger, args.input)

    elif args.task == "system-monitor":
        task_system_monitor(client, logger, args.interval)

    elif args.task == "benchmark":
        task_benchmark(client, logger, args.runs)

    print(f"\nAudit log: {logger.log_path}")


if __name__ == "__main__":
    main()
