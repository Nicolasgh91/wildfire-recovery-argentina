#!/usr/bin/env bash
# scripts/setup-vm-memory.sh
# Ejecutar una sola vez: ssh opc@vm 'bash -s' < scripts/setup-vm-memory.sh
set -euo pipefail

echo "=== Configurar swappiness ==="
# Reducir la agresividad de swap (default=60, queremos 10)
# Solo usar swap como último recurso, no proactivamente
sudo sysctl vm.swappiness=10
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.d/99-forestguard.conf

echo "=== Configurar OOM killer ==="
# Proteger sshd del OOM killer (para no perder acceso remoto)
SSHD_PID=$(pgrep -o sshd || true)
if [ -n "$SSHD_PID" ]; then
    echo -1000 | sudo tee /proc/$SSHD_PID/oom_score_adj
fi

# Configurar Docker para ser el primero en ser matado si hay OOM
DOCKERD_PID=$(pgrep -o dockerd || true)
if [ -n "$DOCKERD_PID" ]; then
    echo 100 | sudo tee /proc/$DOCKERD_PID/oom_score_adj
fi

echo "=== Estado actual de memoria ==="
free -h
swapon --show
cat /proc/sys/vm/swappiness

echo "=== Hecho ==="
