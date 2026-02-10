#!/usr/bin/env python3
"""
UC-F05 Performance Test with Small Area
Tests performance with smaller bbox to validate H3 functionality
"""

import pytest
import time
import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

class UC_F05_Small_Area_Test:
    """Test UC-F05 with small area for better performance"""
    
    def __init__(self):
        self.client = TestClient(app)
        api_key = settings.ADMIN_API_KEY.get_secret_value() if settings.ADMIN_API_KEY else "admin-test-key"
        self.client.headers.update({"X-API-Key": api_key})
        
    def test_small_area_performance(self):
        """Test with very small bbox around Córdoba city"""
        print("\n=== Testing UC-F05 Small Area Performance ===")
        
        # Very small bbox around Córdoba city center
        url = "/api/v1/analysis/recurrence?min_lon=-64.2&min_lat=-31.45&max_lon=-64.15&max_lat=-31.4"
        
        start_time = time.time()
        response = self.client.get(url)
        elapsed = time.time() - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Response time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            cells = data.get('cells', [])
            print(f"✓ Cells returned: {len(cells)}")
            print(f"✓ Max intensity: {data.get('max_intensity', 0)}")
            
            if elapsed < 2.0:
                print(f"✓ Performance OK ({elapsed:.2f}s < 2.0s)")
                return True
            else:
                print(f"⚠ Performance warning ({elapsed:.2f}s > 2.0s)")
                return False
        else:
            print(f"✗ Error: {response.status_code}")
            return False
    
    def test_h3_functionality(self):
        """Test if H3 indexes are working correctly"""
        print("\n=== Testing H3 Functionality ===")
        
        # Test with area that should have H3 data
        url = "/api/v1/analysis/recurrence?min_lon=-64.5&min_lat=-31.5&max_lon=-64.0&max_lat=-31.0"
        
        response = self.client.get(url)
        
        if response.status_code == 200:
            data = response.json()
            cells = data.get('cells', [])
            
            # Check for H3 indexes in response
            h3_found = False
            for cell in cells:
                h3_index = cell.get('h3', '')
                if h3_index and h3_index != '':
                    h3_found = True
                    break
            
            print(f"✓ Cells returned: {len(cells)}")
            print(f"✓ H3 indexes present: {h3_found}")
            
            if h3_found:
                print("✓ H3 spatial indexing functional")
                return True
            else:
                print("⚠ No H3 indexes found in response")
                return False
        else:
            print(f"✗ Error: {response.status_code}")
            return False

def run_small_area_tests():
    """Run small area tests for UC-F05"""
    print("=" * 60)
    print("UC-F05: Small Area Performance Tests")
    print("=" * 60)
    
    test_suite = UC_F05_Small_Area_Test()
    
    results = []
    
    # Test 1: Small area performance
    success = test_suite.test_small_area_performance()
    results.append(('Small Area Performance', success))
    
    # Test 2: H3 functionality
    success = test_suite.test_h3_functionality()
    results.append(('H3 Functionality', success))
    
    # Summary
    print("\n" + "=" * 60)
    print("SMALL AREA TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    for name, success in results:
        status = '✓' if success else '✗'
        print(f"  {status} {name}")
    
    if passed == total:
        print("\n🎉 Small area tests passed!")
        print("H3 indexing is working, performance issue may be data volume related")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = run_small_area_tests()
    exit(0 if success else 1)
