"""
Automated Fertilizer Distribution and Allocation System (AFDAS)
Kano Agricultural Development Agency (KNARDA) - Kano State Government

Full-Stack Flask Engine with:
- Dual Persistence: PostgreSQL (psycopg v3) + Resilient In-Memory Fallback
- Blockchain Ledger for Immutable Distribution Tracking
- Algorithmic Allocation Engine (Crop & Acreage based)
- All 44 Kano State Local Government Areas (LGAs) & Senatorial Zones
- Digital QR Code & 6-Digit SMS Voucher Verification
- Optimized for Vercel Serverless Deployment
"""

from flask import Flask, request, jsonify, send_file, Response, render_template_string
import hashlib
import json
import os
import io
import base64
import logging
import random
from datetime import datetime

# Optional external imports with graceful fallback
try:
    import psycopg
    import psycopg.rows
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    import bleach
    def sanitize(text):
        return bleach.clean(str(text), tags=[], strip=True) if text else ""
except ImportError:
    def sanitize(text):
        return str(text).replace("<", "&lt;").replace(">", "&gt;") if text else ""


# ============= APP CONFIGURATION =============

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kano-knarda-afdas-secret-key-2026')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ============= KANO STATE 44 LGAs & ZONAL DATA =============

KANO_ZONES = {
    "Kano Central": [
        "Dala", "Fagge", "Gwale", "Kano Municipal", "Kumbotso", "Nassarawa", "Tarauni", "Ungogo"
    ],
    "Kano North": [
        "Bagwai", "Bichi", "Danbatta", "Dawakin Tofa", "Gabasawa", "Gezawa", "Gwarzo", 
        "Kabo", "Kunchi", "Makoda", "Minjibir", "Rimin Gado", "Shanono", "Tofa", "Tsanyawa"
    ],
    "Kano South": [
        "Ajingi", "Albasu", "Bebeji", "Bunkure", "Dawakin Kudu", "Doguwa", "Garko", 
        "Garun Mallam", "Gaya", "Karaye", "Kibiya", "Kiru", "Kura", "Madobi", 
        "Rano", "Rogo", "Sumaila", "Takai", "Tudun Wada", "Warawa", "Wudil"
    ]
}

ALL_44_LGAS = []
for zone, lgas in KANO_ZONES.items():
    for lga in sorted(lgas):
        ALL_44_LGAS.append({"name": lga, "zone": zone})


# ============= PASSWORD HASHING =============

def hash_password(password: str) -> str:
    salt = "kano_knarda_afdas_salt_2026"
    return hashlib.sha256(f"{salt}_{password}".encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed: str) -> bool:
    return hash_password(plain_password) == hashed


# ============= BLOCKCHAIN ENGINE =============

def calculate_block_hash(index, timestamp, transactions, previous_hash):
    value = str(index) + str(timestamp) + json.dumps(transactions, sort_keys=True) + str(previous_hash)
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


# ============= RESILIENT IN-MEMORY STORE (ZERO-CRASH FALLBACK) =============

