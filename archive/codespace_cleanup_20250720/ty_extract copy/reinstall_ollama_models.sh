#!/bin/bash
"""
Ollama Model Reinstallation Script
=================================

This script reinstalls all the Ollama models that were previously available.
"""

echo "🤖 OLLAMA MODEL REINSTALLATION"
echo "=============================="
echo "📋 Reinstalling all previously available models..."
echo ""

# List of models to reinstall
models=(
    "gemma3n:latest"
    "qwen2.5vl:latest"
    "phi3:latest"
    "dolphin3:8b"
    "codegemma:2b"
    "codegemma:latest"
    "olmo2:latest"
    "dolphin3:latest"
    "mistral:latest"
    "qwen3:4b"
    "qwen3:1.7b"
    "qwen3:0.6b"
    "gemma3:1b"
    "deepseek-r1:8b"
    "qwen3:latest"
    "phi4-mini-reasoning:latest"
    "phi3:3.8b"
    "gemma3:4b"
    "llama3.2:latest"
)

# Total models count
total_models=${#models[@]}
current_model=0

echo "📊 Total models to install: $total_models"
echo "💾 Estimated total download size: ~65 GB"
echo ""

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "🚨 Ollama is not running. Please start Ollama first:"
    echo "   sudo systemctl start ollama"
    echo "   or"
    echo "   ollama serve"
    echo ""
    exit 1
fi

echo "✅ Ollama is running"
echo ""

# Install each model
for model in "${models[@]}"; do
    current_model=$((current_model + 1))
    
    echo "🔄 Installing model $current_model/$total_models: $model"
    echo "   Progress: [$current_model/$total_models] $(( current_model * 100 / total_models ))%"
    
    # Pull the model
    if ollama pull "$model"; then
        echo "✅ Successfully installed: $model"
    else
        echo "❌ Failed to install: $model"
        echo "   You may need to install this manually later"
    fi
    
    echo ""
done

echo "🎉 MODEL INSTALLATION COMPLETE!"
echo "================================"
echo ""

# Verify installation
echo "🔍 Verifying installed models:"
ollama list

echo ""
echo "✅ All models have been processed!"
echo "📋 Check the list above to confirm successful installations"
echo ""
echo "🚀 You can now run your pipelines!"
