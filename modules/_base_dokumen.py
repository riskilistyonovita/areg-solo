# modules/_base_dokumen.py
"""
Shared base untuk PKS, e-Library, Dokumen Lainnya.
Subtabs dibuat DINAMIS berdasarkan bidang/kategori dari Google Sheets.
"""

import streamlit as st
import pandas as pd
from datetime import date
from utils.google_drive_manager import get_drive_manager
from utils.auth_manager import get_auth_manager
from modules.regulasi import (
    _render_dokumen_list, _render_kadaluarsa_table,
    _tab_upload, _tab_import_drive,
    _build_map, _reverse_map, _parse_date
)
from dateutil.relativedelta import relativedelta


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def show_dokumen_menu(
    title: str,
    icon: str,
    mode: str,          # "by_bidang" | "by_kategori"
    kat_keywords: list, # nama kategori yang termasuk (partial match)
    extra_label: str = "Lainnya",  # label untuk subtab sisa
    show_upload: bool = True,
    menu_key: str = "",   # key untuk get_menu_folder_id: pks|elibrary|dokumen_lainnya
    menu_id: str = "",    # menu_id dari sheet menu_id (prioritas utama filter)
    show_kadaluarsa: bool = True,  # tampilkan tab Kadaluarsa
    show_nonaktif:   bool = True,  # tampilkan tab Nonaktif
    show_tgl_terbit: bool = True,  # tampilkan kolom Tgl Terbit di tabel
):
    """
    mode="by_bidang"    → subtab = bidang di bawah kategori yg cocok
    mode="by_kategori"  → subtab = setiap kategori yang cocok
    """
    dm   = get_drive_manager()
    auth = get_auth_manager(dm)
    cu   = auth.get_current_user()
    can_edit   = auth.has_permission('regulasi', 'edit')
    can_delete = auth.has_permission('regulasi', 'hapus')

    st.title(f"{icon} {title}")
    st.markdown("---")

    # ----- Load data -----
    with st.spinner("Memuat data..."):
        docs    = dm.get_all_documents() or []
        df_kat  = dm.get_master_data('kategori_id')
        df_bid  = dm.get_master_data('bidang_id')
        df_unit = dm.get_master_data('unit_id')

    df_all   = pd.DataFrame(docs).fillna('') if docs else pd.DataFrame()
    kat_map  = _build_map(df_kat,  'kategori_id', 'nama_kategori')
    bid_map  = _build_map(df_bid,  'bidang_id',   'nama_bidang')
    unit_map = _build_map(df_unit, 'unit_id',      'nama_unit')

    # ---- Filter dokumen sesuai kategori keywords ----
    matched_kat_ids = _match_kat_ids(kat_map, kat_keywords,
                                      df_kat=df_kat, menu_id=menu_id)
    df_modul = _filter_by_ids(df_all, 'kategori_id', matched_kat_ids)

    # ---- Build subtab config dinamis ----
    if mode == "by_bidang":
        subtabs = _subtabs_by_bidang(df_modul, df_bid, kat_map, bid_map, matched_kat_ids, extra_label)
    else:  # by_kategori
        subtabs = _subtabs_by_kategori(df_modul, kat_map, matched_kat_ids)

    # ---- Buat tabs ----
    base_labels = [s['label'] for s in subtabs]
    extra_labels = []
    if show_kadaluarsa: extra_labels.append("⚠️ Kadaluarsa")
    if show_nonaktif:   extra_labels.append("🚫 Nonaktif")
    all_labels = base_labels + extra_labels
    tabs = st.tabs(all_labels)

    # Content tabs
    for i, sub in enumerate(subtabs):
        with tabs[i]:
            stable_key = "_".join(sub['ids']) if sub['ids'] else f"extra_{i}"
            df_sub = _filter_by_ids(df_modul, sub['id_col'], sub['ids']) if sub['ids'] else df_modul
            _render_daftar(df_sub, df_all, df_bid, kat_map, bid_map, unit_map,
                           can_edit, can_delete, dm, cu,
                           tab_key=f"{title}_{stable_key}",
                           lock_kat=sub.get('lock_kat'),
                           show_tgl_terbit=show_tgl_terbit)

    # Kadaluarsa
    if show_kadaluarsa:
        idx_kal = len(subtabs)
        with tabs[idx_kal]:
            _render_kadaluarsa(df_modul, dm, cu, kat_map, bid_map, unit_map,
                               can_edit, can_delete,
                               prefix=title.lower().replace(' ', '_'))

    # Nonaktif
    if show_nonaktif:
        idx_na = len(subtabs) + (1 if show_kadaluarsa else 0)
        with tabs[idx_na]:
            df_na = df_modul[
                df_modul.get('status', pd.Series(dtype=str)).str.lower().isin(
                    ['tidak aktif', 'nonaktif']
                )
            ] if not df_modul.empty and 'status' in df_modul.columns else pd.DataFrame()
            if df_na.empty:
                st.success("Tidak ada dokumen nonaktif.")
            else:
                _render_daftar(df_na, df_all, df_bid, kat_map, bid_map, unit_map,
                               can_edit, can_delete, dm, cu,
                               tab_key=f"{title}_nonaktif")


