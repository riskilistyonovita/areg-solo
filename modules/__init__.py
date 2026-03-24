# modules/__init__.py
"""
Modules package untuk AREG SOLO
Berisi semua menu module: regulasi, elibrary, pks, dokumen_lainnya, master_data
"""

# Import semua module agar bisa digunakan dengan: from modules import regulasi
try:
    from . import regulasi
except ImportError as e:
    print(f"Warning: Failed to import regulasi - {e}")

try:
    from . import elibrary
except ImportError as e:
    print(f"Warning: Failed to import elibrary - {e}")

try:
    from . import pks
except ImportError as e:
    print(f"Warning: Failed to import pks - {e}")

try:
    from . import dokumen_lainnya
except ImportError as e:
    print(f"Warning: Failed to import dokumen_lainnya - {e}")

try:
    from . import master_data
except ImportError as e:
    print(f"Warning: Failed to import master_data - {e}")

try:
    from . import _base_dokumen
except ImportError as e:
    print(f"Warning: Failed to import _base_dokumen - {e}")

# List semua module yang tersedia
__all__ = [
    'regulasi',
    'elibrary', 
    'pks',
    'dokumen_lainnya',
    'master_data',
    '_base_dokumen'
]