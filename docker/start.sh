#!/bin/bash
# Start Firecrawl
cd "$(dirname "$0")"
docker compose up -d
echo "Firecrawl is running at http://localhost:3002"
