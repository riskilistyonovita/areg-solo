# utils/google_drive_manager.py - FIXED CONNECTION HANDLING
"""
Google Drive & Sheets Manager untuk AREG SOLO
Handles 2 spreadsheets dengan error handling yang lebih baik
"""

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import streamlit as st
from datetime import datetime
import io
import os
import pandas as pd
import time


class GoogleDriveManager:
    """Manager untuk upload file ke Google Drive dan akses Google Sheets"""
    
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        # ============================================================
        # FOLDER STRUCTURE
        # 📁 AREG SOLO          (PARENT_FOLDER_ID)
        #   ├── 📁 Regulasi_RS_...     (DRIVE_FOLDER_ID)
        #   ├── 📁 Perijinan & PKS     (PKS_FOLDER_ID)
        #   ├── 📁 e-Library           (ELIBRARY_FOLDER_ID)
        #   └── 📁 Dokumen Lainnya     (DOK_LAINNYA_FOLDER_ID)
        # ============================================================

        # Root / parent semua folder
        self.PARENT_FOLDER_ID = "0AAh350WpbrR8Uk9PVA"

        # Folder regulasi (existing)
        self.DRIVE_FOLDER_ID = "1V9XmxIo-kjiXGSYCE3Z58Vw0qijwKtq-"

        # Folder sejajar regulasi
        self.PKS_FOLDER_ID         = "1QWAmUhCuh1BItXcDqWhHfdSzbKpS0Q5l"
        self.ELIBRARY_FOLDER_ID    = "1EjrnAUNnsahUw2sK9XSYzupYryBrW19f"
        self.DOK_LAINNYA_FOLDER_ID = "1gCXlEBrW0dM2MnRp1ZJAR4rn5am9Qf5-"

        # Sub-folder PKS / Perijinan & PKS
        self.PKS_PERIJINAN_FOLDER_ID   = "1QvbXUNI3nYSz52-A90ihlPysuRhDjVsl"  # ← isi setelah folder dibuat di Drive
        self.PKS_KLINIS_FOLDER_ID      = "1zdUdZlcigcZvzVB7yPf7J_T5bL8TmvQ7"
        self.PKS_MANAJERIAL_FOLDER_ID  = "1cNGfghyUxvChZ8gGlSFaEw8HvnkD3xwm"

        # Sub-folder e-Library
        self.LIB_PNPK_FOLDER_ID           = "1VEABDv4WJFtpBMhuueQbTxmXwtlOoOEb"
        self.LIB_CLINICAL_FOLDER_ID        = "1RB--Pw_UIdSdaJ2mfR06KYNa8M3GW24O"
        self.LIB_LAINNYA_FOLDER_ID         = "1CafvW5p6ejDcpRLVHnnPVccAYPT429OR"

        # Sub-folder Dokumen Lainnya
        self.DOK_NOTULEN_FOLDER_ID     = "1_y1CC99iCP105RQxtqzJI-uOLqk6Jb0D"
        self.DOK_PROGJA_FOLDER_ID      = "1gpxA_BGpZPzHIr02oF7Q9lHcUn-r5sev"
        self.DOK_RKK_FOLDER_ID         = "13k0tLCJ_U95XX22uld2qVFFX-srwR4HP"
        self.DOK_SPK_FOLDER_ID         = "1MH2li3msskki_DGGBl9casgazzUtrbXQ"
        
        # Spreadsheet IDs
        self.SPREADSHEET_REGULASI_ID = "14oaSruVmVMUnQXyAeB4IF9prhpHfLDRc7UOnzBR8D1Q"
        self.SPREADSHEET_MANAGEMEN_ID = "18xXtfbCmNOSZdztvv7vsoJnqZdEpgDG4VqW-peBR8Dk"
        
        # Lazy loading untuk spreadsheets
        self._spreadsheet_regulasi = None
        self._spreadsheet_managemen = None
        
        # Retry configuration
        self.MAX_RETRIES = 3
        self.RETRY_DELAY = 2  # seconds
        
        # Initialize
        self.is_ready = False
        self._initialize()
    
    def _initialize(self):
        """Initialize dengan retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                if "gcp_service_account" in st.secrets:
                    _sec = st.secrets["gcp_service_account"]
                    _info = {
                        "type": _sec["type"],
                        "project_id": _sec["project_id"],
                        "private_key_id": _sec["private_key_id"],
                        "private_key": _sec["private_key"],
                        "client_email": _sec["client_email"],
                        "client_id": _sec["client_id"],
                        "auth_uri": _sec["auth_uri"],
                        "token_uri": _sec["token_uri"],
                        "auth_provider_x509_cert_url": _sec["auth_provider_x509_cert_url"],
                        "client_x509_cert_url": _sec["client_x509_cert_url"],
                    }
                    self.creds = Credentials.from_service_account_info(_info, scopes=self.SCOPES)
                else:
                    service_account_file = 'service_account.json'
                    self.creds = Credentials.from_service_account_file(
                        service_account_file,
                        scopes=self.SCOPES
                    )

                self.gc = gspread.authorize(self.creds)
                self.drive_service = build('drive', 'v3', credentials=self.creds)
                self._test_connection()
                self.is_ready = True
                return

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    st.warning(f"\u26a0\ufe0f Connection attempt {attempt + 1} failed, retrying...")
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"\u274c Failed to initialize after {self.MAX_RETRIES} attempts")
                    st.error(f"Error: {str(e)}")
                    self.creds = None
                    self.gc = None
                    self.drive_service = None

    def _test_connection(self):
        """Test koneksi dengan retry"""
        for attempt in range(self.MAX_RETRIES):
            try:
                # Test Drive access
                self.drive_service.files().get(
                    fileId=self.DRIVE_FOLDER_ID,
                    fields='id, name',
                    supportsAllDrives=True
                ).execute()
                
                # Test Sheets access - Regulasi
                self.gc.open_by_key(self.SPREADSHEET_REGULASI_ID)
                
                # Test Sheets access - Managemen
                self.gc.open_by_key(self.SPREADSHEET_MANAGEMEN_ID)
                
                return  # Success
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise Exception(f"Connection test failed: {str(e)}")
    
    def is_initialized(self):
        """Check if manager is properly initialized"""
        return self.is_ready and all([self.creds, self.gc, self.drive_service])
    
    # ========== LAZY LOADING SPREADSHEETS ==========
    
    @property
    def spreadsheet_regulasi(self):
        """Lazy load spreadsheet Regulasi dengan retry"""
        if self._spreadsheet_regulasi is None:
            for attempt in range(self.MAX_RETRIES):
                try:
                    self._spreadsheet_regulasi = self.gc.open_by_key(self.SPREADSHEET_REGULASI_ID)
                    return self._spreadsheet_regulasi
                except Exception as e:
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY)
                    else:
                        st.error(f"âŒ Cannot access Spreadsheet Regulasi: {str(e)}")
                        return None
        return self._spreadsheet_regulasi
    
    @property
    def spreadsheet_managemen(self):
        """Lazy load spreadsheet Managemen dengan retry"""
        if self._spreadsheet_managemen is None:
            for attempt in range(self.MAX_RETRIES):
                try:
                    self._spreadsheet_managemen = self.gc.open_by_key(self.SPREADSHEET_MANAGEMEN_ID)
                    return self._spreadsheet_managemen
                except Exception as e:
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY)
                    else:
                        st.error(f"âŒ Cannot access Spreadsheet Managemen: {str(e)}")
                        return None
        return self._spreadsheet_managemen
    
    # ========== REGULASI FUNCTIONS ==========
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_all_documents(_self):
        """Get all documents from rekap_database dengan error handling"""
        if not _self.is_initialized() or _self.spreadsheet_regulasi is None:
            return []
        
        for attempt in range(_self.MAX_RETRIES):
            try:
                sheet = _self.spreadsheet_regulasi.worksheet('rekap_database')
                all_values = sheet.get_all_values()
                
                if not all_values or len(all_values) < 2:
                    return []
                
                headers = all_values[0]
                data = []
                
                for row in all_values[1:]:
                    if len(row) < len(headers):
                        row.extend([''] * (len(headers) - len(row)))
                    elif len(row) > len(headers):
                        row = row[:len(headers)]
                    
                    row_dict = dict(zip(headers, row))
                    data.append(row_dict)
                
                return data
                
            except gspread.exceptions.WorksheetNotFound:
                st.warning("âš ï¸ Worksheet 'rekap_database' tidak ditemukan")
                return []
            except Exception as e:
                if attempt < _self.MAX_RETRIES - 1:
                    time.sleep(_self.RETRY_DELAY)
                else:
                    st.warning(f"âš ï¸ Error getting documents: {str(e)}")
                    return []
    
    @st.cache_data(ttl=7200, show_spinner=False)
    def get_master_data(_self, worksheet_name):
        """Get master data dengan error handling"""
        if not _self.is_initialized() or _self.spreadsheet_regulasi is None:
            return pd.DataFrame()
        
        for attempt in range(_self.MAX_RETRIES):
            try:
                sheet = _self.spreadsheet_regulasi.worksheet(worksheet_name)
                data = sheet.get_all_records()
                return pd.DataFrame(data)
            except gspread.exceptions.WorksheetNotFound:
                st.warning(f"âš ï¸ Worksheet '{worksheet_name}' tidak ditemukan")
                return pd.DataFrame()
            except Exception as e:
                if attempt < _self.MAX_RETRIES - 1:
                    time.sleep(_self.RETRY_DELAY)
                else:
                    st.warning(f"âš ï¸ Error getting master data from '{worksheet_name}': {str(e)}")
                    return pd.DataFrame()
    
    def add_master_data(self, worksheet_name, data_dict):
        """Add data to master worksheet dengan retry"""
        if not self.is_initialized() or self.spreadsheet_regulasi is None:
            return False
        
        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_regulasi.worksheet(worksheet_name)
                
                # Get headers
                all_values = sheet.get_all_values()
                if not all_values:
                    return False
                
                headers = all_values[0]
                
                # Prepare row
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                row = []
                
                for header in headers:
                    if header in data_dict:
                        row.append(str(data_dict[header]))
                    elif header == 'created_at':
                        row.append(now)
                    else:
                        row.append('')
                
                sheet.append_row(row, value_input_option='USER_ENTERED')
                
                # Clear cache
                st.cache_data.clear()
                
                return True
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"âŒ Error adding master data: {str(e)}")
                    return False
    
    def log_to_sheets(self, data):
        """Log document to sheets dengan retry"""
        if not self.is_initialized() or self.spreadsheet_regulasi is None:
            return False
        
        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_regulasi.worksheet('rekap_database')
                
                # Get headers
                all_values = sheet.get_all_values()
                if not all_values:
                    return False
                
                headers = all_values[0]
                
                # Prepare row
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                next_id = len(all_values)
                
                row = []
                for header in headers:
                    if header == 'dokumen_id':
                        row.append(str(next_id))
                    elif header == 'created_at':
                        row.append(now)
                    elif header in data:
                        row.append(str(data[header]))
                    else:
                        row.append('')
                
                sheet.append_row(row, value_input_option='USER_ENTERED')
                
                # Clear cache
                st.cache_data.clear()
                
                return True
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"âŒ Error logging to sheets: {str(e)}")
                    return False
    
    def update_rekap_database(self, dokumen_id, updates: dict):
        """
        Update baris di rekap_database berdasarkan dokumen_id.
        updates: dict {nama_kolom: nilai_baru}
        Returns True jika berhasil.
        """
        if not self.is_initialized() or self.spreadsheet_regulasi is None:
            return False

        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_regulasi.worksheet('rekap_database')
                all_values = sheet.get_all_values()

                if not all_values or len(all_values) < 2:
                    return False

                headers = all_values[0]

                # Cari baris yang dokumen_id-nya cocok
                row_index = None
                for i, row in enumerate(all_values[1:], start=2):  # baris 2 = index Sheets ke-2
                    if len(row) > 0 and str(row[0]).strip() == str(dokumen_id).strip():
                        row_index = i
                        break
                    # Fallback: cari di kolom manapun yang bernama dokumen_id
                    if 'dokumen_id' in headers:
                        col_idx = headers.index('dokumen_id')
                        if col_idx < len(row) and str(row[col_idx]).strip() == str(dokumen_id).strip():
                            row_index = i
                            break

                if row_index is None:
                    st.error(f"Dokumen ID '{dokumen_id}' tidak ditemukan di database.")
                    return False

                # Update hanya kolom yang ada di dict updates
                for col_name, new_val in updates.items():
                    if col_name in headers:
                        col_index = headers.index(col_name) + 1  # Sheets pakai 1-based index
                        sheet.update_cell(row_index, col_index, str(new_val))

                time.sleep(1)
                st.cache_data.clear()
                return True

            except Exception as e:
                err_str = str(e)
                if '429' in err_str or 'Quota exceeded' in err_str or 'quota' in err_str.lower():
                    wait = (attempt + 1) * 15
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(wait)
                    else:
                        st.error("Gagal update: quota Google Sheets API penuh. Coba lagi sebentar.")
                        return False
                elif attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"Error update_rekap_database: {str(e)}")
                    return False

    # ========== MANAGEMEN FUNCTIONS ==========
    
    @st.cache_data(ttl=7200, show_spinner=False)
    def update_user_password(self, user_id, new_password):
        """
        Update password user di tb_users berdasarkan user_id.
        Returns True jika berhasil.
        """
        if not self.is_initialized() or self.spreadsheet_managemen is None:
            return False
        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_managemen.worksheet('tb_users')
                all_values = sheet.get_all_values()
                if not all_values or len(all_values) < 2:
                    return False
                headers = all_values[0]
                if 'user_id' not in headers or 'password' not in headers:
                    return False
                uid_col  = headers.index('user_id')
                pass_col = headers.index('password')
                for i, row in enumerate(all_values[1:], start=2):
                    if len(row) > uid_col and str(row[uid_col]).strip().upper() == str(user_id).strip().upper():
                        sheet.update_cell(i, pass_col + 1, new_password)
                        time.sleep(1)
                        st.cache_data.clear()
                        return True
                return False  # user_id tidak ditemukan
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    return False
        return False

    def get_users(_self):
        """Get users dengan error handling"""
        if not _self.is_initialized() or _self.spreadsheet_managemen is None:
            return []
        
        for attempt in range(_self.MAX_RETRIES):
            try:
                sheet = _self.spreadsheet_managemen.worksheet('tb_users')
                all_values = sheet.get_all_values()
                
                if not all_values or len(all_values) < 2:
                    return []
                
                headers = all_values[0]
                
                # Fix duplicate headers
                seen = {}
                fixed_headers = []
                for h in headers:
                    if h in seen:
                        seen[h] += 1
                        fixed_headers.append(f"{h}_{seen[h]}")
                    else:
                        seen[h] = 0
                        fixed_headers.append(h)
                
                # Convert to list of dicts
                data = []
                for row in all_values[1:]:
                    if len(row) < len(fixed_headers):
                        row.extend([''] * (len(fixed_headers) - len(row)))
                    elif len(row) > len(fixed_headers):
                        row = row[:len(fixed_headers)]
                    
                    row_dict = dict(zip(fixed_headers, row))
                    data.append(row_dict)
                
                return data
                
            except Exception as e:
                if attempt < _self.MAX_RETRIES - 1:
                    time.sleep(_self.RETRY_DELAY)
                else:
                    st.error(f"âŒ Error getting users: {str(e)}")
                    return []
    
    @st.cache_data(ttl=7200, show_spinner=False)
    def get_roles(_self):
        """Get daftar role dari tb_roles di spreadsheet Managemen."""
        if not _self.is_initialized() or _self.spreadsheet_managemen is None:
            return []
        for attempt in range(_self.MAX_RETRIES):
            try:
                sheet = _self.spreadsheet_managemen.worksheet('tb_roles')
                return sheet.get_all_records()
            except Exception as e:
                if attempt < _self.MAX_RETRIES - 1:
                    time.sleep(_self.RETRY_DELAY)
                else:
                    st.warning(f"⚠️ Error getting tb_roles: {str(e)}")
                    return []

    def add_user(self, user_data):
        """
        Tambah user baru ke tb_users.
        user_data: dict dengan key sesuai header tb_users.
        Returns True jika berhasil.
        """
        if not self.is_initialized() or self.spreadsheet_managemen is None:
            return False
        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_managemen.worksheet('tb_users')
                all_values = sheet.get_all_values()
                if not all_values:
                    return False
                headers = all_values[0]
                from datetime import datetime as _dt
                now = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
                row = []
                for h in headers:
                    if h in user_data:
                        row.append(str(user_data[h]))
                    elif h == 'created_at':
                        row.append(now)
                    elif h == 'status':
                        row.append('aktif')
                    else:
                        row.append('')
                sheet.append_row(row, value_input_option='USER_ENTERED')
                time.sleep(1)
                st.cache_data.clear()
                return True
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"❌ Error adding user: {str(e)}")
                    return False
        return False

    def update_user_field(self, user_id, field, value):
        """
        Update satu field user di tb_users berdasarkan user_id.
        Returns True jika berhasil.
        """
        if not self.is_initialized() or self.spreadsheet_managemen is None:
            return False
        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_managemen.worksheet('tb_users')
                all_values = sheet.get_all_values()
                if not all_values or len(all_values) < 2:
                    return False
                headers = all_values[0]
                if 'user_id' not in headers or field not in headers:
                    return False
                uid_col   = headers.index('user_id')
                field_col = headers.index(field)
                for i, row in enumerate(all_values[1:], start=2):
                    if len(row) > uid_col and str(row[uid_col]).strip().upper() == str(user_id).strip().upper():
                        sheet.update_cell(i, field_col + 1, value)
                        time.sleep(1)
                        st.cache_data.clear()
                        return True
                return False
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"❌ Error updating user field: {str(e)}")
                    return False
        return False

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_ruang_rawat(_self):
        """Get ruang rawat"""
        return _self._get_data_with_retry('tb_ruang_rawat')
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_bed(_self):
        """Get bed"""
        return _self._get_data_with_retry('tb_bed')
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_pasien(_self):
        """Get pasien"""
        return _self._get_data_with_retry('tb_pasien')
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_igd(_self):
        """Get IGD"""
        return _self._get_data_with_retry('tb_igd')
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_rujukan(_self):
        """Get rujukan"""
        return _self._get_data_with_retry('tb_rujukan')
    
    @st.cache_data(ttl=7200, show_spinner=False)
    def get_dpjp(_self):
        """Get DPJP"""
        return _self._get_data_with_retry('tb_dpjp')
    
    @st.cache_data(ttl=7200, show_spinner=False)
    def get_jaminan(_self):
        """Get jaminan"""
        return _self._get_data_with_retry('tb_jaminan')
    
    def _get_data_with_retry(self, worksheet_name):
        """Helper function to get data with retry"""
        if not self.is_initialized() or self.spreadsheet_managemen is None:
            return []
        
        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_managemen.worksheet(worksheet_name)
                return sheet.get_all_records()
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.warning(f"âš ï¸ Error getting {worksheet_name}: {str(e)}")
                    return []
    
    # ========== DRIVE FUNCTIONS ==========
    
    def create_folder(self, folder_name, parent_folder_id=None):
        """Create folder di Google Drive dengan retry"""
        if not self.is_initialized():
            return None
        
        if parent_folder_id is None:
            parent_folder_id = self.DRIVE_FOLDER_ID
        
        for attempt in range(self.MAX_RETRIES):
            try:
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_folder_id]
                }
                
                folder = self.drive_service.files().create(
                    body=file_metadata,
                    fields='id',
                    supportsAllDrives=True
                ).execute()
                
                return folder.get('id')
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"âŒ Error creating folder: {str(e)}")
                    return None
    
    def search_folder(self, folder_name, parent_folder_id):
        """Search folder by name dengan retry"""
        if not self.is_initialized():
            return None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                
                results = self.drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)',
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    corpora='allDrives',
                ).execute()
                
                files = results.get('files', [])
                return files[0]['id'] if files else None
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    return None
    
    def create_folder_for_master_data(self, folder_name, parent_folder_id=None):
        """Create or get folder untuk master data"""
        if parent_folder_id is None:
            parent_folder_id = self.DRIVE_FOLDER_ID
        
        # Check if exists
        existing_id = self.search_folder(folder_name, parent_folder_id)
        if existing_id:
            return existing_id
        
        # Create new
        return self.create_folder(folder_name, parent_folder_id)

    def get_or_create_sibling_folder(self, folder_name):
        """
        Get atau buat folder sejajar dengan Regulasi_RS_Hermina_Solo.
        Semua folder (PKS, e-Library, Dokumen Lainnya) dibuat di PARENT_FOLDER_ID.
        
        Returns: folder_id
        """
        existing = self.search_folder(folder_name, self.PARENT_FOLDER_ID)
        if existing:
            return existing
        return self.create_folder(folder_name, self.PARENT_FOLDER_ID)

    def get_or_create_nonaktif_folder(self):
        """
        Get atau buat folder 'Dokumen_Nonaktif' di dalam DRIVE_FOLDER_ID (Regulasi).
        Dokumen yang dinonaktifkan dipindahkan ke sini.
        Returns: folder_id atau None
        """
        if not self.is_initialized():
            return None
        folder_name = "Dokumen_Nonaktif"
        existing = self.search_folder(folder_name, self.DRIVE_FOLDER_ID)
        if existing:
            return existing
        return self.create_folder(folder_name, self.DRIVE_FOLDER_ID)

    def get_menu_folder_id(self, menu: str) -> str:
        """
        Return folder_id untuk menu tertentu.
        Kalau belum ada, auto-create di PARENT_FOLDER_ID.
        
        menu: 'regulasi' | 'pks' | 'elibrary' | 'dokumen_lainnya'
        """
        menu_map = {
            'regulasi':       (self.DRIVE_FOLDER_ID,        'Regulasi_RS_Hermina_Solo'),
            'pks':            (self.PKS_FOLDER_ID,          'Perijinan & PKS'),
            'elibrary':       (self.ELIBRARY_FOLDER_ID,     'e-Library'),
            'dokumen_lainnya':(self.DOK_LAINNYA_FOLDER_ID,  'Dokumen Lainnya'),
        }
        folder_id, folder_name = menu_map.get(menu.lower(), (self.DRIVE_FOLDER_ID, ''))
        
        if folder_id:
            return folder_id
        
        # Auto-create jika belum ada
        return self.get_or_create_sibling_folder(folder_name)


    # ========== UPLOAD FILE TO DRIVE ==========

    def upload_file_to_drive(self, file_content, file_name, mime_type, folder_id=None):
        """Upload file bytes ke Google Drive. Returns {'id':..,'link':..} atau None."""
        if not self.is_initialized():
            return None
        if folder_id is None:
            folder_id = self.DRIVE_FOLDER_ID
        for attempt in range(self.MAX_RETRIES):
            try:
                media = MediaIoBaseUpload(
                    io.BytesIO(file_content),
                    mimetype=mime_type,
                    resumable=True
                )
                uploaded = self.drive_service.files().create(
                    body={'name': file_name, 'parents': [folder_id]},
                    media_body=media,
                    fields='id, webViewLink',
                    supportsAllDrives=True
                ).execute()
                return {'id': uploaded.get('id', ''), 'link': uploaded.get('webViewLink', '')}
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"❌ Error upload file: {str(e)}")
                    return None

    def upload_docx_as_gdoc(self, file_content, file_name, folder_id=None):
        """
        Upload .docx dan langsung convert ke Google Docs format.
        Returns {'id': gdoc_id, 'link': webViewLink} atau None.
        """
        if not self.is_initialized():
            return None
        if folder_id is None:
            folder_id = self.PARENT_FOLDER_ID
        for attempt in range(self.MAX_RETRIES):
            try:
                media = MediaIoBaseUpload(
                    io.BytesIO(file_content),
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    resumable=True
                )
                gdoc = self.drive_service.files().create(
                    body={
                        'name': file_name,
                        'mimeType': 'application/vnd.google-apps.document',
                        'parents': [folder_id]
                    },
                    media_body=media,
                    fields='id, webViewLink',
                    supportsAllDrives=True
                ).execute()
                return {'id': gdoc.get('id', ''), 'link': gdoc.get('webViewLink', '')}
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"❌ Error upload sebagai Google Docs: {str(e)}")
                    return None

    def export_gdoc_as_pdf(self, gdoc_id):
        """Export Google Docs ke PDF bytes. Returns bytes atau None."""
        if not self.is_initialized():
            return None
        # Coba via Drive API dulu
        try:
            time.sleep(1)
            result = self.drive_service.files().export(
                fileId=gdoc_id,
                mimeType='application/pdf'
            ).execute()
            if result:
                return result
        except Exception as e1:
            pass  # fallback ke requests

        # Fallback: download via URL dengan requests (bypass SSL issue)
        try:
            import requests
            from google.auth.transport.requests import Request as GoogleRequest
            # Refresh token
            creds = self.creds
            if creds.expired:
                creds.refresh(GoogleRequest())
            token = creds.token
            url   = f"https://docs.google.com/feeds/download/documents/export/Export?id={gdoc_id}&exportFormat=pdf"
            resp  = requests.get(url,
                                  headers={"Authorization": f"Bearer {token}"},
                                  verify=False,  # bypass SSL proxy
                                  timeout=60)
            if resp.status_code == 200:
                return resp.content
            # Coba URL alternatif
            url2 = f"https://drive.google.com/uc?export=download&id={gdoc_id}"
            resp2 = requests.get(url2,
                                  headers={"Authorization": f"Bearer {token}"},
                                  verify=False,
                                  timeout=60)
            if resp2.status_code == 200:
                return resp2.content
        except Exception as e2:
            st.error(f"❌ Gagal export PDF: {str(e2)}")
        return None

    def download_file_from_drive(self, file_id):
        """Download file bytes dari Google Drive. Returns bytes atau None."""
        if not self.is_initialized():
            return None
        try:
            from googleapiclient.http import MediaIoBaseDownload
            request = self.drive_service.files().get_media(
                fileId=file_id, supportsAllDrives=True
            )
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buf.getvalue()
        except Exception as e:
            st.error(f"❌ Error download file: {str(e)}")
            return None

    def get_or_create_ratifikasi_folder(self):
        """Get atau create folder Ratifikasi_Draft. Hapus duplikat jika ada."""
        if not self.is_initialized():
            return None
        try:
            # Cari SEMUA folder dengan nama ini di parent
            query = (f"name='Ratifikasi_Draft' and '{self.PARENT_FOLDER_ID}' in parents "
                     f"and mimeType='application/vnd.google-apps.folder' and trashed=false")
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            folders = results.get('files', [])

            if len(folders) == 1:
                return folders[0]['id']

            if len(folders) > 1:
                # Hapus duplikat, pakai yang pertama
                keep_id = folders[0]['id']
                for f in folders[1:]:
                    try:
                        self.drive_service.files().delete(
                            fileId=f['id'], supportsAllDrives=True
                        ).execute()
                    except Exception:
                        pass
                return keep_id

            # Belum ada — buat baru
            meta = {
                'name': 'Ratifikasi_Draft',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.PARENT_FOLDER_ID]
            }
            folder = self.drive_service.files().create(
                body=meta, fields='id', supportsAllDrives=True
            ).execute()
            return folder.get('id')

        except Exception as e:
            st.error(f"❌ Gagal membuat folder Ratifikasi_Draft: {e}")
            return None

    def share_gdrive_file_reader(self, file_id, email):
        """Beri akses reader ke email. Returns permission_id atau None."""
        if not self.is_initialized():
            return None
        try:
            perm = self.drive_service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'user', 'emailAddress': email},
                sendNotificationEmail=True,
                supportsAllDrives=True
            ).execute()
            return perm.get('id')
        except Exception as e:
            st.warning(f"⚠️ Gagal share ke {email}: {str(e)}")
            return None

    def update_file_in_drive(self, file_id, new_content, mime_type='application/pdf'):
        """
        Update konten file yang sudah ada di Drive (file ID tetap sama).
        Returns True jika berhasil.
        """
        if not self.is_initialized():
            return False
        for attempt in range(self.MAX_RETRIES):
            try:
                media = MediaIoBaseUpload(
                    io.BytesIO(new_content),
                    mimetype=mime_type,
                    resumable=True
                )
                self.drive_service.files().update(
                    fileId=file_id,
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                return True
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"❌ Error update file: {str(e)}")
                    return False

    def move_file_to_folder(self, file_id, new_folder_id):
        """Pindahkan file ke folder baru. Returns True jika berhasil."""
        if not self.is_initialized():
            return False
        try:
            file_info = self.drive_service.files().get(
                fileId=file_id, fields='parents', supportsAllDrives=True
            ).execute()
            current_parents = ','.join(file_info.get('parents', []))
            self.drive_service.files().update(
                fileId=file_id,
                addParents=new_folder_id,
                removeParents=current_parents,
                fields='id, parents',
                supportsAllDrives=True
            ).execute()
            return True
        except Exception as e:
            st.error(f"❌ Error memindahkan file: {str(e)}")
            return False

    def list_subfolders(self, parent_folder_id):
        """List semua subfolder. Returns list of {'id':..,'name':..}"""
        if not self.is_initialized():
            return []
        try:
            result = self.drive_service.files().list(
                q=(f"'{parent_folder_id}' in parents "
                   f"and mimeType='application/vnd.google-apps.folder' "
                   f"and trashed=false"),
                fields='files(id, name)',
                orderBy='name',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora='allDrives'
            ).execute()
            return result.get('files', [])
        except Exception as e:
            st.error(f"❌ Error list subfolders: {str(e)}")
            return []

    # ========== RATIFIKASI ==========

    @st.cache_data(ttl=1800, show_spinner=False)
    def get_ratifikasi_list(_self):
        """Get semua record dari tb_ratifikasi."""
        if not _self.is_initialized() or _self.spreadsheet_regulasi is None:
            return []
        try:
            sheet = _self.spreadsheet_regulasi.worksheet('tb_ratifikasi')
            return sheet.get_all_records()
        except gspread.exceptions.WorksheetNotFound:
            return []
        except Exception:
            return []

    def add_ratifikasi_record(self, data_dict):
        """Tambah baris baru ke tb_ratifikasi."""
        if not self.is_initialized() or self.spreadsheet_regulasi is None:
            return False
        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_regulasi.worksheet('tb_ratifikasi')
                all_values = sheet.get_all_values()
                if not all_values:
                    return False
                headers = all_values[0]
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                row = []
                for h in headers:
                    if h in data_dict:      row.append(str(data_dict[h]))
                    elif h == 'tgl_upload': row.append(now)
                    else:                   row.append('')
                sheet.append_row(row, value_input_option='USER_ENTERED')
                time.sleep(0.5)
                st.cache_data.clear()
                return True
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"❌ Error add_ratifikasi_record: {e}")
                    return False

    def update_ratifikasi_record(self, id_ratifikasi, updates: dict):
        """Update kolom tertentu di tb_ratifikasi berdasarkan id_ratifikasi."""
        if not self.is_initialized() or self.spreadsheet_regulasi is None:
            return False
        for attempt in range(self.MAX_RETRIES):
            try:
                sheet = self.spreadsheet_regulasi.worksheet('tb_ratifikasi')
                all_values = sheet.get_all_values()
                if not all_values or len(all_values) < 2:
                    return False
                headers = all_values[0]
                id_col = headers.index('id_ratifikasi') if 'id_ratifikasi' in headers else 0
                row_index = None
                for i, row in enumerate(all_values[1:], start=2):
                    if len(row) > id_col and str(row[id_col]).strip() == str(id_ratifikasi).strip():
                        row_index = i
                        break
                if row_index is None:
                    return False
                for col_name, new_val in updates.items():
                    if col_name in headers:
                        sheet.update_cell(row_index, headers.index(col_name) + 1, str(new_val))
                time.sleep(0.5)
                st.cache_data.clear()
                return True
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    st.error(f"❌ Error update_ratifikasi_record: {e}")
                    return False


# ========== SINGLETON PATTERN ==========

_drive_manager_instance = None

def get_drive_manager():
    """Get Google Drive Manager instance (singleton)"""
    global _drive_manager_instance
    if _drive_manager_instance is None:
        _drive_manager_instance = GoogleDriveManager()
    return _drive_manager_instance

def reset_drive_manager():
    """Reset drive manager instance"""
    global _drive_manager_instance
    _drive_manager_instance = None