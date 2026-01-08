#!/usr/bin/env bash
set -euo pipefail

echo "Breaking: remove t_palm_springs from trending..."
curl -s -X POST "http://localhost:8002/admin/break/remove_from_trending?region=US&locale=en-US&title_id=t_palm_springs" | jq .

echo "Breaking: make artwork stale..."
curl -s -X POST "http://localhost:8001/admin/break/artwork_stale/t_palm_springs" | jq .

echo "Breaking: remove es-MX localization..."
curl -s -X POST "http://localhost:8001/admin/break/remove_localization/t_palm_springs/es-MX" | jq .

echo "Done. Now run checks:"
echo "  curl -s -X POST http://localhost:8003/run_all | jq ."
