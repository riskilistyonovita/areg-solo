# utils/auth_manager.py
"""
Authentication Manager untuk A-REG SOLO
Handles login/logout dengan Google Sheets tb_users
"""

import streamlit as st
from datetime import datetime
import time

class AuthManager:
    """Manager untuk authentication dan authorization"""
    
    def __init__(self, drive_manager):
        """
        Initialize Auth Manager
        
        Args:
            drive_manager: Instance dari GoogleDriveManager
        """
        self.dm = drive_manager
        
        # Permission mapping dari screenshot hak akses
        self.PERMISSIONS = {
            'Admin': {
                'dashboard': ['view'],
                'regulasi': ['lihat', 'edit', 'hapus'],
                'bed_management': ['lihat', 'edit', 'hapus'],
                'igd_rujukan': ['lihat', 'edit', 'hapus'],
                'master_data': ['tambah', 'edit', 'hapus']
            },
            'IT': {
                'dashboard': ['view'],
                'regulasi': ['lihat', 'edit', 'hapus'],
                'bed_management': ['lihat', 'edit', 'hapus'],
                'igd_rujukan': ['lihat', 'edit', 'hapus'],
                'master_data': ['tambah', 'edit', 'hapus']
            },
            'Managemen': {
                'dashboard': ['view'],
                'regulasi': ['lihat', 'edit', 'hapus'],
                'bed_management': ['lihat', 'edit', 'hapus'],
                'igd_rujukan': ['lihat', 'edit', 'hapus'],
                'master_data': ['tambah', 'edit', 'hapus']
            },
            'Mutu dan PPI': {
                'dashboard': ['view'],
                'regulasi': ['lihat', 'edit', 'hapus'],
                'bed_management': ['lihat', 'edit', 'hapus'],
                'igd_rujukan': ['lihat', 'edit', 'hapus'],
                'master_data': ['tambah', 'edit', 'hapus']
            },
            'Sekretaris': {
                'dashboard': ['view'],
                'regulasi': ['lihat', 'edit', 'hapus'],
                'bed_management': ['lihat', 'edit', 'hapus'],
                'igd_rujukan': ['lihat', 'edit', 'hapus'],
                'master_data': ['tambah', 'edit', 'hapus']
            },
            # Role operasional (lihat + operasional, no master data)
            'Casemix': self._operational_access(),
            'CSSU': self._operational_access(),
            'Farmasi': self._operational_access(),
            'Front Office dan SFE': self._operational_access(),
            'Gizi dan Tataboga (Pantry)': self._operational_access(),
            'Perawat': self._operational_access(),
            'HRD': self._operational_access(),
            'Bidan': self._operational_access(),
            'Fisioterapi/KTK': self._operational_access(),
            'Kasir': self._operational_access(),
            'Keuangan': self._operational_access(),
            'Laboratorium': self._operational_access(),
            'Laundry': self._operational_access(),
            'Marketing': self._operational_access(),
            'Radiologi': self._operational_access(),
            'Rekam Medis': self._operational_access(),
            'Dokter Umum': self._operational_access(),
            'Kesling': self._operational_access(),
            'Jangum': self._operational_access(),
        }
    
    def _operational_access(self):
        """Permission untuk role operasional"""
        return {
            'dashboard': ['view'],
            'regulasi': ['lihat'],
            'bed_management': ['lihat', 'edit', 'hapus'],
            'igd_rujukan': ['lihat', 'edit', 'hapus'],
            'master_data': []
        }
    
    @st.cache_data(ttl=600, show_spinner=False)
    def _get_users(_self):
        """
        Get all users dengan caching 10 menit
        
        Returns:
            list: List of user dictionaries
        """
        try:
            return _self.dm.get_users()
        except Exception as e:
            st.error(f"âŒ Error loading users: {str(e)}")
            return []
    
    def authenticate(self, user_id, password):
        """
        Authenticate user dengan user_id dan password
        
        Args:
            user_id (str): User ID (9 digit)
            password (str): Password (plain text)
        
        Returns:
            tuple: (user_dict, error_message)
                   user_dict is None if auth failed
        """
        # Validasi input
        if not user_id or not password:
            return None, "User ID dan Password harus diisi"
        
        # Validasi user_id format (9 digit)
        if not user_id.isdigit() or len(user_id) != 9:
            return None, "User ID harus 9 digit angka"
        
        # Get users dari cache
        users = self._get_users()
        
        if not users:
            return None, "Tidak dapat mengakses database users"
        
        # Find user by user_id
        user = None
        for u in users:
            if str(u.get('user_id', '')).strip() == user_id.strip():
                user = u
                break
        
        if not user:
            return None, f"User ID {user_id} tidak ditemukan"
        
        # Check status
        if str(user.get('status', '')).strip().lower() != 'aktif':
            return None, "User tidak aktif. Hubungi administrator"
        
        # Validate password (plain text comparison)
        if str(user.get('password', '')).strip() != password.strip():
            return None, "Password salah"
        
        # Auth success
        return user, None
    
    def create_session(self, user):
        """
        Create session untuk user yang berhasil login
        
        Args:
            user (dict): User data dari tb_users
        """
        st.session_state['authenticated'] = True
        st.session_state['user_id'] = str(user.get('user_id', ''))
        st.session_state['username'] = str(user.get('username', ''))
        st.session_state['nama_lengkap'] = str(user.get('nama_lengkap', ''))
        st.session_state['role'] = str(user.get('role', ''))
        st.session_state['unit_kerja'] = str(user.get('unit_kerja', ''))
        st.session_state['email'] = str(user.get('email', ''))
        st.session_state['no_hp'] = str(user.get('no_hp', ''))
        st.session_state['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Set permissions - case-insensitive lookup
        role = st.session_state['role']
        # Coba exact match dulu, lalu case-insensitive
        perms = self.PERMISSIONS.get(role, None)
        if perms is None:
            for key in self.PERMISSIONS:
                if key.lower() == role.lower():
                    perms = self.PERMISSIONS[key]
                    break
        # Jika role tidak ditemukan, beri akses lihat saja
        st.session_state['permissions'] = perms if perms is not None else {
            'dashboard': ['view'],
            'regulasi':  ['lihat'],
            'master_data': []
        }
        st.session_state['role_matched'] = role
    
    def logout(self):
        """Clear session (logout)"""
        keys_to_clear = [
            'authenticated', 'user_id', 'username', 'nama_lengkap',
            'role', 'unit_kerja', 'email', 'no_hp', 'login_time',
            'permissions'
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def is_authenticated(self):
        """
        Check if user is authenticated
        
        Returns:
            bool: True if authenticated
        """
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self):
        """
        Get current logged in user data
        
        Returns:
            dict: User data from session
        """
        if not self.is_authenticated():
            return None
        
        return {
            'user_id': st.session_state.get('user_id', ''),
            'username': st.session_state.get('username', ''),
            'nama_lengkap': st.session_state.get('nama_lengkap', ''),
            'role': st.session_state.get('role', ''),
            'unit_kerja': st.session_state.get('unit_kerja', ''),
            'email': st.session_state.get('email', ''),
            'no_hp': st.session_state.get('no_hp', ''),
            'login_time': st.session_state.get('login_time', '')
        }
    
    def has_permission(self, module, action):
        """
        Check if current user has permission for specific action
        
        Args:
            module (str): Module name (dashboard, regulasi, bed_management, etc)
            action (str): Action name (view, lihat, edit, hapus, tambah)
        
        Returns:
            bool: True if user has permission
        """
        if not self.is_authenticated():
            return False
        
        permissions = st.session_state.get('permissions', {})
        module_perms = permissions.get(module, [])
        
        return action.lower() in [p.lower() for p in module_perms]
    
    def require_permission(self, module, action, show_error=True):
        """
        Decorator/helper untuk require permission
        Jika tidak punya akses, tampilkan error
        
        Args:
            module (str): Module name
            action (str): Action name
            show_error (bool): Show error message if no permission
        
        Returns:
            bool: True if has permission
        """
        if self.has_permission(module, action):
            return True
        
        if show_error:
            st.error(f"âŒ Anda tidak memiliki akses untuk {action} di menu {module}")
            st.info(f"Role Anda: {st.session_state.get('role', 'Unknown')}")
        
        return False
    
    def get_session_duration(self):
        """
        Get duration since login
        
        Returns:
            str: Duration string (e.g., "2 jam 30 menit")
        """
        if not self.is_authenticated():
            return "Not logged in"
        
        login_time_str = st.session_state.get('login_time', '')
        if not login_time_str:
            return "Unknown"
        
        try:
            login_time = datetime.strptime(login_time_str, '%Y-%m-%d %H:%M:%S')
            duration = datetime.now() - login_time
            
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            
            if hours > 0:
                return f"{hours} jam {minutes} menit"
            else:
                return f"{minutes} menit"
        except:
            return "Unknown"


# Singleton pattern untuk AuthManager
def get_auth_manager(drive_manager):
    """
    Get or create AuthManager instance (singleton)
    
    Args:
        drive_manager: GoogleDriveManager instance
    
    Returns:
        AuthManager: Singleton instance
    """
    if 'auth_manager' not in st.session_state:
        st.session_state.auth_manager = AuthManager(drive_manager)
    
    return st.session_state.auth_manager