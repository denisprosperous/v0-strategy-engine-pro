#!/bin/bash

# ============================================================
# Production Start Script for v0-strategy-engine-pro
# ============================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# ============================================================
# Pre-flight Checks
# ============================================================

log "🚀 Starting v0-strategy-engine-pro..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    error ".env file not found. Please create it from .env.example"
    error "Run: cp .env.example .env"
    exit 1
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    error "Python3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1,2)
log "✓ Python version: $PYTHON_VERSION"

# ============================================================
# Virtual Environment Setup
# ============================================================

if [ ! -d "venv" ]; then
    log "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        error "Failed to create virtual environment"
        exit 1
    fi
fi

log "🔧 Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    error "Failed to activate virtual environment"
    exit 1
fi

# ============================================================
# Dependencies Installation
# ============================================================

if [ -f "requirements.txt" ]; then
    log "📥 Installing/updating dependencies..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    
    if [ $? -ne 0 ]; then
        error "Failed to install dependencies"
        exit 1
    fi
    log "✓ Dependencies installed successfully"
else
    warn "requirements.txt not found, skipping dependency installation"
fi

# ============================================================
# Health Checks
# ============================================================

log "🏥 Running health checks..."

# Check if Redis is running (optional)
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        log "✓ Redis is running"
    else
        warn "Redis is not running (optional service)"
    fi
fi

# Check if PostgreSQL is running (optional)
if command -v psql &> /dev/null; then
    if pg_isready &> /dev/null 2>&1; then
        log "✓ PostgreSQL is running"
    else
        warn "PostgreSQL is not running (optional service)"
    fi
fi

# Validate critical environment variables
log "🔍 Validating environment variables..."
source .env

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    error "TELEGRAM_BOT_TOKEN is not set in .env"
    exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    error "TELEGRAM_CHAT_ID is not set in .env"
    exit 1
fi

log "✓ Critical environment variables validated"

# ============================================================
# Graceful Shutdown Handler
# ============================================================

cleanup() {
    log "\n⚠️  Received shutdown signal..."
    log "🛑 Stopping trading bot gracefully..."
    
    if [ ! -z "$BOT_PID" ]; then
        kill -TERM "$BOT_PID" 2>/dev/null || true
        wait "$BOT_PID" 2>/dev/null || true
    fi
    
    log "✓ Bot stopped successfully"
    exit 0
}

trap cleanup SIGTERM SIGINT

# ============================================================
# Start Application
# ============================================================

log "🎉 Starting trading bot..."
log "Environment: ${ENVIRONMENT:-development}"
log "Trading Mode: ${TRADING_MODE:-MANUAL}"
log "======================================"

# Run the bot
python3 main.py &
BOT_PID=$!

log "✓ Bot started with PID: $BOT_PID"
log "Press Ctrl+C to stop gracefully"

# Wait for the process
wait $BOT_PID
