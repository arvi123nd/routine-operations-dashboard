#!/bin/bash
# ================================================================
# Production Deployment Script
# ================================================================

set -e

echo "🚀 Starting deployment..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Load environment variables
source .env

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

# Check Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment checks passed${NC}"

# Pull latest images
echo -e "${YELLOW}📥 Pulling latest images...${NC}"
docker-compose pull

# Build application image
echo -e "${YELLOW}🔨 Building application...${NC}"
docker-compose build --no-cache

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Check health
echo -e "${YELLOW}🏥 Checking service health...${NC}"
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Application is healthy${NC}"
else
    echo -e "${RED}❌ Application health check failed${NC}"
    docker-compose logs app
    exit 1
fi

# Show running containers
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Running containers:"
docker-compose ps

echo ""
echo "📊 Access dashboard at: http://localhost:${APP_PORT:-5000}"
echo "🔍 View logs: docker-compose logs -f app"
echo "🛑 Stop services: docker-compose down"
