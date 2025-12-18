#!/bin/bash
# ActorHub.ai - Local Development Setup Script
# Run this script to set up the development environment

set -e

echo "=========================================="
echo "  ActorHub.ai Local Development Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed.${NC}" >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e "${RED}Node.js is required but not installed.${NC}" >&2; exit 1; }
command -v python >/dev/null 2>&1 || { echo -e "${RED}Python is required but not installed.${NC}" >&2; exit 1; }

echo -e "${GREEN}All prerequisites satisfied!${NC}"

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check PostgreSQL
echo "Checking PostgreSQL..."
until docker exec actorhub-postgres pg_isready -U postgres >/dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}PostgreSQL is ready!${NC}"

# Check Redis
echo "Checking Redis..."
until docker exec actorhub-redis redis-cli ping >/dev/null 2>&1; do
    echo "Waiting for Redis..."
    sleep 2
done
echo -e "${GREEN}Redis is ready!${NC}"

# Setup Python backend
echo -e "\n${YELLOW}Setting up Python backend...${NC}"
cd apps/api

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate || source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
alembic upgrade head

cd ../..

# Setup Node.js frontend
echo -e "\n${YELLOW}Setting up Node.js frontend...${NC}"
cd apps/web
npm install || pnpm install
cd ../..

echo -e "\n${GREEN}=========================================="
echo "  Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "To start the development servers:"
echo ""
echo "  Backend API:"
echo "    cd apps/api && source venv/bin/activate"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Frontend:"
echo "    cd apps/web && npm run dev"
echo ""
echo "Access points:"
echo "  - Frontend: http://localhost:3000"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - MinIO Console: http://localhost:9001"
echo "  - Qdrant Dashboard: http://localhost:6333/dashboard"
echo ""
