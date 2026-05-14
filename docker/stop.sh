#!/bin/bash
# Stop Firecrawl
cd "$(dirname "$0")"
docker compose down
echo "Firecrawl stopped"
