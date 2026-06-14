@echo off
echo Building and starting production container...
docker compose build --pull
docker compose up -d
echo App should be available at http://localhost:5000