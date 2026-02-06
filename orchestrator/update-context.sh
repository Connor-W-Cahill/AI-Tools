#!/usr/bin/env bash
# Run this to update CONTEXT.md with latest shared context
AIO_DIR="${AIO_DIR:-$HOME/.ai-orchestrator}"
export PATH="$AIO_DIR/bin:$PATH"

aio-context export "$(pwd)" > "$(dirname "$0")/CONTEXT.md.new"
mv "$(dirname "$0")/CONTEXT.md.new" "$(dirname "$0")/CONTEXT.md"
echo "Context updated"
