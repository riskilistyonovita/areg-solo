# modules/dokumen_lainnya.py
from modules._base_dokumen import show_dokumen_menu

def show():
    show_dokumen_menu(
        title="Dokumen Lainnya",
        icon="🗂️",
        mode="by_kategori",
        kat_keywords=["Program Kerja", "SPK", "RKK", "Notulen", "Dokumen Lainnya"],
        extra_label="Lainnya",
        menu_key="dokumen_lainnya",
        menu_id="MENU004",
        show_kadaluarsa=False,
        show_nonaktif=False,
        show_tgl_terbit=False,
    )