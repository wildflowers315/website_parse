#!/bin/bash
# Setup script for Python environment using uv

echo "========================================"
echo "Setting up Python environment with uv"
echo "========================================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo ""
    echo "uv is not installed. Installing uv..."
    echo ""
    # Install uv using pip
    pip install uv
    if [ $? -ne 0 ]; then
        echo "Failed to install uv. Please install it manually:"
        echo "  pip install uv"
        echo "Or download from: https://github.com/astral-sh/uv"
        exit 1
    fi
fi

echo ""
echo "Creating virtual environment with uv..."
uv venv

echo ""
echo "Installing dependencies..."
uv pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the extraction script:"
echo "  python extract_content.py"
echo ""
