# modules/elibrary.py
from modules._base_dokumen import show_dokumen_menu

def show():
    show_dokumen_menu(
        title="e-Library",
        icon="📚",
        mode="by_kategori",
        kat_keywords=["e-LIBRARY", "LIBRARY", "PNPK", "Clinical Pathway", "Lainnya"],
        extra_label="Lainnya",
        menu_key="elibrary",
        menu_id="MENU003",
        show_kadaluarsa=False,
        show_nonaktif=False,
        show_tgl_terbit=False,
    )