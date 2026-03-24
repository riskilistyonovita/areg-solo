# A-REG SOLO
## Aplikasi Regulasi RS Hermina Solo

---

## 🚀 CARA SETUP DI KOMPUTER BARU

### LANGKAH 1 — Install Python
1. Download Python di: https://www.python.org/downloads/
2. Saat install, **CENTANG** kotak **"Add Python to PATH"**
3. Klik Install Now

### LANGKAH 2 — Install VS Code Extension
Buka VS Code → Extensions (Ctrl+Shift+X) → Install:
- **Python** (Microsoft)

### LANGKAH 3 — Siapkan File Assets
Letakkan file berikut di folder `assets/`:
- `logo.png` → Logo RS Hermina
- `hermina_solo.jpg` → Foto RS Hermina Solo

### LANGKAH 4 — Setup & Jalankan (Windows)
**Cara mudah:** Double-click file `SETUP_WINDOWS.bat`

**Cara manual (via VS Code Terminal):**
```bash
# Buka terminal di VS Code: Ctrl + `

# Install semua dependencies
pip install -r requirements.txt

# Jalankan aplikasi
streamlit run app.py
```

### LANGKAH 5 — Buka di Browser
Otomatis terbuka di: **http://localhost:8501**

---

## 📁 STRUKTUR FOLDER
```
areg-solo/
├── app.py                    ← File utama
├── style.css                 ← CSS styling
├── requirements.txt          ← Daftar library
├── service_account.json      ← Google credentials (RAHASIA!)
├── auth_config.yaml          ← Config auth
├── SETUP_WINDOWS.bat         ← Setup otomatis Windows
│
├── assets/
│   ├── logo.png              ← Logo RS Hermina
│   └── hermina_solo.jpg      ← Foto background login
│
├── utils/
│   ├── __init__.py
│   ├── google_drive_manager.py
│   ├── auth_manager.py
│   ├── folder_creator.py
│   ├── data_handler.py
│   └── file_manager.py
│
└── modules/
    ├── __init__.py
    ├── regulasi.py
    ├── bed_management.py
    ├── igd_rujukan.py
    └── master_data.py
```

---

## ⚠️ PENTING

| File | Keterangan |
|------|-----------|
| `service_account.json` | **JANGAN** di-share ke publik / upload ke GitHub |
| `assets/logo.png` | Harus ada, kalau tidak login page tidak sempurna |
| `assets/hermina_solo.jpg` | Harus ada untuk background login |

---

## 🔧 TROUBLESHOOTING

**Error: `streamlit` not found**
```bash
pip install streamlit
```

**Error: `ModuleNotFoundError`**
```bash
pip install -r requirements.txt
```

**Port sudah dipakai**
```bash
streamlit run app.py --server.port 8502
```

**Google Drive tidak bisa connect**
- Pastikan `service_account.json` ada di root folder
- Cek koneksi internet
- Pastikan spreadsheet sudah di-share ke service account email

---

## 📞 Kontak
IT Department RS Hermina Solo
© 2025 RS Hermina Solo