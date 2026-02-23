"""
Healthcheck contract tests for docker-compose.yml

Tests validate that healthcheck configurations follow the correct patterns:
- celery-beat uses process-level checks (not celery inspect ping)
- flower uses Python stdlib (not curl)
- nginx uses wget (not curl) 
- All workers use process-level checks (not celery inspect ping)
- All critical services define healthcheck
"""

import pytest
import yaml
from pathlib import Path


def load_compose_file():
    """Load and parse docker-compose.yml"""
    compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"
    with open(compose_path, 'r') as f:
        return yaml.safe_load(f)


def get_service_healthcheck(service_config):
    """Extract healthcheck configuration from service"""
    if 'healthcheck' not in service_config:
        return None
    
    healthcheck = service_config['healthcheck']
    if 'test' not in healthcheck:
        return None
    
    test_config = healthcheck['test']
    if isinstance(test_config, list):
        if len(test_config) == 1:
            return test_config[0]
        elif len(test_config) > 1:
            # For CMD format, join all parts after the first
            if test_config[0] == "CMD":
                return " ".join(test_config[1:])
            # For CMD-SHELL format, return the command part
            elif test_config[0] == "CMD-SHELL":
                return test_config[1]
    return test_config


class TestHealthcheckContracts:
    """Test healthcheck configurations follow contracts"""
    
    @pytest.fixture
    def compose(self):
        """Load docker-compose.yml for testing"""
        return load_compose_file()
    
    def test_celery_beat_uses_process_check(self, compose):
        """celery-beat should use pgrep to check process, not celery inspect ping"""
        service = compose['services']['celery-beat']
        healthcheck = get_service_healthcheck(service)
        
        assert healthcheck is not None, "celery-beat must have healthcheck"
        assert "celery inspect ping" not in healthcheck, "celery-beat should not use celery inspect ping"
        assert "pgrep -f 'celery.*beat'" in healthcheck, "celery-beat should use process-level check"
    
    def test_flower_uses_python_not_curl(self, compose):
        """flower should use Python stdlib, not curl"""
        service = compose['services']['flower']
        healthcheck = get_service_healthcheck(service)
        
        assert healthcheck is not None, "flower must have healthcheck"
        assert "curl" not in healthcheck, "flower should not use curl"
        assert "urllib.request" in healthcheck, "flower should use Python urllib"
    
    def test_nginx_uses_wget_not_curl(self, compose):
        """nginx should use wget, not curl"""
        service = compose['services']['nginx']
        healthcheck = get_service_healthcheck(service)
        
        assert healthcheck is not None, "nginx must have healthcheck"
        assert "curl" not in healthcheck, "nginx should not use curl"
        assert "wget" in healthcheck, "nginx should use wget"
    
    @pytest.mark.parametrize("worker_name", [
        "worker-ingestion",
        "worker-clustering", 
        "worker-analysis",
        "worker-reports"
    ])
    def test_workers_use_process_checks(self, compose, worker_name):
        """All workers should use process-level checks, not celery inspect ping"""
        service = compose['services'][worker_name]
        healthcheck = get_service_healthcheck(service)
        
        assert healthcheck is not None, f"{worker_name} must have healthcheck"
        assert "celery inspect ping" not in healthcheck, f"{worker_name} should not use celery inspect ping"
        assert "pgrep -f 'celery.*worker'" in healthcheck, f"{worker_name} should use process-level check"
    
    def test_critical_services_have_healthcheck(self, compose):
        """All critical services should define healthcheck"""
        critical_services = [
            'redis', 'api', 'worker-ingestion', 'worker-clustering',
            'worker-analysis', 'worker-reports', 'celery-beat', 'flower', 'nginx'
        ]
        
        for service_name in critical_services:
            service = compose['services'][service_name]
            healthcheck = get_service_healthcheck(service)
            assert healthcheck is not None, f"{service_name} must have healthcheck defined"
    
    def test_api_healthcheck_uses_curl(self, compose):
        """API service should continue using curl (available in API image)"""
        service = compose['services']['api']
        healthcheck = get_service_healthcheck(service)
        
        assert healthcheck is not None, "api must have healthcheck"
        assert "curl" in healthcheck, "api should use curl (available in API image)"
    
    def test_redis_healthcheck_uses_redis_cli(self, compose):
        """Redis should use redis-cli ping"""
        service = compose['services']['redis']
        healthcheck = get_service_healthcheck(service)
        
        assert healthcheck is not None, "redis must have healthcheck"
        assert "redis-cli ping" in healthcheck, "redis should use redis-cli ping"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
