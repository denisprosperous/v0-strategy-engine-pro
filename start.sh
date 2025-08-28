#!/bin/bash

# SmartTraderAI Startup Script

echo "🚀 Starting SmartTraderAI..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Test setup
echo "🧪 Running setup tests..."
python test_setup.py

# Start the application
echo "🎉 Starting SmartTraderAI..."
python main.py
