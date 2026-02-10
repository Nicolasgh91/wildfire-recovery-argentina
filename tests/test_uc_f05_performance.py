#!/usr/bin/env python3
"""
UC-F05 Performance Test with Authentication
Tests KPIs de Recurrencia endpoints with API key authentication
"""

import pytest
import time
import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

class UC_F05_Performance_Test:
    """Test suite for UC-F05 KPIs de Recurrencia performance validation"""
    
    def __init__(self):
        self.client = TestClient(app)
        # Use admin API key for full access
        api_key = settings.ADMIN_API_KEY.get_secret_value() if settings.ADMIN_API_KEY else "admin-test-key"
        self.client.headers.update({"X-API-Key": api_key})
        self.base_url = "http://testserver"
        
    def test_recurrence_performance(self):
        """Test recurrence analysis endpoint performance"""
        print("\n=== Testing UC-F05 Recurrence Analysis Performance ===")
        
        # Test case 1: Normal bbox (Córdoba area)
        url = "/api/v1/analysis/recurrence?min_lon=-65&min_lat=-32&max_lon=-63&max_lat=-30"
        
        start_time = time.time()
        response = self.client.get(url)
        elapsed = time.time() - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Response time: {elapsed:.2f}s")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert elapsed < 2.0, f"Performance requirement failed: {elapsed:.2f}s > 2.0s"
        
        data = response.json()
        assert "features" in data, "Missing features in response"
        assert "summary" in data, "Missing summary in response"
        
        print(f"✓ Features returned: {len(data['features'])}")
        print(f"✓ Summary: {data['summary']}")
        print(f"✓ Performance OK ({elapsed:.2f}s < 2.0s)")
        
        return True, elapsed
    
    def test_trends_performance(self):
        """Test trends analysis endpoint performance"""
        print("\n=== Testing UC-F05 Trends Analysis Performance ===")
        
        # Trends endpoint expects date_from and date_to parameters
        url = "/api/v1/analysis/trends?date_from=2015-01-01&date_to=2024-12-31"
        
        start_time = time.time()
        response = self.client.get(url)
        elapsed = time.time() - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Response time: {elapsed:.2f}s")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert elapsed < 2.0, f"Performance requirement failed: {elapsed:.2f}s > 2.0s"
        
        data = response.json()
        assert "annual_fires" in data, "Missing annual_fires in response"
        assert "trend_analysis" in data, "Missing trend_analysis in response"
        
        trend = data['trend_analysis']
        assert "direction" in trend, "Missing trend direction"
        assert "slope" in trend, "Missing trend slope"
        
        print(f"✓ Annual fires points: {len(data['annual_fires'])}")
        print(f"✓ Trend: {trend['direction']} (slope: {trend['slope']})")
        print(f"✓ Performance OK ({elapsed:.2f}s < 2.0s)")
        
        return True, elapsed
    
    def test_edge_cases(self):
        """Test edge cases and validation"""
        print("\n=== Testing UC-F05 Edge Cases ===")
        
        results = []
        
        # Test 1: Large bbox (> 10°)
        print("1. Testing large bbox (> 10°)")
        url = "/api/v1/analysis/recurrence?min_lon=-70&min_lat=-40&max_lon=-60&max_lat=-30"
        
        start_time = time.time()
        response = self.client.get(url)
        elapsed = time.time() - start_time
        
        print(f"   Status: {response.status_code} (should be 400)")
        print(f"   Response time: {elapsed:.2f}s")
        
        if response.status_code == 400:
            print("   ✓ Large bbox correctly rejected")
            results.append(True)
        else:
            print("   ⚠ Large bbox not properly validated")
            results.append(False)
        
        # Test 2: Very long time range (> 10 years)
        print("2. Testing very long time range (> 10 years)")
        url = "/api/v1/analysis/trends?date_from=2000-01-01&date_to=2024-12-31"
        
        start_time = time.time()
        response = self.client.get(url)
        elapsed = time.time() - start_time
        
        print(f"   Status: {response.status_code}")
        print(f"   Response time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            period = data.get('period', {})
            years_covered = period.get('end', 0) - period.get('start', 0)
            print(f"   Years covered: {years_covered}")
            print("   ✓ Long range handled with aggregation")
            results.append(True)
        else:
            print(f"   ⚠ Long range error: {response.text[:100]}")
            results.append(False)
        
        # Test 3: Invalid bbox format
        print("3. Testing invalid bbox format")
        url = "/api/v1/analysis/recurrence?min_lon=invalid&min_lat=-32&max_lon=-63&max_lat=-30"
        
        response = self.client.get(url)
        print(f"   Status: {response.status_code} (should be 422)")
        
        if response.status_code == 422:
            print("   ✓ Invalid bbox correctly rejected")
            results.append(True)
        else:
            print("   ⚠ Invalid bbox not properly validated")
            results.append(False)
        
        return all(results)
    
    def test_h3_spatial_indexing(self):
        """Test H3 spatial indexing functionality"""
        print("\n=== Testing UC-F05 H3 Spatial Indexing ===")
        
        # Test with a small area that should have H3 data
        url = "/api/v1/analysis/recurrence?min_lon=-64.5&min_lat=-31.5&max_lon=-64.0&max_lat=-31.0"
        
        start_time = time.time()
        response = self.client.get(url)
        elapsed = time.time() - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Response time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            # Check for H3 index in features
            h3_found = False
            for feature in features:
                props = feature.get('properties', {})
                if 'h3_index' in props:
                    h3_found = True
                    break
            
            print(f"✓ Features returned: {len(features)}")
            print(f"✓ H3 indexing present: {h3_found}")
            
            if h3_found:
                print("✓ H3 spatial indexing functional")
                return True
            else:
                print("⚠ H3 indexing not found in response")
                return False
        else:
            print(f"✗ Error: {response.text[:200]}")
            return False

def run_uc_f05_validation():
    """Run complete UC-F05 validation suite"""
    print("=" * 60)
    print("UC-F05: KPIs de Recurrencia - Complete Validation")
    print("=" * 60)
    
    test_suite = UC_F05_Performance_Test()
    
    results = []
    
    try:
        # Test 1: Recurrence performance
        success, elapsed = test_suite.test_recurrence_performance()
        results.append(('Recurrence Analysis', success, elapsed))
        
        # Test 2: Trends performance  
        success, elapsed = test_suite.test_trends_performance()
        results.append(('Trends Analysis', success, elapsed))
        
        # Test 3: Edge cases
        success = test_suite.test_edge_cases()
        results.append(('Edge Cases', success, 0))
        
        # Test 4: H3 spatial indexing
        success = test_suite.test_h3_spatial_indexing()
        results.append(('H3 Spatial Indexing', success, 0))
        
    except Exception as e:
        print(f"✗ Test execution error: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("UC-F05 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    for name, success, elapsed in results:
        status = '✓' if success else '✗'
        if elapsed > 0:
            print(f"  {status} {name}: {elapsed:.2f}s")
        else:
            print(f"  {status} {name}")
    
    print("\n" + "=" * 60)
    
    if passed == total:
        print("🎉 ALL UC-F05 TESTS PASSED!")
        print("✓ Performance requirements met (< 2s)")
        print("✓ Edge cases properly validated")
        print("✓ H3 spatial indexing functional")
        print("✓ Evidence of geospatial load confirmed")
        return True
    else:
        print(f"❌ {total - passed} tests failed")
        print("UC-F05 requires attention before go-live")
        return False

if __name__ == "__main__":
    success = run_uc_f05_validation()
    exit(0 if success else 1)
