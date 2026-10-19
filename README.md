# Automated Fertilizer Distribution and Allocation System (AFDAS)
### Kano Agricultural Development Agency (KNARDA) &bull; Kano State Government of Nigeria

[![Vercel Deployment](https://img.shields.io/badge/Deploy-Vercel-black?style=for-the-badge&logo=vercel)](https://vercel.com)
[![Kano State](https://img.shields.io/badge/Kano_State-Agriculture-046A38?style=for-the-badge)](https://kanostate.gov.ng)
[![Blockchain Verified](https://img.shields.io/badge/Ledger-SHA--256_Blockchain-f59e0b?style=for-the-badge)](/api/blockchain)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)

---

## Executive Overview

The **Automated Fertilizer Distribution and Allocation System (AFDAS)** is a statewide digital infrastructure deployed for the **Kano Agricultural Development Agency (KNARDA)** under the supervision of the Kano State Ministry of Agriculture and Natural Resources.

AFDAS transforms how agricultural subsidies are managed across Kano State by replacing manual paper rosters with **cryptographic equity, algorithmic quota allocation, and tamper-proof distribution verification** covering all **44 Local Government Areas (LGAs)** of Kano State.

---

## Key Features & Functional Innovations

### 1. Algorithmic Quota Allocation Engine
- Eliminates political favoritism and manual discrepancies.
- Computes fair bag allocations based on:
  - Verified farm size (hectares) with smallholder baseline quotas (2 bags/hectare).
  - Crop priority multipliers (Irrigation Rice & Dry-Season Wheat receive 1.2x priority; Maize, Sorghum, and Vegetables receive tailored quotas).
  - Kano State Agricultural Cooperative Society verification incentive (+1 bag bonus).
  - Maximum allocation cap (12 bags) to ensure equitable reach for smallholders.

### 2. Multi-Mode QR & 6-Digit SMS Voucher Verification
- **High-Resolution QR Code**: Downloadable and displayable on smartphones.
- **6-Digit SMS OTP Voucher**: Rural smallholders with feature phones receive an instant 6-digit redemption token via SMS.
- **Store Officer Terminal**:
  - Live Webcam Scanner (using HTML5-QRCode directly in browser).
  - Image file dropzone for scanned or photo QR vouchers.
  - Manual 6-digit SMS OTP verification.
  - Anti-fraud double-redemption guard that cryptographically blocks bags from being claimed twice.

### 3. Kano State 44 LGAs & Zonal Depots Coverage
- Full spatial coverage partitioned into Kano's 3 senatorial agricultural belts:
  - **Kano Central Zone** (Dawanau Grain Depot & Central Hub): Dala, Fagge, Gwale, Kano Municipal, Kumbotso, Nassarawa, Tarauni, Ungogo.
  - **Kano North Zone** (Bichi Agro-Distribution Depot): Bagwai, Bichi, Danbatta, Dawakin Tofa, Gwarzo, Kabo, Kunchi, Makoda, Minjibir, Rimin Gado, Shanono, Tofa, Tsanyawa.
  - **Kano South Zone** (Rano & Kura Irrigation Depots): Ajingi, Albasu, Bebeji, Bunkure, Doguwa, Garko, Garun Mallam, Gaya, Karaye, Kibiya, Kiru, Kura, Madobi, Rano, Rogo, Sumaila, Takai, Tudun Wada, Warawa, Wudil.

### 4. Immutable SHA-256 Blockchain Ledger
- Every allocation run and physical bag dispensing event is sealed in a cryptographic block.
- Links preceding block hashes with Merkle-structured transaction payloads.
- Includes a live **Blockchain Explorer** with an automated **"Verify Chain Integrity"** diagnostic that detects data tampering in real time.

### 5. Official Printable KNARDA Collection Slips
- Generates official government collection receipts (`/api/acknowledgement_slip/<id>`) formatted with Kano State crest, farmer passport details, NIN, allocated quota, pickup depot, and security stamps.

### 6. Modern Kano Emerald & Harvest Gold UI
- Modern, clean design using **Tailwind CSS 3**, **Plus Jakarta Sans**, **Outfit**, and **FontAwesome 6**.
- Responsive sidebar navigation, dark/light ambient contrast, Chart.js zonal telemetry, and celebratory confetti effects.

---

## Hosting on Vercel

AFDAS is engineered to deploy to **Vercel** as a Python Serverless Application with zero configuration.

### Deployment Steps:

1. **Push to GitHub**:
   Ensure all files are committed to your GitHub repository (`AL-AHOTANEE/AFDAS`).

2. **Import into Vercel**:
   - Go to [Vercel Dashboard](https://vercel.com/new).
   - Click **Add New &rarr; Project** and import `AL-AHOTANEE/AFDAS`.
   - Vercel automatically detects `vercel.json` and configures the `@vercel/python` builder.

3. **Environment Variables (Optional)**:
   | Variable | Required | Description |
   |---|---|---|
   | `DATABASE_URL` | Optional | External PostgreSQL connection URL (e.g. Neon, Supabase, Vercel Postgres, Render). If omitted, AFDAS runs in resilient zero-crash fallback mode with full pre-seeded data. |
   | `SECRET_KEY` | Optional | Random string for cryptographic security and session signing. |

4. **Click Deploy**:
   Vercel will build and serve your application with a global edge URL (e.g., `https://afdas-kano.vercel.app`).

---

## Local Development

```bash
# 1. Clone repository
git clone https://github.com/AL-AHOTANEE/AFDAS.git
cd AFDAS

# 2. Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start local server
python app.py
# Open http://localhost:5000 in your browser
```

---

## Pre-Seeded Test Credentials

| Role | User ID | Password | Context |
|---|---|---|---|
| **Administrator** | `A001` | `Admin1` | KNARDA Director General / Zonal Director |
| **Store Officer** | `S001` | `Officer1` | Dawanau Central Grain Depot, Kano Central |
| **Store Officer** | `S002` | `Officer1` | Bichi Agro-Distribution Depot, Kano North |
| **Store Officer** | `S003` | `Officer1` | Rano Zonal Seed & Input Store, Kano South |
| **Farmer** | `F001` | `Farmer1` | Alhaji Musa Danbatta (Danbatta LGA - 4.5 ha) |
| **Farmer** | `F002` | `Farmer1` | Balaraba Sani Kura (Kura LGA - 3.2 ha) |
| **Farmer** | `F003` | `Farmer1` | Malam Garba Bichi (Bichi LGA - 2.0 ha) |

*(You can also register a new farmer self-service directly from the portal login screen!)*

---

## API Endpoints Reference

### Public & Authentication
- `GET /` &bull; Public KNARDA AFDAS Landing Page
- `GET /app` &bull; Single-page unified Dashboard Application
- `GET /health` &bull; Serverless health telemetry & persistence status
- `POST /api/login` &bull; Authenticate Farmer, Officer, or Administrator
- `POST /api/register/farmer` &bull; Enroll new Kano smallholder farmer
- `POST /api/register/officer` &bull; Register store officer

### Algorithmic Allocation & Seasons
- `GET /api/seasons` &bull; List all distribution subsidy seasons
- `GET /api/seasons/active` &bull; List current active season programmes
- `POST /api/seasons` &bull; Launch a new distribution programme (Admin)
- `POST /api/allocate/<season_id>` &bull; Execute statewide algorithmic allocation engine

### Farmer Requests & Voucher Verification
- `POST /api/requests` &bull; Farmer submits subsidy application
- `GET /api/requests/farmer/<id>` &bull; Fetch farmer's allocation history & QR vouchers
- `POST /api/verify_qr` &bull; Verify QR Code payload, hash, or 6-digit SMS token
- `POST /api/distribute` &bull; Store officer dispenses bags & records block to chain
- `POST /api/acknowledge` &bull; Farmer confirms physical collection
- `GET /api/acknowledgement_slip/<request_id>` &bull; Printable official KNARDA collection receipt

### Blockchain Ledger
- `GET /api/blockchain` &bull; Query blocks in the distribution chain
- `GET /api/blockchain/verify` &bull; Recalculate SHA-256 hashes from genesis to head

### Spatial Analytics & LGAs
- `GET /api/locations/lga` &bull; Directory of all 44 Kano LGAs
- `GET /api/stats/admin` &bull; Executive telemetry (farmers, bags, fulfillment rate)
- `GET /api/stats/kano-zones` &bull; Breakdown across Kano Central, North, and South

---

## License & Sovereignty

&copy; 2026 Kano Agricultural Development Agency (KNARDA), Kano State Ministry of Agriculture and Natural Resources, Government of Kano State, Nigeria. All Rights Reserved.
