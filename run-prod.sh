#!/bin/bash
clear
docker rm -f $(docker ps -aq) 2>/dev/null || true
clear
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up