#!/bin/sh
set -e

cleanup() {
    echo "Shutting down byosh..."
    /usr/sbin/nginx -s quit 2>/dev/null || true
    kill -TERM "$dns_pid" 2>/dev/null || true
    wait "$dns_pid" 2>/dev/null || true
    echo "byosh stopped"
    exit 0
}
trap cleanup TERM INT

# Stop any existing nginx gracefully first, then force
if /usr/sbin/nginx -s quit 2>/dev/null; then
    sleep 1
fi
pkill -9 nginx 2>/dev/null || true

# Validate config before starting
if ! /usr/sbin/nginx -t 2>/dev/null; then
    echo "ERROR: nginx configuration test failed"
    exit 1
fi

# Start nginx in foreground (daemon off) and background it
/usr/sbin/nginx
sleep 1
if ! pgrep -x nginx >/dev/null 2>&1; then
    echo "ERROR: nginx failed to start"
    exit 1
fi
echo "nginx started successfully"

# Start DNS server and track PID for signal handling
/usr/bin/python3 /opt/dns.py --ip ENV --whitelist /opt/domains &
dns_pid=$!

wait "$dns_pid"
