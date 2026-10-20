"""
Comprehensive Automated Verification Suite for AFDAS
Tests all core workflows:
- Health & static routes
- Locations (LGAs, Wards, Polling Units) CRUD & Hierarchy
- Inventory Management (Batch creation, adjustment, inter-depot transfers, logs)
- Farmer Request Lifecycle (Submission, query, cancellation)
- Store Officer enrollment & history
- Blockchain Ledger, Tamper Demonstration, and Repair
- Bilingual (Hausa & English) SMS simulator
- CSV Export engines
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

    # 1. Health & Landing
    res = client.get('/health')
    assert_test("Health Endpoint", res.status_code == 200 and b"healthy" in res.data)
    res_land = client.get('/')
    assert_test("Landing Page", res_land.status_code == 200 and b"KNARDA" in res_land.data)
    res_app = client.get('/app')
    assert_test("Dashboard Page", res_app.status_code == 200 and b"AFDAS" in res_app.data)

    # 2. Locations: 44 LGAs Loaded & Hierarchy
    res_lgas = client.get('/api/locations/lga')
    lgas = json.loads(res_lgas.data)
    assert_test("44 Kano LGAs Loaded", len(lgas) == 44, f"Found {len(lgas)} LGAs")

    res_hier = client.get('/api/locations/hierarchy')
    hier = json.loads(res_hier.data)
    assert_test("Zonal Hierarchy Structure", 'Kano Central' in hier and 'Kano North' in hier and 'Kano South' in hier)

    # 3. Locations CRUD: Add LGA, Add Ward, Add PU, Delete PU
    res_add_lga = client.post('/api/locations/lga', json={'name': 'Kano Municipal Extension', 'zone': 'Kano Central', 'total_quota': 2000})
    lga_d = json.loads(res_add_lga.data)
    assert_test("Add LGA (CRUD)", lga_d.get('success') is True)
    new_lga_id = lga_d.get('lga_id')

    res_add_ward = client.post('/api/locations/ward', json={'lga_id': new_lga_id, 'name': 'Dan Agundi Ward', 'extension_officer': 'M. Sani'})
    ward_d = json.loads(res_add_ward.data)
    assert_test("Add Ward (CRUD)", ward_d.get('success') is True)
    new_ward_id = ward_d.get('ward_id')

    res_add_pu = client.post('/api/locations/polling_unit', json={'ward_id': new_ward_id, 'name': 'Dan Agundi Primary School', 'pu_code': 'PU-99-01', 'landmark': 'School Gate'})
    pu_d = json.loads(res_add_pu.data)
    assert_test("Add Polling Unit (CRUD)", pu_d.get('success') is True)
    new_pu_id = pu_d.get('pu_id')

    res_del_pu = client.delete(f'/api/locations/polling_unit/{new_pu_id}')
    del_pu_d = json.loads(res_del_pu.data)
    assert_test("Delete Polling Unit (CRUD)", del_pu_d.get('success') is True)

    # 4. Inventory Management: Add Batch, Adjust, Transfer, Logs
    res_inv = client.post('/api/inventory', json={
        'fertilizer_type': 'NPK 20:10:10 (Kano Formulation)',
        'quantity': 5000,
        'unit': 'bags',
        'location': 'Dawanau Central Depot',
        'batch_number': 'KN-TEST-BATCH-01',
        'supplier': 'Dangote Fertilizer Plant'
    })
    inv_d = json.loads(res_inv.data)
    assert_test("Add Inventory Batch", inv_d.get('success') is True)
    test_inv_id = inv_d.get('inventory_id')

    res_adj = client.post('/api/inventory/adjust', json={
        'inventory_id': test_inv_id,
        'adjustment': 500,
        'reason': 'Emergency Buffer Addition'
    })
    adj_d = json.loads(res_adj.data)
    assert_test("Adjust / Restock Inventory", adj_d.get('success') is True and adj_d.get('new_quantity') == 5500)

    res_trf = client.post('/api/inventory/transfer', json={
        'source_inventory_id': test_inv_id,
        'destination_location': 'Bichi Agro-Distribution Depot',
        'quantity': 1000,
        'driver_name': 'Malam Tanko Driver',
        'vehicle_plate': 'KNC-882-TR'
    })
    trf_d = json.loads(res_trf.data)
    assert_test("Inter-Depot Stock Transfer", trf_d.get('success') is True)

    res_logs = client.get('/api/inventory/logs')
    logs_d = json.loads(res_logs.data)
    assert_test("Inventory Movements Ledger", len(logs_d) > 0)

    # 5. Farmer Request Placement & Lifecycle
    res_req = client.post('/api/requests', json={
        'farmer_id': 'F004',
        'season_id': 1,
        'requested_bags': 5,
        'crop_type': 'Sorghum & Groundnut'
    })
    req_d = json.loads(res_req.data)
    assert_test("Farmer Request Placement", req_d.get('success') is True)
    new_req_id = req_d.get('request_id')

    res_f_reqs = client.get('/api/requests/farmer/F004')
    f_reqs = json.loads(res_f_reqs.data)
    assert_test("Query Farmer Requests", len(f_reqs) > 0)

    res_cancel = client.delete(f'/api/requests/{new_req_id}')
    cancel_d = json.loads(res_cancel.data)
    assert_test("Cancel Pending Farmer Request", cancel_d.get('success') is True)

    # 6. Store Officer Management
    res_officer = client.post('/api/officers', json={
        'officer_id': 'S009',
        'name': 'Malam Lawan Officer',
        'location': 'Kura Irrigation Distribution Hub'
    })
    off_d = json.loads(res_officer.data)
    assert_test("Register Store Officer", off_d.get('success') is True)

    res_off_hist = client.get('/api/distributions/officer/S001')
    off_hist = json.loads(res_off_hist.data)
    assert_test("Officer Dispensing History", isinstance(off_hist, list))

    # 7. Farmer Detail Dossier
    res_f_detail = client.get('/api/farmers/F001')
    f_detail = json.loads(res_f_detail.data)
    assert_test("Farmer Detail Dossier Inspection", 'passport_photo' in f_detail and 'requests' in f_detail)

    # 8. Bilingual SMS Simulation
    res_sms = client.get('/api/sms_simulation/1')
    sms_d = json.loads(res_sms.data)
    assert_test("Bilingual SMS Simulator", 'hausa_sms' in sms_d and 'english_sms' in sms_d)

    # 9. What-If Quota Allocation Simulator
    res_sim = client.post('/api/allocate/simulate', json={
        'total_pool': 50000,
        'bags_per_hectare': 2.0,
        'rice_multiplier': 1.2
    })
    sim_d = json.loads(res_sim.data)
    assert_test("What-If Quota Simulator", 'coverage_percentage' in sim_d and sim_d['total_demand_bags'] > 0)

    # 10. Blockchain Ledger & Tamper Demo
    res_bc_verify = client.get('/api/blockchain/verify?chain=distribution')
    bc_v = json.loads(res_bc_verify.data)
    assert_test("Blockchain Verification", bc_v.get('valid') is True)

    res_tamper = client.post('/api/blockchain/simulate_tamper')
    assert_test("Blockchain Tamper Demonstration", res_tamper.status_code == 200)

    res_repair = client.post('/api/blockchain/repair')
    repair_d = json.loads(res_repair.data)
    assert_test("Blockchain Integrity Repair", repair_d.get('success') is True)

    # 11. CSV Exports
    res_exp_f = client.get('/api/export/farmers')
    assert_test("Export Farmers CSV", res_exp_f.status_code == 200 and b"Farmer ID" in res_exp_f.data)

    res_exp_a = client.get('/api/export/allocations')
    assert_test("Export Allocations CSV", res_exp_a.status_code == 200 and b"Request ID" in res_exp_a.data)

    print("\n" + "="*50)
    print(f"ALL WORKFLOW TESTS COMPLETED: {passed}/{total} TESTS PASSED")
    print("="*50)
    return passed == total

if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
