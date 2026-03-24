"""
Script sekali pakai: update SEMUA password di tb_users menjadi 'solo020'
Jalankan dari root folder areg-solo:
    python reset_passwords.py
"""

import gspread
from google.oauth2.service_account import Credentials
import time

SERVICE_ACCOUNT_FILE = "service_account.json"
SPREADSHEET_ID       = "18xXtfbCmNOSZdztvv7vsoJnqZdEpgDG4VqW-peBR8Dk"
NEW_PASSWORD         = "solo020"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def main():
    print("=== Reset Semua Password → solo020 ===\n")

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    gc    = gspread.authorize(creds)

    ss    = gc.open_by_key(SPREADSHEET_ID)
    sheet = ss.worksheet("tb_users")

    all_values = sheet.get_all_values()
    if not all_values or len(all_values) < 2:
        print("❌ Sheet tb_users kosong atau tidak ditemukan.")
        return

    headers = all_values[0]
    print(f"Headers: {headers}\n")

    if "user_id" not in headers or "password" not in headers:
        print("❌ Kolom 'user_id' atau 'password' tidak ditemukan!")
        return

    uid_col  = headers.index("user_id")
    pass_col = headers.index("password")   # 0-based index

    updates = []
    for i, row in enumerate(all_values[1:], start=2):  # row 2 dst (1-based di Sheets)
        uid = str(row[uid_col]).strip() if len(row) > uid_col else ""
        if not uid:
            continue
        old_pw = str(row[pass_col]).strip() if len(row) > pass_col else ""
        updates.append((i, pass_col + 1, uid, old_pw))  # pass_col+1 → 1-based kolom

    print(f"Ditemukan {len(updates)} user. Mulai update...\n")

    ok_count = 0
    for row_num, col_num, uid, old_pw in updates:
        try:
            sheet.update_cell(row_num, col_num, NEW_PASSWORD)
            print(f"  ✅  row {row_num:3d} | {uid:15s} | '{old_pw}' → '{NEW_PASSWORD}'")
            ok_count += 1
            time.sleep(1.2)   # hindari quota 429
        except Exception as e:
            print(f"  ❌  row {row_num:3d} | {uid:15s} | ERROR: {e}")
            time.sleep(3)

    print(f"\n=== Selesai: {ok_count}/{len(updates)} user diupdate ===")

if __name__ == "__main__":
    main()