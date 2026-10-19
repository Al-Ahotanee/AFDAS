"""
Automated Verification Suite for AFDAS
Tests all core API endpoints, smart allocation, verification, and blockchain ledger.
"""

from app import app
import json

def run_tests():
    client = app.test_client()
    passed = 0
    total = 0

    def assert_test(name, condition, details=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name}: {details}")

    # 1. Health check
    res = client.get('/health')
    assert_test("Health Endpoint", res.status_code == 200 and b"healthy" in res.data)

    # 2. Static Pages
    res_land = client.get('/')
    assert_test("Landing Page", res_land.status_code == 200 and b"KNARDA" in res_land.data)

    res_app = client.get('/app')
    assert_test("Dashboard Page", res_app.status_code == 200 and b"AFDAS" in res_app.data)

    # 3. LGAs Endpoint
    res_lgas = client.get('/api/locations/lga')
    lgas = json.loads(res_lgas.data)
    assert_test("44 Kano LGAs Loaded", len(lgas) == 44, f"Found {len(lgas)} LGAs")

    # 4. Auth - Admin
    res_admin = client.post('/api/login', json={'user_id': 'A001', 'password': 'Admin1'})
    admin_data = json.loads(res_admin.data)
    assert_test("Admin Login (A001)", admin_data.get('success') is True)

    # 5. Auth - Officer
    res_off = client.post('/api/login', json={'user_id': 'S001', 'password': 'Officer1'})
    off_data = json.loads(res_off.data)
    assert_test("Officer Login (S001)", off_data.get('success') is True)

    # 6. Auth - Farmer
    res_farm = client.post('/api/login', json={'user_id': 'F001', 'password': 'Farmer1'})
    farm_data = json.loads(res_farm.data)
    assert_test("Farmer Login (F001)", farm_data.get('success') is True)

    # 7. Stats Endpoint
    res_stats = client.get('/api/stats/admin')
    stats = json.loads(res_stats.data)
    assert_test("Admin Stats Telemetry", 'total_inventory_bags' in stats and stats['total_farmers'] > 0)

    # 8. Blockchain Verification
    res_bc = client.get('/api/blockchain/verify?chain=distribution')
    bc = json.loads(res_bc.data)
    assert_test("Blockchain Integrity", bc.get('valid') is True)

    # 9. Smart Allocation Execution
    res_alloc = client.post('/api/allocate/1')
    alloc = json.loads(res_alloc.data)
    assert_test("Algorithmic Allocation Execution", alloc.get('success') is True)

    # 10. QR & SMS Verification
    res_verify = client.post('/api/verify_qr', json={'qr_data': '{"request_id": 1}'})
    v_data = json.loads(res_verify.data)
    assert_test("Voucher Verification Endpoint", v_data.get('valid') is True and 'allocated_bags' in v_data)

    # 11. Printable Slip
    res_slip = client.get('/api/acknowledgement_slip/1')
    assert_test("Official Printable Slip", res_slip.status_code == 200 and b"Kano Agricultural Development Agency" in res_slip.data)

    print("\n" + "="*50)
    print(f"TEST RUN COMPLETED: {passed}/{total} TESTS PASSED")
    print("="*50)
    return passed == total

if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
