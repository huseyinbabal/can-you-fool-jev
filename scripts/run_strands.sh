#!/usr/bin/env bash
# Serve Strands Decider 2B locally on the same /v1/systemone API, run all questions, stop the server.
#   python3 -m venv .venv-strands && .venv-strands/bin/pip install strands-decider
#   ./scripts/run_strands.sh            (Apple silicon: --device mps; use --device cuda or cpu elsewhere)
cd "$(dirname "$0")/.."
.venv-strands/bin/strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8765 --device ${DEVICE:-mps} > strands-serve.log 2>&1 & SRV=$!
for i in $(seq 1 600); do curl -s -o /dev/null -w '%{http_code}' localhost:8765/v1/systemone -X POST -H 'content-type: application/json' -d '{"state":"hi","questions":{"q":{"type":"noul","instructions":"Is this a greeting?"}}}' 2>/dev/null | grep -q 200 && break; sleep 2; done
SYSTEMONE_HOST=http://localhost:8765 python3 -u scripts/run_systemone.py strands
kill $SRV
