#!/bin/bash
# Quick performance test script
# Usage: ./performance/quick_test.sh

set -e

# Colors
GREEN='\033[0.32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== eSalão Performance Quick Test ===${NC}"
echo ""

# Check if API is running
echo -n "Checking API health... "
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "API is not running. Start with:"
    echo "  docker-compose up -d"
    echo "  OR uvicorn backend.app.main:app --reload"
    exit 1
fi

# Create results directory
mkdir -p performance/results

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="performance/results/report_${TIMESTAMP}.html"

echo ""
echo -e "${YELLOW}Running load test...${NC}"
echo "  Users: 50"
echo "  Spawn rate: 10/s"
echo "  Duration: 2min"
echo "  Report: $REPORT_FILE"
echo ""

# Run locust headless
locust -f performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 10 \
  --run-time 2m \
  --headless \
  --html "$REPORT_FILE" \
  --csv "performance/results/stats_${TIMESTAMP}"

echo ""
echo -e "${GREEN}=== Test Complete ===${NC}"
echo ""
echo "Results:"
echo "  HTML Report: $REPORT_FILE"
echo "  CSV Stats: performance/results/stats_${TIMESTAMP}_stats.csv"
echo ""
echo "Open report with:"
echo "  xdg-open $REPORT_FILE  # Linux"
echo "  open $REPORT_FILE      # macOS"
echo ""
