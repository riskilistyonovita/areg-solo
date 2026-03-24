# modules/pks.py
from modules._base_dokumen import show_dokumen_menu

def show():
    show_dokumen_menu(
        title="Perijinan & PKS",
        icon="🤝",
        mode="by_kategori",          # ← tiap tab = satu kategori (Klinis/Manajerial/Perijinan)
        kat_keywords=["PKS", "Perijinan", "Klinis", "Manajerial", "Kerjasama"],
        extra_label="Lainnya",
        menu_key="pks",
        menu_id="MENU002",
    )