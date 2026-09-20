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
shift || true

# Parse optional flags
MAX_PARALLEL=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --max-parallel) MAX_PARALLEL="--max-parallel=$2"; shift 2 ;;
        --max-parallel=*) MAX_PARALLEL="$1"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Check repo arg
if [ -z "$REPO" ]; then
    echo "Usage: $0 <github-repo-url-or-local-path> [--max-parallel N]"
    echo "  e.g. $0 https://github.com/example/project"
    echo "  e.g. $0 ../my-local-repo --max-parallel 1"
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

# --- Run CIAO with live output ---
echo "🌀 Running CIAO on: $REPO"
echo "   LLM:    $LLM_MODEL"
echo "   API:    $LLM_BASE_URL"
if [ -n "$MAX_PARALLEL" ]; then
    echo "   Mode:   serial ($MAX_PARALLEL)"
fi
echo ""

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="ciao_${TIMESTAMP}.log"

echo "📝 Logging to: $LOG_FILE"
echo "   (tail -f $LOG_FILE in another terminal to watch progress)"
echo ""

# Force unbuffered Python output so tee captures everything immediately
PYTHONUNBUFFERED=1 uv run main.py ${MAX_PARALLEL:-} "$REPO" 2>&1 | tee "$LOG_FILE"

# Check if output was created
if [ -f "arc42_documentation.txt" ]; then
    SIZE=$(wc -c < "arc42_documentation.txt" | tr -d ' ')
    echo ""
    echo "✅ CIAO run complete."
    echo "📄 Output: arc42_documentation.txt (${SIZE} bytes)"
    echo "📋 Log:    $LOG_FILE"
else
    echo ""
    echo "⚠️  CIAO finished but arc42_documentation.txt was not created."
    echo "📋 Log:    $LOG_FILE"
fi
