#!/bin/bash
set -e

# Define la pantalla virtual y directorio runtime
export DISPLAY=:99
export XDG_RUNTIME_DIR=/tmp/runtime-root

# Crea el directorio runtime
mkdir -p /tmp/runtime-root
chmod 700 /tmp/runtime-root

# Elimina bloqueo previo de Xvfb
rm -f /tmp/.X99-lock

echo "Iniciando Xvfb..."
Xvfb :99 -screen 0 1366x768x24 &
sleep 2

echo "Iniciando fluxbox..."
fluxbox &

echo "Iniciando x11vnc..."
x11vnc -display :99 -forever -shared -nopw -listen 0.0.0.0 -rfbport 5900 &

echo "Iniciando noVNC..."
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &

echo "Iniciando Jupyter..."
exec start-notebook.sh --ip=0.0.0.0 --port=8888 --no-browser --allow-root