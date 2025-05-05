#!/bin/sh
echo "worker starting; will push a timestamp to Redis every 5s"
while true; do
  redis-cli -h "$REDIS_HOST" LPUSH jobs "$(date)" >/dev/null 2>&1
  sleep 5
done