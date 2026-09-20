#!/usr/bin/env bash
# ============================================================
# CIAO Start Script
# Reads .env for LLM config, starts llama.cpp server, runs CIAO
# ============================================================

set -euo pipefail

# Load .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source env vars (simple key=value parser)
export $(grep -v '^#' .env | xargs)

# Resolve model path (expand ~)
LLM_MODEL="${LLM_MODEL/#\~/$HOME}"

# Default arg: point to a repo
REPO="${1:-}"

# Check repo arg
if [ -z "$REPO" ]; then
    echo "Usage: $0 <github-repo-url-or-local-path>"
    echo "  e.g. $0 https://github.com/example/project"
    echo "  e.g. $0 ../my-local-repo"
    exit 1
fi

# Check model exists
if [ ! -f "$LLM_MODEL" ]; then
    echo "❌ Model not found: $LLM_MODEL"
    exit 1
fi

# Extract host and port from LLM_BASE_URL
# e.g. http://localhost:8080/v1 -> localhost:8080
PING_URL="${LLM_BASE_URL%/v1}"

# --- Start llama.cpp server if not already running ---
if ! curl -s "$PING_URL/health" > /dev/null 2>&1; then
    echo "🚀 Starting llama.cpp server..."
    echo "   Model: $LLM_MODEL"
    echo "   URL:   $LLM_BASE_URL"
    echo ""

    uv run llama-server \
        -m "$LLM_MODEL" \
        --host 127.0.0.1 \
        --port 8080 \
        &
    SERVER_PID=$!
    echo $SERVER_PID > .server.pid

    # Wait for server to be ready
    echo "⏳ Waiting for server to come online..."
    for i in {1..30}; do
        if curl -s "$PING_URL/health" > /dev/null 2>&1; then
            echo "✅ Server ready."
            echo ""
            break
        fi
        sleep 1
    done
else
    echo "ℹ️  llama.cpp server already running"
    echo ""
fi

# --- Run CIAO ---
echo "🌀 Running CIAO on: $REPO"
echo "   LLM:    $LLM_MODEL"
echo "   API:    $LLM_BASE_URL"
echo ""

uv run main.py "$REPO"

echo ""
echo "✅ CIAO run complete."
echo "📄 Check arc42_documentation.txt for output."