# ============================================================
# HELPERS: SUBTAB BUILDERS
# ============================================================

def _subtabs_by_bidang(df_modul, df_bid, kat_map, bid_map, kat_ids, extra_label):
    """Subtab berdasarkan bidang yang ada di bawah kategori terpilih"""
    subtabs = []

    if df_bid.empty or 'kategori_id' not in df_bid.columns:
        # Tidak ada data bidang → 1 tab Semua
        subtabs.append({'label': '📋 Semua', 'id_col': 'kategori_id',
                        'ids': kat_ids, 'lock_kat': None})
        return subtabs

    # Ambil bidang yang ada di bawah kat_ids + aktif
    df_bid_f = df_bid[df_bid['kategori_id'].astype(str).isin(kat_ids)]
    if 'status' in df_bid_f.columns:
        df_bid_f = df_bid_f[df_bid_f['status'].str.lower() == 'aktif']

    # Bidang yang benar-benar ada dokumennya
    if not df_modul.empty and 'bidang_id' in df_modul.columns:
        existing_bid_ids = df_modul['bidang_id'].astype(str).unique().tolist()
    else:
        existing_bid_ids = []

    added = []
    for _, row in df_bid_f.iterrows():
        bid_id   = str(row.get('bidang_id', ''))
        bid_name = str(row.get('nama_bidang', bid_id))
        subtabs.append({
            'label':    f"📁 {bid_name}",
            'id_col':   'bidang_id',
            'ids':      [bid_id],
            'lock_kat': None,
        })
        added.append(bid_id)

    # Dokumen tanpa bidang / bidang tidak dikenal
    doc_no_bid = []
    if not df_modul.empty and 'bidang_id' in df_modul.columns:
        doc_no_bid = df_modul[
            ~df_modul['bidang_id'].astype(str).isin(added)
        ].index.tolist()

    if subtabs and doc_no_bid:
        subtabs.append({'label': f"📂 {extra_label}", 'id_col': '__lainnya__',
                        'ids': [], 'lock_kat': None, '_index': doc_no_bid})
    elif not subtabs:
        subtabs.append({'label': '📋 Semua', 'id_col': 'kategori_id',
                        'ids': kat_ids, 'lock_kat': None})

    return subtabs


def _subtabs_by_kategori(df_modul, kat_map, kat_ids):
    """Subtab satu per kategori"""
    subtabs = []
    for kid in kat_ids:
        kname = kat_map.get(str(kid), str(kid))
        subtabs.append({
            'label':  f"📁 {kname}",
            'id_col': 'kategori_id',
            'ids':    [str(kid)],
            'lock_kat': str(kid),
        })
    if not subtabs:
        subtabs.append({'label': '📋 Semua', 'id_col': 'kategori_id',
                        'ids': [], 'lock_kat': None})
    return subtabs


# ============================================================
# HELPERS: FILTER & RENDER
# ============================================================

def _match_kat_ids(kat_map: dict, keywords: list,
                   df_kat=None, menu_id: str = '') -> list:
    """
    Return list kat_id yang sesuai.
    Prioritas:
    1. Filter by menu_id (jika menu_id diberikan dan kolom menu_id ada di df_kat)
    2. Keyword matching pada nama kategori (fallback)
    """
    # --- Prioritas 1: filter by menu_id ---
    if menu_id and df_kat is not None and not df_kat.empty and 'menu_id' in df_kat.columns:
        matched = []
        for _, r in df_kat.iterrows():
            kid  = str(r.get('kategori_id', '')).strip()
            mid  = str(r.get('menu_id', '')).strip()
            if kid and mid == menu_id:
                matched.append(kid)
        if matched:
            return matched
        # menu_id ada tapi tidak ada match → fallthrough ke keyword

    # --- Fallback: keyword matching ---
    if not keywords:
        return list(kat_map.keys())
    matched = []
    kw_lower = [kw.lower() for kw in keywords]
    for kid, kname in kat_map.items():
        for kw in kw_lower:
            if kw in kname.lower():
                matched.append(str(kid)); break
            if kw in str(kid).lower():
                matched.append(str(kid)); break
    return matched


def _filter_by_ids(df: pd.DataFrame, col: str, ids: list) -> pd.DataFrame:
    # Kalau ids kosong → kembalikan DataFrame kosong (bukan semua dokumen!)
    if df.empty or col not in df.columns:
        return pd.DataFrame()
    if not ids:
        return pd.DataFrame()
    return df[df[col].astype(str).isin(ids)]


