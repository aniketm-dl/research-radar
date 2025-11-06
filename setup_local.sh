#!/bin/bash

# Local setup script for Darpan Research Radar
# NOTE: You must set the environment variables separately for security

echo "========================================="
echo "Darpan Research Radar - Local Setup"
echo "========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo ""
    echo "Please create a .env file with the following content:"
    echo "----------------------------------------"
    cat > .env.template << 'EOF'
# Google Gemini Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# SMTP Configuration for Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=your-email@darpanlabs.ai
SMTP_PASSWORD=your-app-password-here
EOF
    cat .env.template
    echo "----------------------------------------"
    echo ""
    echo "Copy .env.template to .env and add your actual credentials:"
    echo "  cp .env.template .env"
    echo "  nano .env  # or use your favorite editor"
else
    echo "✅ Environment file found"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "To run the newsletter generator:"
echo "1. Ensure .env file has correct credentials"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run: python -m src.run"
echo ""
echo "Recipients configured in config.yaml:"
echo "- manav@darpanlabs.ai"
echo "- aniketg@darpanlabs.ai"
echo "- aniketm@darpanlabs.ai"
echo ""
echo "Email will be sent from: aniketm@darpanlabs.ai"
echo "Subject format: [Darpan Research Radar] - YYYY-MM-DD HH:MM UTC"