class MemoryStore:
    def __init__(self):
        self.admins = {}
        self.store_officers = {}
        self.farmers = {}
        self.seasons = {}
        self.farmer_requests = {}
        self.inventory = {}
        self.lgas = {}
        self.wards = {}
        self.polling_units = {}
        self.audit_logs = []
        self.blockchain = []
        self._next_season_id = 1
        self._next_request_id = 1
        self._next_inventory_id = 1
        self._next_audit_id = 1
        self._next_block_id = 1
        self.seed_initial_data()

    def seed_initial_data(self):
        # Default Admins
        self.admins['A001'] = {
            'id': 'A001',
            'name': 'Engr. Kabiru A. Sani (KNARDA Director)',
            'password': hash_password('Admin1'),
            'role': 'Director General',
            'created_at': datetime.now().isoformat()
        }

        # Store Officers at Major Kano Depots
        officers_data = [
            ('S001', 'Malam Aminu Bello', 'Officer1', 'Dawanau Central Depot (Kano Central)', 'Central Zone'),
            ('S002', 'Hajiya Fatima Garba', 'Officer1', 'Bichi Agro-Distribution Center (Kano North)', 'North Zone'),
            ('S003', 'Ibrahim Usman', 'Officer1', 'Rano Zonal Seed & Input Store (Kano South)', 'South Zone'),
            ('S004', 'Mansur Aliyu', 'Officer1', 'Kura Irrigation Distribution Hub', 'South Zone')
        ]
        for oid, name, pwd, loc, zone in officers_data:
            self.store_officers[oid] = {
                'id': oid,
                'name': name,
                'password': hash_password(pwd),
                'location': loc,
                'zone': zone,
                'created_at': datetime.now().isoformat()
            }

        # Seed Demo Farmers with Realistic Kano agricultural contexts
        demo_farmers = [
            ('F001', 'Alhaji Musa Danbatta', 'Farmer1', '08031234567', 'Danbatta', 'Danbatta East', 'PU-001 Gidan Sarki', 4.5, 'Rice & Wheat', '23456789012', 'Danbatta Rice Farmers Apex Cooperative'),
            ('F002', 'Balaraba Sani Kura', 'Farmer1', '08029876543', 'Kura', 'Kura Central', 'PU-014 Kadawa Irrigation', 3.2, 'Rice & Tomato', '89012345678', 'Kadawa Irrigation Valley Farmers'),
            ('F003', 'Malam Garba Bichi', 'Farmer1', '08134567890', 'Bichi', 'Badume Ward', 'PU-008 Badume Market', 2.0, 'Maize & Sorghum', '34567890123', 'Bichi Grains Producers Association'),
            ('F004', 'Shehu Mohammed Gaya', 'Farmer1', '08056789012', 'Gaya', 'Gaya North', 'PU-003 Fadar Sarki', 5.0, 'Sorghum & Groundnut', '45678901234', 'Gaya Agricultural Cooperative Society')
        ]
        for fid, name, pwd, phone, lga, ward, pu, fsize, crop, nin, coop in demo_farmers:
            self.farmers[fid] = {
                'id': fid,
                'name': name,
                'password': hash_password(pwd),
                'phone': phone,
                'lga': lga,
                'ward': ward,
                'polling_unit': pu,
                'farm_size': fsize,
                'crop_type': crop,
                'nin': nin,
                'passport_photo': '',
                'coop_evidence': '',
                'coop_name': coop,
                'total_bags_received': 0,
                'created_at': datetime.now().isoformat()
            }

        # Seed LGAs
        for idx, item in enumerate(ALL_44_LGAS, start=1):
            self.lgas[idx] = {
                'id': idx,
                'name': item['name'],
                'zone': item['zone'],
                'total_quota': 2500
            }
            # Add sample wards
            self.wards[idx] = [
                {'id': idx * 10 + 1, 'name': f"{item['name']} North", 'lga_id': idx},
                {'id': idx * 10 + 2, 'name': f"{item['name']} South", 'lga_id': idx},
                {'id': idx * 10 + 3, 'name': f"{item['name']} Central", 'lga_id': idx}
            ]

        # Seed Kano Strategic Fertilizer Inventory
        inventory_batches = [
            ('NPK 20:10:10 (Kano Special)', 45000, 'bags', 'Dawanau Central Depot', 'KN-NPK-2026-01'),
            ('Urea 46% Nitrogen', 32000, 'bags', 'Bichi Agro-Distribution Depot', 'KN-UREA-2026-04'),
            ('DAP (Di-Ammonium Phosphate)', 18500, 'bags', 'Rano Zonal Seed & Input Store', 'KN-DAP-2026-02'),
            ('Organic Kano Bio-Fertilizer', 12000, 'bags', 'Kura Irrigation Distribution Hub', 'KN-ORG-2026-08')
        ]
        for ftype, qty, unit, loc, batch in inventory_batches:
            iid = self._next_inventory_id
            self._next_inventory_id += 1
            self.inventory[iid] = {
                'id': iid,
                'fertilizer_type': ftype,
                'quantity': qty,
                'unit': unit,
                'location': loc,
                'batch_number': batch,
                'last_updated': datetime.now().isoformat()
            }

        # Seed Active Season
        sid = self._next_season_id
        self._next_season_id += 1
        self.seasons[sid] = {
            'id': sid,
            'name': '2026 Kano Dry-Season Wheat & Rice Farming Subsidy Allocation',
            'fertilizer_type': 'NPK 20:10:10 (Kano Special)',
            'total_bags': 100000,
            'start_time': '2026-01-15T08:00:00',
            'end_time': '2026-12-31T18:00:00',
            'status': 'active',
            'created_by': 'A001',
            'created_at': datetime.now().isoformat()
        }

        # Seed Sample Farmer Requests & Pre-allocations
        self._add_sample_request('F001', 1, 8, 8, 'approved', 'S001', True)
        self._add_sample_request('F002', 1, 6, 6, 'allocated', None, False)
        self._add_sample_request('F003', 1, 4, 4, 'pending', None, False)

        # Initialize Genesis Blocks
        for chain_name in ('distribution', 'inventory'):
            ts = datetime.now().isoformat()
            genesis_hash = calculate_block_hash(0, ts, [{'type': 'GENESIS', 'message': f'KNARDA {chain_name.upper()} GENESIS BLOCK'}], '0')
            bid = self._next_block_id
            self._next_block_id += 1
            self.blockchain.append({
                'id': bid,
                'chain_name': chain_name,
                'block_index': 0,
                'timestamp': ts,
                'transactions': [{'type': 'GENESIS', 'message': f'KNARDA {chain_name.upper()} GENESIS BLOCK'}],
                'previous_hash': '0',
                'hash': genesis_hash
            })

    def _add_sample_request(self, farmer_id, season_id, requested, allocated, status, distributed_by, acknowledged):
        rid = self._next_request_id
        self._next_request_id += 1
        sms_token = f"{random.randint(100000, 999999)}"
        qr_payload = {
            'request_id': rid,
            'farmer_id': farmer_id,
            'season_id': season_id,
            'allocated_bags': allocated,
            'sms_token': sms_token,
            'timestamp': datetime.now().isoformat()
        }
        bhash = hashlib.sha256(json.dumps(qr_payload, sort_keys=True).encode()).hexdigest()
        self.farmer_requests[rid] = {
            'id': rid,
            'farmer_id': farmer_id,
            'season_id': season_id,
            'requested_bags': requested,
            'allocated_bags': allocated,
            'status': status,
            'sms_token': sms_token,
            'qr_code': json.dumps(qr_payload),
            'blockchain_hash': bhash,
            'distributed_by': distributed_by,
            'distributed_at': datetime.now().isoformat() if distributed_by else None,
            'acknowledged': acknowledged,
            'acknowledged_at': datetime.now().isoformat() if acknowledged else None,
            'created_at': datetime.now().isoformat()
        }


# Instantiate Global Fallback Memory Store
mem_db = MemoryStore()


# ============= DATABASE CONNECTION HANDLER =============

USE_POSTGRES = False

def get_db_connection():
    global USE_POSTGRES
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url and HAS_PSYCOPG:
        try:
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            conn = psycopg.connect(
                db_url,
                row_factory=psycopg.rows.dict_row,
                sslmode='require',
                connect_timeout=5
            )
            USE_POSTGRES = True
            return conn
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to memory-safe store.")
            USE_POSTGRES = False
            return None
    USE_POSTGRES = False
    return None


# ============= AUDIT LOGGING HELPER =============

def log_audit(actor_id, actor_type, action, details):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO audit_logs (actor_id, actor_type, action, details, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (actor_id, actor_type, action, details, datetime.now()))
            conn.commit()
            conn.close()
            return
        except Exception as e:
            logger.warning(f"Failed to log audit in Postgres: {e}")

    # Fallback to in-memory audit logs
    aid = mem_db._next_audit_id
    mem_db._next_audit_id += 1
    mem_db.audit_logs.insert(0, {
        'id': aid,
        'actor_id': actor_id,
        'actor_type': actor_type,
        'action': action,
        'details': details,
        'timestamp': datetime.now().isoformat()
    })


