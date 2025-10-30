#!/bin/bash
# Test runner script for logstash-parser

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Logstash Parser Test Suite ===${NC}\n"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

# Parse command line arguments
COVERAGE=true
VERBOSE=false
MARKERS=""
PARALLEL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cov)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -n|--parallel)
            PARALLEL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-cov          Disable coverage reporting"
            echo "  -v, --verbose     Verbose output"
            echo "  -m, --markers     Run tests with specific markers (e.g., 'unit', 'integration')"
            echo "  -n, --parallel    Run tests in parallel"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests with coverage"
            echo "  $0 --no-cov          # Run tests without coverage"
            echo "  $0 -v                # Run with verbose output"
            echo "  $0 -m unit           # Run only unit tests"
            echo "  $0 -n                # Run tests in parallel"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Sync dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
uv sync --group test

# Build pytest command
PYTEST_CMD="uv run pytest tests/"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov --cov-report=term-missing --cov-report=html"
fi

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $MARKERS"
fi

if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Run tests
echo -e "\n${YELLOW}Running tests...${NC}"
echo "Command: $PYTEST_CMD"
echo ""

if eval $PYTEST_CMD; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"

    if [ "$COVERAGE" = true ]; then
        echo -e "\n${YELLOW}Coverage report generated in htmlcov/index.html${NC}"
    fi

    exit 0
else
    echo -e "\n${RED}✗ Tests failed!${NC}"
    exit 1
fi
