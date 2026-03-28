# utils/auth_manager.py
"""
Authentication Manager untuk A-REG SOLO
Handles login/logout dengan Google Sheets tb_users

Role hierarchy:
  DIREKSI      : Direktur, Wakil Direktur
  TIM REGULASI : Ketua Tim Regulasi, Sekretaris Tim Regulasi,
                 Mutu dan PPI, Sekretaris
  MANAJEMEN    : Manajer Bidang (alias: Managemen)
  UNIT         : Kepala Unit
  IT/ADMIN     : Admin, IT
  STAF         : semua role operasional (lihat saja)

Multi-role: kolom 'role' di tb_users bisa diisi lebih dari satu,
dipisah koma — mis. "Manajer Bidang,Ketua Tim Regulasi".
Permission yang diterima = gabungan (union) semua role.

Action khusus ratifikasi:
  approve_t1  → Manajer Bidang
  approve_t2  → Wakil Direktur, Ketua Tim Regulasi, Sekretaris Tim Regulasi
  distribusi  → Ketua Tim Regulasi, Sekretaris Tim Regulasi,
                Mutu dan PPI, Sekretaris, Admin, IT
"""

import streamlit as st
from datetime import datetime

try:
    import bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False


class AuthManager:

    def __init__(self, drive_manager):
        self.dm = drive_manager

        self.PERMISSIONS = {

            # ── DIREKSI ──────────────────────────────────────────────────
            'Direktur': {
                'dashboard':       ['view'],
                'regulasi':        ['lihat'],
                'perijinan_pks':   ['lihat'],
                'elibrary':        ['lihat'],
                'dokumen_lainnya': ['lihat'],
                'ratifikasi':      ['lihat'],
                'master_data':     [],
            },
            'Wakil Direktur': {
                'dashboard':       ['view'],
                'regulasi':        ['lihat'],
                'perijinan_pks':   ['lihat'],
                'elibrary':        ['lihat'],
                'dokumen_lainnya': ['lihat'],
                'ratifikasi':      ['lihat', 'approve_t2'],
                'master_data':     [],
            },

            # ── TIM REGULASI ─────────────────────────────────────────────
            'Ketua Tim Regulasi': {
                'dashboard':       ['view'],
                'regulasi':        ['lihat', 'edit', 'hapus'],
                'perijinan_pks':   ['lihat', 'edit', 'hapus'],
                'elibrary':        ['lihat', 'edit', 'hapus'],
                'dokumen_lainnya': ['lihat', 'edit', 'hapus'],
                'ratifikasi':      ['lihat', 'approve_t2', 'distribusi'],
                'master_data':     [],
            },
            'Sekretaris Tim Regulasi': {
                'dashboard':       ['view'],
                'regulasi':        ['lihat', 'edit', 'hapus'],
                'perijinan_pks':   ['lihat', 'edit', 'hapus'],
                'elibrary':        ['lihat', 'edit', 'hapus'],
                'dokumen_lainnya': ['lihat', 'edit', 'hapus'],
                'ratifikasi':      ['lihat', 'approve_t2', 'distribusi'],
                'master_data':     ['lihat', 'tambah', 'edit', 'hapus'],
            },
            'Mutu dan PPI': {
                'dashboard':       ['view'],
                'regulasi':        ['lihat', 'edit', 'hapus'],
                'perijinan_pks':   ['lihat', 'edit', 'hapus'],
                'elibrary':        ['lihat', 'edit', 'hapus'],
                'dokumen_lainnya': ['lihat', 'edit', 'hapus'],
                'ratifikasi':      ['lihat', 'distribusi'],
                'master_data':     [],
            },
            'Sekretaris': {
                'dashboard':       ['view'],
                'regulasi':        ['lihat', 'edit', 'hapus'],
                'perijinan_pks':   ['lihat', 'edit', 'hapus'],
                'elibrary':        ['lihat', 'edit', 'hapus'],
                'dokumen_lainnya': ['lihat', 'edit', 'hapus'],
                'ratifikasi':      ['lihat', 'distribusi'],
                'master_data':     [],
            },

            # ── MANAJEMEN ────────────────────────────────────────────────
            'Manajer Bidang': {
                'dashboard':       ['view'],
                'regulasi':        ['lihat', 'edit', 'hapus'],
                'perijinan_pks':   ['lihat', 'edit', 'hapus'],
                'elibrary':        ['lihat', 'edit', 'hapus'],
                'dokumen_lainnya': ['lihat', 'edit', 'hapus'],
                'ratifikasi':      ['lihat', 'approve_t1'],
                'master_data':     ['lihat', 'tambah', 'edit', 'hapus'],
            },
            # Alias lama — akun yang sudah pakai 'Managemen' tetap berfungsi
            'Managemen': {
                'dashboard':       ['view'],
                'regulasi':        ['lihat', 'edit', 'hapus'],
                'perijinan_pks':   ['lihat', 'edit', 'hapus'],
                'elibrary':        ['lihat', 'edit', 'hapus'],
                'dokumen_lainnya': ['lihat', 'edit', 'hapus'],
                'ratifikasi':      ['lihat', 'approve_t1'],
                'master_data':     ['lihat', 'tambah', 'edit', 'hapus'],
            },

            # ── UNIT ─────────────────────────────────────────────────────
            'Kepala Unit': self._unit_access(),

            # ── IT / ADMIN ───────────────────────────────────────────────
            'Admin': self._admin_access(),
            'IT':    self._admin_access(),

            # ── STAF OPERASIONAL ─────────────────────────────────────────
            'Bidan':                      self._staff_access(),
            'Casemix':                    self._staff_access(),
            'CSSU':                       self._staff_access(),
            'Dokter Spesialis':           self._staff_access(),
            'Dokter Umum':                self._staff_access(),
            'Farmasi':                    self._staff_access(),
            'Fisioterapi/KTK':            self._staff_access(),
            'Front Office dan SFE':       self._staff_access(),
            'Gizi dan Tataboga (Pantry)': self._staff_access(),
            'HRD':                        self._staff_access(),
            'Jangum':                     self._staff_access(),
            'Kasir':                      self._staff_access(),
            'Kesling':                    self._staff_access(),
            'Keuangan':                   self._staff_access(),
            'Laboratorium':               self._staff_access(),
            'Laundry':                    self._staff_access(),
            'Marketing':                  self._staff_access(),
            'Perawat':                    self._staff_access(),
            'Radiologi':                  self._staff_access(),
            'Rekam Medis':                self._staff_access(),
        }

    # ── Permission presets ──────────────────────────────────────────────

    def _admin_access(self):
        """Admin/IT — akses penuh termasuk master data, bisa distribusi."""
        return {
            'dashboard':       ['view'],
            'regulasi':        ['lihat', 'edit', 'hapus'],
            'perijinan_pks':   ['lihat', 'edit', 'hapus'],
            'elibrary':        ['lihat', 'edit', 'hapus'],
            'dokumen_lainnya': ['lihat', 'edit', 'hapus'],
            'ratifikasi':      ['lihat', 'distribusi'],
            'master_data':     ['lihat', 'tambah', 'edit', 'hapus'],
        }

    def _unit_access(self):
        """Kepala Unit — lihat saja di webapp, edit GDocs via Drive sharing."""
        return {
            'dashboard':       ['view'],
            'regulasi':        ['lihat'],
            'perijinan_pks':   ['lihat'],
            'elibrary':        ['lihat'],
            'dokumen_lainnya': ['lihat'],
            'ratifikasi':      ['lihat'],
            'master_data':     [],
        }

    def _staff_access(self):
        """Staf operasional — lihat saja semua modul."""
        return {
            'dashboard':       ['view'],
            'regulasi':        ['lihat'],
            'perijinan_pks':   ['lihat'],
            'elibrary':        ['lihat'],
            'dokumen_lainnya': ['lihat'],
            'ratifikasi':      ['lihat'],
            'master_data':     [],
        }

    # ── User data ───────────────────────────────────────────────────────

    @st.cache_data(ttl=600, show_spinner=False)
    def _get_users(_self):
        """Get all users dengan caching 10 menit."""
        try:
            return _self.dm.get_users()
        except Exception as e:
            st.error(f"❌ Error loading users: {str(e)}")
            return []

    # ── Authentication ──────────────────────────────────────────────────

    def authenticate(self, user_id, password):
        """
        Authenticate user. Mendukung bcrypt ($2b$/$2a$) dan plain text.

        Returns:
            tuple: (user_dict, error_message)
        """
        if not user_id or not password:
            return None, "User ID dan Password harus diisi"

        user_id  = user_id.strip()
        password = password.strip()

        users = self._get_users()
        if not users:
            return None, "Tidak dapat mengakses database users"

        user = next(
            (u for u in users
             if str(u.get('user_id', '')).strip().upper() == user_id.upper()),
            None,
        )
        if not user:
            return None, f"User ID {user_id} tidak ditemukan"

        if str(user.get('status', '')).strip().lower() != 'aktif':
            return None, "Akun tidak aktif. Hubungi IT"

        stored_pw = str(user.get('password', '')).strip()
        pw_ok = False
        if _BCRYPT_AVAILABLE and stored_pw.startswith(('$2b$', '$2a$')):
            try:
                pw_ok = bcrypt.checkpw(password.encode(), stored_pw.encode())
            except Exception:
                pw_ok = False
        else:
            pw_ok = (password == stored_pw)

        if not pw_ok:
            return None, "Password salah"

        return user, None

    # ── Session ─────────────────────────────────────────────────────────

    def create_session(self, user):
        """
        Buat session. Support multi-role: kolom 'role' di tb_users
        bisa diisi lebih dari satu role dipisah koma.
        Permission = union dari semua role yang dimiliki.
        """
        st.session_state['authenticated'] = True
        st.session_state['user_id']       = str(user.get('user_id', ''))
        st.session_state['username']      = str(user.get('username', ''))
        st.session_state['nama_lengkap']  = str(user.get('nama_lengkap', ''))
        st.session_state['role']          = str(user.get('role', ''))
        st.session_state['unit_kerja']    = str(user.get('unit_kerja', ''))
        st.session_state['email']         = str(user.get('email', ''))
        st.session_state['no_hp']         = str(user.get('no_hp', ''))
        st.session_state['login_time']    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Parse multi-role dari kolom role (dipisah koma)
        raw_role = st.session_state['role']
        roles    = [r.strip() for r in raw_role.split(',') if r.strip()]

        # Gabungkan permission semua role (union)
        merged = {}
        for role in roles:
            perms = self.PERMISSIONS.get(role)
            if perms is None:
                for key in self.PERMISSIONS:
                    if key.lower() == role.lower():
                        perms = self.PERMISSIONS[key]
                        break
            if perms is None:
                continue

            for module, actions in perms.items():
                if module not in merged:
                    merged[module] = set()
                merged[module].update(actions)

        merged = {mod: list(acts) for mod, acts in merged.items()}

        # Fallback minimal jika tidak ada role dikenal
        if not merged:
            merged = {
                'dashboard':       ['view'],
                'regulasi':        ['lihat'],
                'perijinan_pks':   ['lihat'],
                'elibrary':        ['lihat'],
                'dokumen_lainnya': ['lihat'],
                'ratifikasi':      ['lihat'],
                'master_data':     [],
            }

        st.session_state['permissions']  = merged
        st.session_state['roles']        = roles
        st.session_state['role_matched'] = raw_role

    def logout(self):
        for key in [
            'authenticated', 'user_id', 'username', 'nama_lengkap',
            'role', 'roles', 'unit_kerja', 'email', 'no_hp', 'login_time',
            'permissions', 'role_matched',
        ]:
            st.session_state.pop(key, None)

    # ── Helpers ─────────────────────────────────────────────────────────

    def is_authenticated(self):
        return st.session_state.get('authenticated', False)

    def get_current_user(self):
        if not self.is_authenticated():
            return None
        return {
            'user_id':      st.session_state.get('user_id', ''),
            'username':     st.session_state.get('username', ''),
            'nama_lengkap': st.session_state.get('nama_lengkap', ''),
            'role':         st.session_state.get('role', ''),
            'roles':        st.session_state.get('roles', []),
            'unit_kerja':   st.session_state.get('unit_kerja', ''),
            'email':        st.session_state.get('email', ''),
            'no_hp':        st.session_state.get('no_hp', ''),
            'login_time':   st.session_state.get('login_time', ''),
        }

    def has_permission(self, module, action):
        """
        Cek izin untuk action di modul tertentu.

        Action standar : view, lihat, edit, hapus, tambah
        Action ratifikasi: approve_t1, approve_t2, distribusi
        """
        if not self.is_authenticated():
            return False
        perms = st.session_state.get('permissions', {})
        return action.lower() in [p.lower() for p in perms.get(module, [])]

    def require_permission(self, module, action, show_error=True):
        if self.has_permission(module, action):
            return True
        if show_error:
            st.error(f"⛔ Anda tidak memiliki akses **{action}** di menu **{module}**")
            roles = st.session_state.get('roles', [st.session_state.get('role', '')])
            st.info(f"Role Anda: **{', '.join(roles)}**")
        return False

    def get_session_duration(self):
        if not self.is_authenticated():
            return "Not logged in"
        try:
            login_time = datetime.strptime(
                st.session_state.get('login_time', ''), '%Y-%m-%d %H:%M:%S'
            )
            dur = datetime.now() - login_time
            h = dur.seconds // 3600
            m = (dur.seconds % 3600) // 60
            return f"{h} jam {m} menit" if h > 0 else f"{m} menit"
        except Exception:
            return "Unknown"


# ── Singleton factory ───────────────────────────────────────────────────

def get_auth_manager(drive_manager):
    if 'auth_manager' not in st.session_state:
        st.session_state.auth_manager = AuthManager(drive_manager)
    return st.session_state.auth_manager