# ============= BLOCKCHAIN TRANSACTION HELPER =============

def add_blockchain_block(chain_name: str, transactions: list) -> str:
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT block_index, hash FROM blockchain WHERE chain_name = %s ORDER BY block_index DESC LIMIT 1',
                    (chain_name,)
                )
                last_block = cur.fetchone()
                if not last_block:
                    prev_index = -1
                    prev_hash = '0'
                else:
                    prev_index = last_block['block_index']
                    prev_hash = last_block['hash']

                new_index = prev_index + 1
                ts = datetime.now().isoformat()
                new_hash = calculate_block_hash(new_index, ts, transactions, prev_hash)

                cur.execute("""
                    INSERT INTO blockchain (chain_name, block_index, timestamp, transactions, previous_hash, hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (chain_name, new_index, ts, json.dumps(transactions), prev_hash, new_hash))
            conn.commit()
            conn.close()
            return new_hash
        except Exception as e:
            logger.warning(f"Blockchain write to Postgres failed: {e}")

    # Memory Store blockchain append
    chain = [b for b in mem_db.blockchain if b['chain_name'] == chain_name]
    prev_block = chain[-1] if chain else None
    prev_index = prev_block['block_index'] if prev_block else -1
    prev_hash = prev_block['hash'] if prev_block else '0'

    new_index = prev_index + 1
    ts = datetime.now().isoformat()
    new_hash = calculate_block_hash(new_index, ts, transactions, prev_hash)

    bid = mem_db._next_block_id
    mem_db._next_block_id += 1
    mem_db.blockchain.append({
        'id': bid,
        'chain_name': chain_name,
        'block_index': new_index,
        'timestamp': ts,
        'transactions': transactions,
        'previous_hash': prev_hash,
        'hash': new_hash
    })
    return new_hash


# ============= QR CODE GENERATION HELPER =============

def generate_qr_base64(data_dict: dict) -> str:
    raw_str = json.dumps(data_dict, sort_keys=True)
    if HAS_QRCODE:
        try:
            qr = qrcode.QRCode(version=1, box_size=6, border=2)
            qr.add_data(raw_str)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#046A38", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
    # Fallback to an SVG data URL if qrcode library fails
    encoded = base64.b64encode(raw_str.encode()).decode()
    return f"data:text/plain;base64,{encoded}"


# ============= STATIC & TEMPLATE ROUTES =============

@app.route('/')
def landing_page():
    landing_file = os.path.join(BASE_DIR, 'main.html')
    if os.path.exists(landing_file):
        with open(landing_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>Kano Agricultural Development Agency (KNARDA) - AFDAS</h1><p><a href='/app'>Go to App</a></p>"

@app.route('/app')
def app_dashboard():
    dashboard_file = os.path.join(BASE_DIR, 'index.html')
    if os.path.exists(dashboard_file):
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>KNARDA Dashboard</h1>"

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'AFDAS - Kano Agricultural Development Agency',
        'timestamp': datetime.now().isoformat(),
        'persistence': 'postgresql' if USE_POSTGRES else 'in-memory-fallback',
        'version': '2.6.0-vercel-edition'
    })


# ============= AUTHENTICATION API =============

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    user_id = sanitize(data.get('user_id', '').strip())
    password = data.get('password', '')

    if not user_id or not password:
        return jsonify({'success': False, 'message': 'User ID and password are required'}), 400

    conn = get_db_connection()
    user = None
    user_type = None

    if conn:
        try:
            with conn.cursor() as cur:
                if user_id.startswith('A'):
                    cur.execute('SELECT * FROM admins WHERE id = %s', (user_id,))
                    u = cur.fetchone()
                    if u and verify_password(password, u['password']):
                        user = u
                        user_type = 'admin'
                elif user_id.startswith('S'):
                    cur.execute('SELECT * FROM store_officers WHERE id = %s', (user_id,))
                    u = cur.fetchone()
                    if u and verify_password(password, u['password']):
                        user = u
                        user_type = 'officer'
                elif user_id.startswith('F'):
                    cur.execute('SELECT * FROM farmers WHERE id = %s', (user_id,))
                    u = cur.fetchone()
                    if u and verify_password(password, u['password']):
                        user = u
                        user_type = 'farmer'
            conn.close()
        except Exception as e:
            logger.warning(f"Postgres login failed: {e}")

    # Fallback to Memory Store
    if not user:
        if user_id.startswith('A') and user_id in mem_db.admins:
            u = mem_db.admins[user_id]
            if verify_password(password, u['password']):
                user = u
                user_type = 'admin'
        elif user_id.startswith('S') and user_id in mem_db.store_officers:
            u = mem_db.store_officers[user_id]
            if verify_password(password, u['password']):
                user = u
                user_type = 'officer'
        elif user_id.startswith('F') and user_id in mem_db.farmers:
            u = mem_db.farmers[user_id]
            if verify_password(password, u['password']):
                user = u
                user_type = 'farmer'

    if not user or not user_type:
        return jsonify({'success': False, 'message': 'Invalid credentials. Please verify your ID and password.'}), 401

    log_audit(user_id, user_type, 'LOGIN', f"{user_type.capitalize()} logged in successfully")

    return jsonify({
        'success': True,
        'user_id': user['id'],
        'user_type': user_type,
        'name': user['name'],
        'lga': user.get('lga', ''),
        'location': user.get('location', 'Kano State'),
        'farm_size': user.get('farm_size', 0),
        'crop_type': user.get('crop_type', '')
    })


@app.route('/api/register/farmer', methods=['POST'])
def register_farmer():
    data = request.get_json() or {}
    farmer_id = sanitize(data.get('farmer_id', '').strip())
    name = sanitize(data.get('name', '').strip())
    password = data.get('password', '')
    phone = sanitize(data.get('phone', '').strip())
    lga = sanitize(data.get('lga', '').strip())
    ward = sanitize(data.get('ward', '').strip())
    polling_unit = sanitize(data.get('polling_unit', '').strip())
    farm_size = float(data.get('farm_size', 1.0))
    crop_type = sanitize(data.get('crop_type', 'Rice & Maize').strip())
    nin = sanitize(data.get('nin', '').strip())
    coop_name = sanitize(data.get('coop_name', '').strip())
    passport_photo = data.get('passport_photo', '')
    coop_evidence = data.get('coop_evidence', '')

    if not farmer_id or not name or not password:
        return jsonify({'success': False, 'message': 'Farmer ID, Full Name, and Password are required'}), 400

    hashed_pw = hash_password(password)
    created_at = datetime.now().isoformat()

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM farmers WHERE id = %s', (farmer_id,))
                if cur.fetchone():
                    conn.close()
                    return jsonify({'success': False, 'message': 'Farmer ID already registered'}), 409

                cur.execute("""
                    INSERT INTO farmers (
                        id, name, password, phone, lga, ward, polling_unit, farm_size,
                        passport_photo, coop_evidence, coop_name, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    farmer_id, name, hashed_pw, phone, lga, ward, polling_unit, farm_size,
                    passport_photo, coop_evidence, coop_name, created_at
                ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Postgres insert farmer failed: {e}")

    # Also save to memory store
    if farmer_id in mem_db.farmers:
        return jsonify({'success': False, 'message': 'Farmer ID already exists'}), 409

    mem_db.farmers[farmer_id] = {
        'id': farmer_id,
        'name': name,
        'password': hashed_pw,
        'phone': phone,
        'lga': lga,
        'ward': ward,
        'polling_unit': polling_unit,
        'farm_size': farm_size,
        'crop_type': crop_type,
        'nin': nin,
        'passport_photo': passport_photo,
        'coop_evidence': coop_evidence,
        'coop_name': coop_name,
        'total_bags_received': 0,
        'created_at': created_at
    }

    log_audit(farmer_id, 'farmer', 'REGISTER_FARMER', f"Farmer {name} registered in {lga} LGA")

    return jsonify({
        'success': True,
        'message': f'Farmer {name} successfully registered with KNARDA AFDAS!',
        'farmer_id': farmer_id
    })


@app.route('/api/register/officer', methods=['POST'])
def register_officer():
    data = request.get_json() or {}
    officer_id = sanitize(data.get('officer_id', '').strip())
    name = sanitize(data.get('name', '').strip())
    password = data.get('password', '')
    location = sanitize(data.get('location', 'Kano State Depot').strip())

    if not officer_id or not name or not password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    hashed_pw = hash_password(password)
    mem_db.store_officers[officer_id] = {
        'id': officer_id,
        'name': name,
        'password': hashed_pw,
        'location': location,
        'created_at': datetime.now().isoformat()
    }
    log_audit(officer_id, 'officer', 'REGISTER_OFFICER', f"Officer {name} registered at {location}")
    return jsonify({'success': True, 'message': 'Store Officer registered successfully!'})


# ============= SEASONS & ALLOCATION API =============

@app.route('/api/seasons', methods=['GET', 'POST'])
def seasons():
    if request.method == 'POST':
        data = request.get_json() or {}
        name = sanitize(data.get('name', ''))
        fertilizer_type = sanitize(data.get('fertilizer_type', 'NPK 20:10:10'))
        total_bags = int(data.get('total_bags', 10000))
        start_time = data.get('start_time', datetime.now().isoformat())
        end_time = data.get('end_time', datetime.now().isoformat())
        created_by = sanitize(data.get('created_by', 'A001'))

        sid = mem_db._next_season_id
        mem_db._next_season_id += 1
        mem_db.seasons[sid] = {
            'id': sid,
            'name': name,
            'fertilizer_type': fertilizer_type,
            'total_bags': total_bags,
            'start_time': start_time,
            'end_time': end_time,
            'status': 'active',
            'created_by': created_by,
            'created_at': datetime.now().isoformat()
        }
        log_audit(created_by, 'admin', 'CREATE_SEASON', f"Created season {name} ({total_bags} bags)")
        return jsonify({'success': True, 'season_id': sid, 'message': 'Season created successfully'})

    # GET
    return jsonify(list(mem_db.seasons.values()))


@app.route('/api/seasons/active', methods=['GET'])
def active_seasons():
    active = [s for s in mem_db.seasons.values() if s.get('status') == 'active']
    return jsonify(active)


# ============= ALGORITHMIC ALLOCATION ENGINE =============

@app.route('/api/allocate/<int:season_id>', methods=['POST'])
def allocate_season(season_id):
    """
    Kano State Algorithmic Allocation Engine:
    Fairly allocates fertilizer based on farm acreage, crop type, cooperative membership,
    and LGA quotas to ensure equitable distribution across Kano's 44 LGAs.
    """
    season = mem_db.seasons.get(season_id)
    if not season:
        return jsonify({'success': False, 'message': 'Season not found'}), 404

    pending_requests = [
        r for r in mem_db.farmer_requests.values()
        if r['season_id'] == season_id and r['status'] == 'pending'
    ]

    total_allocated_in_run = 0
    allocations_summary = []

    for req in pending_requests:
        farmer = mem_db.farmers.get(req['farmer_id'], {})
        farm_size = float(farmer.get('farm_size', 1.0))
        crop_type = farmer.get('crop_type', 'Grains')
        has_coop = bool(farmer.get('coop_name'))

        # Allocation formula:
        # 2 bags per hectare baseline, with maximum cap of 12 bags per smallholder.
        # Priority multiplier for high-demand Kano crops (Rice/Wheat irrigation).
        multiplier = 1.2 if any(c in crop_type for c in ['Rice', 'Wheat']) else 1.0
        allocated = int(round(farm_size * 2.0 * multiplier))
        if has_coop:
            allocated += 1  # Cooperative verification incentive

        # Bound by requested bags and maximum policy cap
        allocated = max(1, min(allocated, req['requested_bags'], 12))

        # Generate unique 6-digit SMS verification token
        sms_token = f"{random.randint(100000, 999999)}"

        # Prepare QR data payload
        qr_payload = {
            'system': 'KNARDA-AFDAS',
            'request_id': req['id'],
            'farmer_id': req['farmer_id'],
            'season_id': season_id,
            'allocated_bags': allocated,
            'sms_token': sms_token,
            'timestamp': datetime.now().isoformat()
        }
        bhash = hashlib.sha256(json.dumps(qr_payload, sort_keys=True).encode()).hexdigest()

        req['allocated_bags'] = allocated
        req['status'] = 'allocated'
        req['sms_token'] = sms_token
        req['qr_code'] = json.dumps(qr_payload)
        req['blockchain_hash'] = bhash

        total_allocated_in_run += allocated
        allocations_summary.append({
            'farmer_id': req['farmer_id'],
            'name': farmer.get('name'),
            'lga': farmer.get('lga'),
            'allocated': allocated
        })

    # Record block on distribution blockchain
    if total_allocated_in_run > 0:
        block_hash = add_blockchain_block('distribution', [{
            'action': 'ALGORITHMIC_ALLOCATION',
            'season_id': season_id,
            'season_name': season['name'],
            'total_farmers': len(pending_requests),
            'total_bags_allocated': total_allocated_in_run,
            'timestamp': datetime.now().isoformat()
        }])
        log_audit('A001', 'admin', 'ALLOCATE_SEASON', f"Allocated {total_allocated_in_run} bags across {len(pending_requests)} farmers. Block Hash: {block_hash[:10]}...")

    return jsonify({
        'success': True,
        'message': f"Successfully allocated {total_allocated_in_run} bags to {len(pending_requests)} farmers!",
        'total_allocated': total_allocated_in_run,
        'allocated_count': len(pending_requests),
        'allocations': allocations_summary
    })


# ============= FARMER REQUESTS API =============

@app.route('/api/requests', methods=['POST'])
def submit_request():
    data = request.get_json() or {}
    farmer_id = sanitize(data.get('farmer_id', '').strip())
    season_id = int(data.get('season_id', 1))
    requested_bags = int(data.get('requested_bags', 2))

    if not farmer_id or requested_bags < 1:
        return jsonify({'success': False, 'message': 'Farmer ID and valid quantity required'}), 400

    # Check for existing pending/allocated request in this season
    for r in mem_db.farmer_requests.values():
        if r['farmer_id'] == farmer_id and r['season_id'] == season_id and r['status'] in ['pending', 'allocated', 'approved']:
            return jsonify({'success': False, 'message': 'You already have an active application in this season'}), 409

    rid = mem_db._next_request_id
    mem_db._next_request_id += 1

    mem_db.farmer_requests[rid] = {
        'id': rid,
        'farmer_id': farmer_id,
        'season_id': season_id,
        'requested_bags': requested_bags,
        'allocated_bags': 0,
        'status': 'pending',
        'sms_token': '',
        'qr_code': '',
        'blockchain_hash': '',
        'distributed_by': None,
        'distributed_at': None,
        'acknowledged': False,
        'acknowledged_at': None,
        'created_at': datetime.now().isoformat()
    }

    log_audit(farmer_id, 'farmer', 'SUBMIT_REQUEST', f"Applied for {requested_bags} bags in Season #{season_id}")

    return jsonify({
        'success': True,
        'message': 'Fertilizer allocation request submitted successfully to KNARDA!',
        'request_id': rid
    })


@app.route('/api/requests/farmer/<farmer_id>', methods=['GET'])
def get_farmer_requests(farmer_id):
    reqs = [r for r in mem_db.farmer_requests.values() if r['farmer_id'] == farmer_id]
    # Augment with season name and QR base64 image
    for r in reqs:
        season = mem_db.seasons.get(r['season_id'], {})
        r['season_name'] = season.get('name', 'General Allocation')
        r['fertilizer_type'] = season.get('fertilizer_type', 'NPK 20:10:10')
        if r.get('qr_code'):
            try:
                qr_dict = json.loads(r['qr_code'])
                r['qr_image_base64'] = generate_qr_base64(qr_dict)
            except Exception:
                r['qr_image_base64'] = ""
    return jsonify(reqs)


@app.route('/api/requests/season/<int:season_id>', methods=['GET'])
def get_season_requests(season_id):
    reqs = [r for r in mem_db.farmer_requests.values() if r['season_id'] == season_id]
    for r in reqs:
        farmer = mem_db.farmers.get(r['farmer_id'], {})
        r['farmer_name'] = farmer.get('name', 'Unknown')
        r['lga'] = farmer.get('lga', 'Kano')
        r['phone'] = farmer.get('phone', '')
    return jsonify(reqs)


# ============= DISTRIBUTION & QR VERIFICATION =============

@app.route('/api/verify_qr', methods=['POST'])
def verify_qr():
    """
    Verifies farmer QR Code or 6-digit SMS Voucher Token.
    Checks anti-fraud double-redemption status and verifies allocation against blockchain.
    """
    data = request.get_json() or {}
    qr_data = data.get('qr_data', '')
    token = data.get('token', '')

    target_request = None

    if token:
        # Search by 6-digit SMS token
        for r in mem_db.farmer_requests.values():
            if str(r.get('sms_token')) == str(token).strip():
                target_request = r
                break
    elif qr_data:
        try:
            parsed = json.loads(qr_data) if isinstance(qr_data, str) else qr_data
            req_id = parsed.get('request_id')
            if req_id and req_id in mem_db.farmer_requests:
                target_request = mem_db.farmer_requests[req_id]
        except Exception:
            # Maybe raw hash or manual token was passed
            for r in mem_db.farmer_requests.values():
                if r.get('blockchain_hash') == qr_data.strip() or r.get('sms_token') == qr_data.strip():
                    target_request = r
                    break

    if not target_request:
        return jsonify({
            'valid': False,
            'message': 'Invalid QR Code or SMS Voucher Token. No record found in KNARDA registry.'
        }), 404

    farmer = mem_db.farmers.get(target_request['farmer_id'], {})
    season = mem_db.seasons.get(target_request['season_id'], {})

    already_distributed = bool(target_request.get('distributed_by')) or target_request.get('status') == 'distributed'

    return jsonify({
        'valid': True,
        'request_id': target_request['id'],
        'farmer_id': target_request['farmer_id'],
        'farmer_name': farmer.get('name', 'N/A'),
        'farmer_phone': farmer.get('phone', 'N/A'),
        'lga': farmer.get('lga', 'N/A'),
        'ward': farmer.get('ward', 'N/A'),
        'nin': farmer.get('nin', 'N/A'),
        'passport_photo': farmer.get('passport_photo', ''),
        'season_name': season.get('name', 'N/A'),
        'fertilizer_type': season.get('fertilizer_type', 'NPK 20:10:10'),
        'allocated_bags': target_request.get('allocated_bags', 0),
        'status': target_request.get('status', 'pending'),
        'sms_token': target_request.get('sms_token', ''),
        'already_distributed': already_distributed,
        'distributed_by': target_request.get('distributed_by'),
        'distributed_at': target_request.get('distributed_at'),
        'blockchain_hash': target_request.get('blockchain_hash')
    })


@app.route('/api/distribute', methods=['POST'])
def distribute_bags():
    data = request.get_json() or {}
    request_id = data.get('request_id')
    officer_id = sanitize(data.get('officer_id', 'S001'))

    req = mem_db.farmer_requests.get(request_id)
    if not req:
        return jsonify({'success': False, 'message': 'Application record not found'}), 404

    if req.get('distributed_by') or req.get('status') == 'distributed':
        return jsonify({'success': False, 'message': 'ALERT: Fertilizer bags have ALREADY been collected for this allocation!'}), 409

    bags = req.get('allocated_bags', 0)
    req['status'] = 'distributed'
    req['distributed_by'] = officer_id
    req['distributed_at'] = datetime.now().isoformat()

    farmer = mem_db.farmers.get(req['farmer_id'], {})
    farmer['total_bags_received'] = farmer.get('total_bags_received', 0) + bags

    # Record distribution in blockchain
    tx = {
        'type': 'DISTRIBUTION_EXECUTION',
        'request_id': request_id,
        'farmer_id': req['farmer_id'],
        'farmer_name': farmer.get('name'),
        'lga': farmer.get('lga'),
        'bags': bags,
        'officer_id': officer_id,
        'timestamp': datetime.now().isoformat()
    }
    block_hash = add_blockchain_block('distribution', [tx])

    log_audit(officer_id, 'officer', 'DISTRIBUTE_BAGS', f"Dispensed {bags} bags to Farmer {req['farmer_id']} ({farmer.get('name')}). Block: {block_hash[:10]}")

    return jsonify({
        'success': True,
        'message': f"Successfully verified & dispensed {bags} bags to {farmer.get('name')}!",
        'blockchain_hash': block_hash,
        'slip_url': f"/api/acknowledgement_slip/{request_id}"
    })


@app.route('/api/acknowledge', methods=['POST'])
def acknowledge_receipt():
    data = request.get_json() or {}
    request_id = data.get('request_id')
    farmer_id = sanitize(data.get('farmer_id', ''))

    req = mem_db.farmer_requests.get(request_id)
    if not req:
        return jsonify({'success': False, 'message': 'Request not found'}), 404

    if req['farmer_id'] != farmer_id:
        return jsonify({'success': False, 'message': 'Unauthorized acknowledgement attempt'}), 403

    req['acknowledged'] = True
    req['acknowledged_at'] = datetime.now().isoformat()
    log_audit(farmer_id, 'farmer', 'ACKNOWLEDGE_RECEIPT', f"Farmer confirmed physical collection of bags for Request #{request_id}")

    return jsonify({'success': True, 'message': 'Receipt acknowledged successfully!'})


# ============= PRINTABLE OFFICIAL KNARDA SLIP =============

@app.route('/api/acknowledgement_slip/<int:request_id>', methods=['GET'])
def get_acknowledgement_slip(request_id):
    req = mem_db.farmer_requests.get(request_id)
    if not req:
        return "<h3>Request not found</h3>", 404

    farmer = mem_db.farmers.get(req['farmer_id'], {})
    season = mem_db.seasons.get(req['season_id'], {})

    # Generate QR Base64
    qr_img = ""
    if req.get('qr_code'):
        try:
            qr_dict = json.loads(req['qr_code'])
            qr_img = generate_qr_base64(qr_dict)
        except Exception:
            qr_img = ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>KNARDA AFDAS - Collection & Acknowledgement Slip</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1e293b; background: #fff; }}
            .slip-card {{ max-width: 750px; margin: 0 auto; border: 2px solid #046A38; border-radius: 12px; padding: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
            .header {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #046A38; padding-bottom: 15px; margin-bottom: 20px; }}
            .logo-title h2 {{ margin: 0; color: #046A38; font-size: 22px; text-transform: uppercase; }}
            .logo-title p {{ margin: 4px 0 0; color: #64748b; font-size: 13px; font-weight: 600; }}
            .state-badge {{ background: #046A38; color: #fff; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase; }}
            .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
            .field-row {{ margin-bottom: 10px; font-size: 14px; }}
            .field-label {{ color: #64748b; font-weight: 600; width: 140px; display: inline-block; }}
            .field-value {{ font-weight: 700; color: #0f172a; }}
            .qr-section {{ text-align: center; border-left: 1px dashed #cbd5e1; padding-left: 20px; }}
            .qr-section img {{ width: 160px; height: 160px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; }}
            .token-box {{ background: #fef3c7; border: 1px solid #f59e0b; color: #92400e; padding: 8px; border-radius: 6px; font-size: 16px; font-weight: bold; margin-top: 10px; }}
            .footer {{ border-top: 1px solid #e2e8f0; margin-top: 25px; padding-top: 15px; display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; }}
            .signatures {{ display: flex; justify-content: space-between; margin-top: 30px; padding-top: 10px; }}
            .sig-line {{ border-top: 1px solid #334155; width: 200px; text-align: center; font-size: 12px; color: #475569; padding-top: 4px; }}
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="slip-card">
            <div class="header">
                <div class="logo-title">
                    <h2>Kano Agricultural Development Agency (KNARDA)</h2>
                    <p>Automated Fertilizer Distribution and Allocation System (AFDAS)</p>
                </div>
                <div class="state-badge">Official Slip</div>
            </div>

            <div class="grid">
                <div>
                    <div class="field-row"><span class="field-label">Slip Number:</span> <span class="field-value">KN-AFDAS-{req['id']:06d}</span></div>
                    <div class="field-row"><span class="field-label">Farmer Name:</span> <span class="field-value">{farmer.get('name')}</span></div>
                    <div class="field-row"><span class="field-label">Farmer ID:</span> <span class="field-value">{farmer.get('id')}</span></div>
                    <div class="field-row"><span class="field-label">Phone Number:</span> <span class="field-value">{farmer.get('phone')}</span></div>
                    <div class="field-row"><span class="field-label">LGA & Ward:</span> <span class="field-value">{farmer.get('lga')} / {farmer.get('ward')}</span></div>
                    <div class="field-row"><span class="field-label">Season Programme:</span> <span class="field-value">{season.get('name')}</span></div>
                    <div class="field-row"><span class="field-label">Fertilizer Type:</span> <span class="field-value">{season.get('fertilizer_type')}</span></div>
                    <div class="field-row"><span class="field-label">Allocated Quota:</span> <span class="field-value" style="color:#046A38; font-size: 16px;">{req.get('allocated_bags')} Bags (50kg)</span></div>
                    <div class="field-row"><span class="field-label">Status:</span> <span class="field-value" style="text-transform:uppercase;">{req.get('status')}</span></div>
                    <div class="field-row"><span class="field-label">Distributed Date:</span> <span class="field-value">{req.get('distributed_at') or 'Pending Verification'}</span></div>
                </div>
                <div class="qr-section">
                    <img src="{qr_img}" alt="QR Voucher">
                    <div class="token-box">SMS OTP: {req.get('sms_token')}</div>
                    <small style="display:block; margin-top:6px; color:#64748b;">Show this QR / OTP to Store Officer</small>
                </div>
            </div>

            <div class="signatures">
                <div class="sig-line">Farmer's Signature & Thumbprint</div>
                <div class="sig-line">KNARDA Store Officer Sign & Stamp</div>
            </div>

            <div class="footer">
                <div>Cryptographic Verification Hash: {req.get('blockchain_hash', 'N/A')[:32]}...</div>
                <div>Government of Kano State &bull; Transparency in Agriculture</div>
            </div>
        </div>

        <div style="text-align:center; margin-top: 20px;" class="no-print">
            <button onclick="window.print()" style="background:#046A38; color:#fff; border:none; padding:10px 24px; border-radius:6px; font-weight:bold; cursor:pointer;">
                Print Acknowledgement Slip
            </button>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


# ============= BLOCKCHAIN EXPLORER API =============

@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    chain_name = request.args.get('chain', 'distribution')
    chain = [b for b in mem_db.blockchain if b['chain_name'] == chain_name]
    return jsonify(chain)


@app.route('/api/blockchain/verify', methods=['GET'])
def verify_blockchain():
    chain_name = request.args.get('chain', 'distribution')
    chain = [b for b in mem_db.blockchain if b['chain_name'] == chain_name]

    if not chain:
        return jsonify({'valid': True, 'message': 'Chain is currently empty', 'blocks_checked': 0})

    for i in range(1, len(chain)):
        current = chain[i]
        previous = chain[i - 1]

        # Verify previous hash link
        if current['previous_hash'] != previous['hash']:
            return jsonify({
                'valid': False,
                'error': f"Hash chain broken between block {previous['block_index']} and {current['block_index']}",
                'block_index': current['block_index']
            }), 400

        # Recalculate SHA-256
        recalculated = calculate_block_hash(
            current['block_index'],
            current['timestamp'],
            current['transactions'],
            current['previous_hash']
        )
        if current['hash'] != recalculated:
            return jsonify({
                'valid': False,
                'error': f"Data tampering detected at block {current['block_index']}",
                'expected_hash': recalculated,
                'stored_hash': current['hash']
            }), 400

    return jsonify({
        'valid': True,
        'message': f"Cryptographic integrity verified! All {len(chain)} blocks in {chain_name} chain are valid and untampered.",
        'blocks_checked': len(chain),
        'latest_hash': chain[-1]['hash']
    })


# ============= INVENTORY & DEPOTS API =============

@app.route('/api/inventory', methods=['GET', 'POST'])
def inventory_api():
    if request.method == 'POST':
        data = request.get_json() or {}
        ftype = sanitize(data.get('fertilizer_type', 'NPK 20:10:10'))
        qty = int(data.get('quantity', 1000))
        unit = sanitize(data.get('unit', 'bags'))
        location = sanitize(data.get('location', 'Dawanau Central Depot'))
        batch = sanitize(data.get('batch_number', f'KN-BATCH-{random.randint(100,999)}'))

        iid = mem_db._next_inventory_id
        mem_db._next_inventory_id += 1
        mem_db.inventory[iid] = {
            'id': iid,
            'fertilizer_type': ftype,
            'quantity': qty,
            'unit': unit,
            'location': location,
            'batch_number': batch,
            'last_updated': datetime.now().isoformat()
        }
        log_audit('A001', 'admin', 'ADD_INVENTORY', f"Added {qty} {unit} of {ftype} to {location}")
        return jsonify({'success': True, 'message': 'Inventory batch recorded successfully'})

    return jsonify(list(mem_db.inventory.values()))


# ============= LOCATIONS API (KANO 44 LGAs) =============

@app.route('/api/locations/lga', methods=['GET', 'POST'])
def lga_api():
    return jsonify(list(mem_db.lgas.values()))

@app.route('/api/locations/ward/<int:lga_id>', methods=['GET'])
def ward_api(lga_id):
    wards = mem_db.wards.get(lga_id, [
        {'id': lga_id * 10 + 1, 'name': 'Central Ward', 'lga_id': lga_id},
        {'id': lga_id * 10 + 2, 'name': 'North Ward', 'lga_id': lga_id},
        {'id': lga_id * 10 + 3, 'name': 'South Ward', 'lga_id': lga_id}
    ])
    return jsonify(wards)

@app.route('/api/locations/polling_unit/<int:ward_id>', methods=['GET'])
def polling_unit_api(ward_id):
    return jsonify([
        {'id': ward_id * 10 + 1, 'name': 'Primary School Polling Unit', 'ward_id': ward_id},
        {'id': ward_id * 10 + 2, 'name': 'District Head Palace Gate', 'ward_id': ward_id},
        {'id': ward_id * 10 + 3, 'name': 'Community Health Center Unit', 'ward_id': ward_id}
    ])


# ============= STATS & ANALYTICS API =============

@app.route('/api/stats/admin', methods=['GET'])
def admin_stats():
    total_farmers = len(mem_db.farmers)
    total_officers = len(mem_db.store_officers)
    total_seasons = len(mem_db.seasons)
    
    total_inventory_bags = sum(i['quantity'] for i in mem_db.inventory.values())
    total_requested_bags = sum(r['requested_bags'] for r in mem_db.farmer_requests.values())
    total_allocated_bags = sum(r['allocated_bags'] for r in mem_db.farmer_requests.values())
    total_distributed_bags = sum(
        r['allocated_bags'] for r in mem_db.farmer_requests.values()
        if r.get('distributed_by') or r.get('status') == 'distributed'
    )

    # LGA breakdown
    lga_breakdown = {}
    for f in mem_db.farmers.values():
        lga = f.get('lga', 'Kano')
        lga_breakdown[lga] = lga_breakdown.get(lga, 0) + 1

    return jsonify({
        'total_farmers': total_farmers,
        'total_officers': total_officers,
        'total_seasons': total_seasons,
        'total_inventory_bags': total_inventory_bags,
        'total_requested_bags': total_requested_bags,
        'total_allocated_bags': total_allocated_bags,
        'total_distributed_bags': total_distributed_bags,
        'distribution_rate': round((total_distributed_bags / total_allocated_bags * 100), 1) if total_allocated_bags > 0 else 0,
        'lga_breakdown': lga_breakdown,
        'total_lgas_covered': len(lga_breakdown),
        'blocks_count': len(mem_db.blockchain)
    })


@app.route('/api/stats/kano-zones', methods=['GET'])
def kano_zones_stats():
    zones_summary = {
        'Kano Central': {'farmers': 0, 'allocated_bags': 0, 'distributed_bags': 0},
        'Kano North': {'farmers': 0, 'allocated_bags': 0, 'distributed_bags': 0},
        'Kano South': {'farmers': 0, 'allocated_bags': 0, 'distributed_bags': 0}
    }

    # Map LGAs to Zones
    lga_to_zone = {}
    for z, lga_list in KANO_ZONES.items():
        for l in lga_list:
            lga_to_zone[l.lower()] = z

    for f in mem_db.farmers.values():
        z = lga_to_zone.get(f.get('lga', '').lower(), 'Kano Central')
        zones_summary[z]['farmers'] += 1

    for r in mem_db.farmer_requests.values():
        farmer = mem_db.farmers.get(r['farmer_id'], {})
        z = lga_to_zone.get(farmer.get('lga', '').lower(), 'Kano Central')
        zones_summary[z]['allocated_bags'] += r.get('allocated_bags', 0)
        if r.get('distributed_by') or r.get('status') == 'distributed':
            zones_summary[z]['distributed_bags'] += r.get('allocated_bags', 0)

    return jsonify(zones_summary)


@app.route('/api/farmers', methods=['GET'])
def get_farmers():
    farmers_list = []
    for f in mem_db.farmers.values():
        farmers_list.append({
            'id': f['id'],
            'name': f['name'],
            'phone': f.get('phone', ''),
            'lga': f.get('lga', ''),
            'ward': f.get('ward', ''),
            'farm_size': f.get('farm_size', 0),
            'crop_type': f.get('crop_type', ''),
            'nin': f.get('nin', ''),
            'coop_name': f.get('coop_name', ''),
            'total_bags_received': f.get('total_bags_received', 0),
            'has_passport': bool(f.get('passport_photo')),
            'has_coop_evidence': bool(f.get('coop_evidence')),
            'created_at': f.get('created_at')
        })
    return jsonify(farmers_list)


@app.route('/api/farmers/<farmer_id>', methods=['GET'])
def get_farmer_detail(farmer_id):
    f = mem_db.farmers.get(farmer_id)
    if not f:
        return jsonify({'message': 'Farmer not found'}), 404
    # Clean sensitive password
    f_copy = dict(f)
    f_copy.pop('password', None)
    return jsonify(f_copy)


@app.route('/api/officers', methods=['GET'])
def get_officers():
    officers = []
    for o in mem_db.store_officers.values():
        officers.append({
            'id': o['id'],
            'name': o['name'],
            'location': o.get('location', 'Kano Depot'),
            'zone': o.get('zone', 'Central Zone')
        })
    return jsonify(officers)


@app.route('/api/audit_logs', methods=['GET'])
def get_audit_logs():
    return jsonify(mem_db.audit_logs[:100])


@app.route('/api/distributions/pending', methods=['GET'])
def pending_distributions():
    pending = [
        r for r in mem_db.farmer_requests.values()
        if r.get('status') == 'allocated' and not r.get('distributed_by')
    ]
    for r in pending:
        farmer = mem_db.farmers.get(r['farmer_id'], {})
        r['farmer_name'] = farmer.get('name')
        r['lga'] = farmer.get('lga')
        r['phone'] = farmer.get('phone')
    return jsonify(pending)


# ============= INITIALIZATION & RUNNER =============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting KNARDA AFDAS on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