def _render_daftar(df_show, df_all, df_bid, kat_map, bid_map, unit_map,
                   can_edit, can_delete, dm, cu, tab_key="", lock_kat=None,
                   show_tgl_terbit=True):
    """Render daftar aktif/draft dengan filter keyword"""
    df_aktif = df_show[
        df_show.get('status', pd.Series(dtype=str)).str.lower().isin(['aktif', 'draft'])
    ] if not df_show.empty and 'status' in df_show.columns else df_show

    # Search bar
    col1, col2 = st.columns([4, 2])
    with col1:
        kw = st.text_input("Cari nama dokumen...", key=f"kw_{tab_key}",
                            placeholder="Ketik untuk mencari...")
    with col2:
        if not lock_kat and not df_bid.empty and 'nama_bidang' in df_bid.columns:
            # dropdown bidang
            bid_in_tab = df_aktif['bidang_id'].astype(str).unique() if not df_aktif.empty and 'bidang_id' in df_aktif.columns else []
            bid_opts = {'Semua': ''}
            for _, r in df_bid.iterrows():
                if str(r.get('bidang_id', '')) in bid_in_tab:
                    bid_opts[str(r.get('nama_bidang', ''))] = str(r.get('bidang_id', ''))
            sel_bid = st.selectbox("Bidang", list(bid_opts.keys()), key=f"bid_{tab_key}")
            sel_bid_id = bid_opts.get(sel_bid, '')
        else:
            sel_bid_id = ''
            st.markdown('')

    # Apply filter
    df_r = df_aktif.copy()
    if kw:
        df_r = df_r[df_r.get('nama_regulasi', pd.Series(dtype=str)).str.contains(kw, case=False, na=False)]
    if sel_bid_id:
        df_r = df_r[df_r.get('bidang_id', pd.Series(dtype=str)) == sel_bid_id]

    # Statistik ringkas
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Dokumen", len(df_aktif))
    c2.metric("Ditampilkan",   len(df_r))
    n_kal = len(df_show[
        _get_expired_mask(df_show)
    ]) if not df_show.empty else 0
    c3.metric("Kadaluarsa", n_kal)
    st.markdown("")

    if df_r.empty:
        st.info("Tidak ada dokumen yang sesuai filter.")
        return

    _render_dokumen_list(df_r, dm, cu, kat_map, bid_map, unit_map,
                         can_edit, can_delete, page_key=f"base_{tab_key}",
                         show_tgl_terbit=show_tgl_terbit)


def _get_expired_mask(df):
    today = date.today()
    def is_exp(row):
        tgl = _parse_date(str(row.get('tanggal_kadaluarsa', '')))
        return (tgl and tgl < today) or str(row.get('status', '')).lower() in ('kadaluarsa', 'expired')
    return df.apply(is_exp, axis=1) if not df.empty else pd.Series(dtype=bool)


def _render_kadaluarsa(df_modul, dm, cu, kat_map, bid_map, unit_map,
                        can_edit, can_delete, prefix=""):
    today = date.today()
    batas = today + relativedelta(months=6)

    rows_exp, rows_dekat = [], []
    if not df_modul.empty:
        for _, row in df_modul.iterrows():
            status = str(row.get('status', '')).lower()
            tgl    = _parse_date(str(row.get('tanggal_kadaluarsa', '')))
            if tgl:
                if tgl < today:
                    rows_exp.append(row)
                elif tgl <= batas:
                    rows_dekat.append(row)
            elif status in ('kadaluarsa', 'expired'):
                rows_exp.append(row)

    df_exp   = pd.DataFrame(rows_exp)   if rows_exp   else pd.DataFrame()
    df_dekat = pd.DataFrame(rows_dekat) if rows_dekat else pd.DataFrame()

    c1, c2 = st.columns(2)
    c1.metric("⏳ Mendekati Kadaluarsa (≤6 bln)", len(df_dekat))
    c2.metric("❌ Sudah Kadaluarsa",               len(df_exp))
    st.markdown("")

    st.markdown("<div style='background:#fff3cd;border-left:4px solid #ffc107;"
                "padding:10px 16px;border-radius:4px;margin-bottom:8px'>"
                "<b>⏳ Mendekati Kadaluarsa</b></div>", unsafe_allow_html=True)
    if df_dekat.empty:
        st.success("Tidak ada.")
    else:
        _render_kadaluarsa_table(df_dekat, dm, cu, kat_map, bid_map, unit_map,
                                  can_edit, can_delete, today, prefix=f"{prefix}_dekat")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='background:#f8d7da;border-left:4px solid #dc3545;"
                "padding:10px 16px;border-radius:4px;margin-bottom:8px'>"
                "<b>❌ Sudah Kadaluarsa</b></div>", unsafe_allow_html=True)
    if df_exp.empty:
        st.success("Tidak ada.")
    else:
        _render_kadaluarsa_table(df_exp, dm, cu, kat_map, bid_map, unit_map,
                                  can_edit, can_delete, today, prefix=f"{prefix}_exp")