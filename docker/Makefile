# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

cache-clear:  ## Limpiar toda la caché de Redis
	docker compose exec redis redis-cli FLUSHDB
	@echo "✅ Caché limpiada"

cache-stats:  ## Ver estadísticas de caché
	docker compose exec redis redis-cli INFO stats | \
	grep -E "keyspace_hits|keyspace_misses"

cache-keys:  ## Listar todas las claves en caché
	docker compose exec redis redis-cli KEYS "*"

cache-monitor:  ## Monitorear caché en tiempo real
	docker compose exec redis redis-cli MONITOR
