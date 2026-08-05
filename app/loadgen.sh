#!/bin/sh
# Continuously hits the sample app so there's always traffic for the SLI
# recording rules to compute against. Adjust REQUEST_INTERVAL to change rate.

APP_URL="${APP_URL:-http://app:5000/api}"
REQUEST_INTERVAL="${REQUEST_INTERVAL:-0.2}"

echo "Load generator started: hitting $APP_URL every ${REQUEST_INTERVAL}s"

while true; do
  curl -s -o /dev/null "$APP_URL" &
  sleep "$REQUEST_INTERVAL"
done
