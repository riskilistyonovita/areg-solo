"""
init_folders.py - Script sekali jalan
Buat struktur folder di Google Drive untuk A-REG SOLO

Jalankan: python init_folders.py
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ============================================================
# CONFIG
# ============================================================

SERVICE_ACCOUNT_FILE = "service_account.json"

PARENT_FOLDER_ID   = "0AAh350WpbrR8Uk9PVA"
REGULASI_FOLDER_ID = "1V9XmxIo-kjiXGSYCE3Z58Vw0qijwKtq-"

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
]

FOLDER_STRUCTURE = {
    "PKS": {
        "Klinis": {},
        "Manajerial": {},
    },
    "e-Library": {
        "PNPK": {},
        "Clinical Pathway": {},
        "Lainnya": {},
    },
    "Dokumen Lainnya": {
        "Program Kerja": {},
        "SPK": {},
        "RKK": {},
        "Notulen MM": {},
    },
}

# ============================================================
# HELPERS
# ============================================================

def get_drive_service():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)


def search_folder(service, name, parent_id):
    q = (
        "name='" + name + "' and '" + parent_id + "' in parents "
        "and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    res = service.files().list(
        q=q, spaces='drive', fields='files(id, name)',
        supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    files = res.get('files', [])
    return files[0]['id'] if files else None


def create_folder(service, name, parent_id):
    meta = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id],
    }
    folder = service.files().create(
        body=meta, fields='id', supportsAllDrives=True
    ).execute()
    return folder.get('id')


def get_or_create(service, name, parent_id, indent=0):
    prefix = "  " * indent
    existing = search_folder(service, name, parent_id)
    if existing:
        print(prefix + "[SKIP] '" + name + "' sudah ada -> " + existing)
        return existing
    else:
        new_id = create_folder(service, name, parent_id)
        print(prefix + "[BUAT] '" + name + "' -> " + new_id)
        return new_id


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  INIT FOLDERS - A-REG SOLO")
    print("=" * 60)
    print("")

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print("ERROR: File '" + SERVICE_ACCOUNT_FILE + "' tidak ditemukan!")
        print("Pastikan script dijalankan dari folder root project.")
        sys.exit(1)

    print("Menghubungkan ke Google Drive...")
    try:
        service = get_drive_service()
        print("Koneksi berhasil!")
        print("")
    except Exception as e:
        print("ERROR koneksi: " + str(e))
        sys.exit(1)

    print("Parent folder : " + PARENT_FOLDER_ID)
    print("Regulasi      : " + REGULASI_FOLDER_ID + " (tidak diubah)")
    print("")

    folder_ids = {}

    for folder_name, subfolders in FOLDER_STRUCTURE.items():
        print("[" + folder_name + "]")
        parent_id = get_or_create(service, folder_name, PARENT_FOLDER_ID, indent=1)
        folder_ids[folder_name] = parent_id

        for sub_name in subfolders:
            get_or_create(service, sub_name, parent_id, indent=2)

        print("")

    print("=" * 60)
    print("  HASIL - Salin ke utils/google_drive_manager.py")
    print("=" * 60)
    print("")
    print("Tempel 3 baris ini di __init__ GoogleDriveManager:")
    print("")
    print('        self.PKS_FOLDER_ID         = "' + folder_ids.get("PKS", "") + '"')
    print('        self.ELIBRARY_FOLDER_ID    = "' + folder_ids.get("e-Library", "") + '"')
    print('        self.DOK_LAINNYA_FOLDER_ID = "' + folder_ids.get("Dokumen Lainnya", "") + '"')
    print("")
    print("Selesai!")


if __name__ == "__main__":
    main()