#!/bin/bash
# Run script for PDF LLM Processor

cd "$(dirname "$0")"

echo "=== Starting PDF LLM Processor ==="
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

# Run the application
echo "Starting application..."
echo ""
python3 app.py
