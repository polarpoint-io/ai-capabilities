# Example: Gemma 4 Edge Agent

**Goal:** Run a fully capable agentic AI workload locally on edge hardware — offline, with native function calling, near-zero latency, and no data leaving the device.

Related blog post: [Gemma 4 at the Edge: Agentic Skills in Production](/blog/2026/04/07/gemma-4-at-the-edge-agentic-skills-in-production/)

## Problem

Most AI agent architectures assume a cloud API endpoint. For sensitive data, air-gapped environments, latency-critical automation, or high-volume inference where API costs matter, that's the wrong assumption. Gemma 4's E2B and E4B models run full agentic workloads locally on edge hardware.

## Workflow

1. **Download**: pull a quantised Gemma 4 model (GGUF or ONNX format)
2. **Serve**: start a local inference server (Ollama or llama.cpp)
3. **Connect**: point the agent at the local endpoint instead of an external API
4. **Run**: the agent uses function calling, structured output, and tool use — fully offline

## Hardware requirements

| Model | Minimum hardware | Recommended |
|-------|-----------------|-------------|
| Gemma 4 E2B (quantised 4-bit) | Raspberry Pi 5, 8GB RAM | Jetson Orin Nano |
| Gemma 4 E4B (quantised 4-bit) | Jetson Orin Nano, 8GB | Jetson Orin NX |
| Gemma 4 26B MoE | Jetson AGX Orin | Workstation GPU |
| Gemma 4 31B Dense | GPU with 24GB+ VRAM | A100 / H100 |

## Quick start with Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Gemma 4 E4B (4-bit quantised — good balance of quality and size)
ollama pull gemma4:4b-q4_K_M

# Test inference
ollama run gemma4:4b-q4_K_M "List the running processes on this system"

# Start as a server (default: localhost:11434)
ollama serve
```

## Scripts

```bash
# Run the example edge agent (document classifier)
python scripts/edge/gemma-edge-agent.py \
  --model gemma4:4b-q4_K_M \
  --endpoint http://localhost:11434 \
  --task classify-document \
  --input /path/to/document.pdf

# Run the example edge agent (local system monitor)
python scripts/edge/gemma-edge-agent.py \
  --model gemma4:4b-q4_K_M \
  --endpoint http://localhost:11434 \
  --task system-monitor \
  --interval 60

# Benchmark latency on your hardware
python scripts/edge/benchmark-latency.py \
  --model gemma4:4b-q4_K_M \
  --endpoint http://localhost:11434 \
  --runs 20
```

## Environment variables required

```bash
GEMMA_ENDPOINT=http://localhost:11434    # Ollama local server
GEMMA_MODEL=gemma4:4b-q4_K_M            # model tag
AUDIT_LOG=/var/log/edge-agent.jsonl     # structured log output
# No ANTHROPIC_API_KEY needed — fully local
```

## Example tool definition (native function calling)

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "classify_document",
            "description": "Classify a document into one of the defined categories",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["PII", "FINANCIAL", "TECHNICAL", "PUBLIC", "INTERNAL"],
                        "description": "The document category"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score 0.0-1.0"
                    },
                    "reason": {
                        "type": "string",
                        "description": "One sentence explaining the classification"
                    }
                },
                "required": ["category", "confidence", "reason"]
            }
        }
    }
]
```

## Inputs

- Local model file (GGUF format via Ollama, or ONNX)
- Document, image, audio, or structured data to process
- Tool definitions (function calling schemas)

## Outputs

- Structured JSON responses (function call outputs)
- Audit log: every inference logged with inputs, outputs, latency, model version
- No data transmitted to external endpoints

## Production considerations

**Model updates**: use a pull script on a schedule to check for new quantised versions. Roll back by switching the `GEMMA_MODEL` env var and restarting the agent process.

**Logging**: the agent logs every inference to a JSONL file. Rotate daily. Ship to your central log aggregator if the edge device has network access to do so.

**Health check**: expose a simple HTTP health endpoint from the inference server — Ollama does this at `/api/health` by default. Wire it into your monitoring.

**Quantisation tradeoff**: 4-bit quantised models (q4_K_M) are the best starting point — minimal quality loss for most classification and summarisation tasks, 60-70% smaller than full precision. Test q8_0 if you see quality issues.
