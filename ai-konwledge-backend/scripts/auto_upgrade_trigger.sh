#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: ./scripts/auto_upgrade_trigger.sh <session_id> <message>"
  exit 1
fi

curl -s -X POST "http://127.0.0.1:8000/api/v1/query?auto_upgrade=true" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$1\",\"message\":\"$2\"}" | cat
