#!/bin/bash

# LiveCheck Test Runner
# Runs all tests and reports results

set -e

echo "========================================"
echo "LiveCheck Test Suite"
echo "========================================"
echo ""

# Check if backend is running
echo "Checking if backend is running..."
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "Backend is running"
else
    echo "ERROR: Backend is not running"
    echo "Start backend with: cd infra && docker-compose up"
    exit 1
fi

echo ""
echo "========================================"
echo "Running Integration Tests"
echo "========================================"
echo ""

# Run integration tests
pytest tests/test_backend_integration.py -v

echo ""
echo "========================================"
echo "Running Backend Unit Tests"
echo "========================================"
echo ""

# Run backend unit tests
cd backend
pytest tests/test_api.py -v
cd ..

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo ""
echo "All tests completed successfully!"
echo ""
echo "To run individual test files:"
echo "  pytest tests/test_backend_integration.py -v"
echo "  pytest backend/tests/test_api.py -v"
echo ""
echo "To run specific test:"
echo "  pytest tests/test_backend_integration.py::TestHealthEndpoint::test_health_check -v"
echo ""
