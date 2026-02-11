#!/usr/bin/env bash
set -e

MODELS=(
  # General EN/DE, small–medium
  "llama3.1:8b"          # or whichever exact 8B tag you prefer
  "phi3.5:mini"          # example small model, adjust tag if needed

  # Multilingual EU focus
  "fl0id/teuken-7b-instruct-commercial-v0.4"

  # German-focused
  "jobautomation/OpenEuroLLM-German"
)

echo "🔁 Pulling Ollama models..."
for MODEL in "${MODELS[@]}"; do
  echo "➡️  Pulling: $MODEL"
  ollama pull "$MODEL"
  echo
done

echo "✅ Done. Installed models:"
ollama list
