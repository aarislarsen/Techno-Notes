#!/bin/bash
# Run script for Techno-Notes

cd "$(dirname "$0")"

echo "=== Starting Techno-Notes ==="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check Python dependencies
if ! python3 -c "import flask, PyPDF2, requests" 2>/dev/null; then
    echo "Error: Missing Python dependencies!"
    echo "Please run setup.sh again"
    exit 1
fi

# Show GPU/VRAM info and model recommendation
echo ""
echo "=== Hardware & Model Info ==="

CURRENT_MODEL=$(python3 -c "
import json, os
try:
    with open('llm_config.json') as f:
        print(json.load(f).get('model_name', 'qwen2.5:14b'))
except:
    print('qwen2.5:14b')
" 2>/dev/null)
echo "Current model: $CURRENT_MODEL"

# Recommended VRAM lookup (in GB)
case "$CURRENT_MODEL" in
    mistral-nemo*|mistral-nemo:12b) REC_VRAM=8 ;;
    qwen2.5:7b)                     REC_VRAM=5 ;;
    qwen2.5:14b)                    REC_VRAM=10 ;;
    command-r*|command-r:35b)       REC_VRAM=24 ;;
    *:13b|*:14b)                    REC_VRAM=10 ;;
    *:35b)                          REC_VRAM=24 ;;
    *:70b)                          REC_VRAM=40 ;;
    *)                              REC_VRAM=5 ;;
esac

if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null)
    if [ -n "$GPU_INFO" ]; then
        GPU_NAME=$(echo "$GPU_INFO" | cut -d',' -f1 | xargs)
        VRAM_TOTAL=$(echo "$GPU_INFO" | cut -d',' -f2 | xargs)
        VRAM_FREE=$(echo "$GPU_INFO" | cut -d',' -f3 | xargs)
        VRAM_FREE_MB=$(echo "$VRAM_FREE" | grep -o '[0-9]*')
        VRAM_FREE_GB=$((VRAM_FREE_MB / 1024))

        echo "GPU: $GPU_NAME"
        echo "VRAM: $VRAM_FREE / $VRAM_TOTAL free"
        echo "Recommended VRAM for $CURRENT_MODEL: ~${REC_VRAM} GB"

        if [ "$VRAM_FREE_GB" -lt "$REC_VRAM" ]; then
            echo ""
            echo "⚠️  Warning: Available VRAM (~${VRAM_FREE_GB} GB) is below recommended (~${REC_VRAM} GB)."
            echo "   Model will partially offload to CPU and run slower."
            echo "   Consider using a smaller model (e.g. qwen2.5:7b) for faster results."
        else
            echo "✅ Sufficient VRAM available"
        fi
    else
        echo "⚠️  nvidia-smi available but no GPU detected"
        echo "   Models will run on CPU (significantly slower)"
    fi
else
    echo "⚠️  No NVIDIA GPU detected — models will run on CPU (slower)"
    echo "   Recommended VRAM for $CURRENT_MODEL: ~${REC_VRAM} GB"
fi

echo ""
echo "================================"
echo ""

# Run the application
echo "Starting application..."
echo ""
python3 app.py
