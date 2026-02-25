#!/usr/bin/env bash
# scripts/setup-vm-memory.sh
# Ejecutar una sola vez: ssh opc@vm 'bash -s' < scripts/setup-vm-memory.sh
set -euo pipefail

SYSCTL_FILE="/etc/sysctl.d/99-forestguard.conf"

echo "=== Configurar swappiness ==="
# Reducir la agresividad de swap (default=60, queremos 10)
# Solo usar swap como ultimo recurso, no proactivamente.
sudo sysctl vm.swappiness=10 >/dev/null
printf '%s\n' "vm.swappiness=10" | sudo tee "$SYSCTL_FILE" >/dev/null

echo "=== Configurar OOM killer ==="
# Proteger sshd del OOM killer para no perder acceso remoto.
SSHD_PID="$(pgrep -o sshd || true)"
if [ -n "$SSHD_PID" ] && [ -w "/proc/$SSHD_PID/oom_score_adj" ]; then
    printf '%s\n' "-1000" | sudo tee "/proc/$SSHD_PID/oom_score_adj" >/dev/null
fi

# Hacer dockerd mas sacrificable bajo OOM.
DOCKERD_PID="$(pgrep -o dockerd || true)"
if [ -n "$DOCKERD_PID" ] && [ -w "/proc/$DOCKERD_PID/oom_score_adj" ]; then
    printf '%s\n' "100" | sudo tee "/proc/$DOCKERD_PID/oom_score_adj" >/dev/null
fi

echo "=== Estado actual de memoria ==="
free -h
swapon --show
cat /proc/sys/vm/swappiness

echo "=== Hecho ==="
