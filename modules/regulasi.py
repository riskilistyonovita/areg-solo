# modules/regulasi.py
"""
Modul Regulasi - AREG SOLO
Kelola dokumen regulasi: lihat, cari, filter, upload, edit, hapus
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils.google_drive_manager import get_drive_manager
from utils.auth_manager import get_auth_manager


# Kategori yang DIPINDAHKAN ke menu lain (tidak tampil di Regulasi utama)
_EXCLUDE_KAT = [
    "e-LIBRARY", "e-library", "LIBRARY",
    "Program Kerja",
    "PKS", "Perjanjian Kerjasama", "Perijinan",
    "SPK", "RKK", "Notulen",
]


def show(default_tab='daftar'):
    dm = get_drive_manager()
    auth = get_auth_manager(dm)
    current_user = auth.get_current_user()

    # Map default_tab ke index
    _tab_index_map = {'daftar': 0, 'kadaluarsa': 1, 'upload': 2, 'import': 3, 'nonaktif': 4}
    _default_idx = _tab_index_map.get(default_tab, 0)

    st.title("Regulasi")
    st.markdown("---")

    # Jika dipanggil langsung dari menu Upload File
    if default_tab == 'upload':
        if auth.has_permission('regulasi', 'edit'):
            _tab_upload(dm, current_user)
        else:
            st.warning("Anda tidak memiliki akses untuk mengupload dokumen.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Daftar Dokumen",
        "⚠️ Kadaluarsa",
        "🚫 Nonaktif",
        "📧 Kirim Notifikasi",
    ])

    with tab1:
        _tab_daftar(dm, auth, current_user, status_filter=['aktif', 'draft'], tab_key="aktif", exclude_kat_keywords=_EXCLUDE_KAT)

    with tab2:
        _tab_kadaluarsa(dm, auth, current_user)

    with tab3:
        _tab_daftar(dm, auth, current_user, status_filter=['tidak aktif', 'nonaktif', 'test'], tab_key="nonaktif", exclude_kat_keywords=_EXCLUDE_KAT)

    with tab4:
        _tab_kirim_notifikasi(dm, auth)



# ============================================================
# TAB KIRIM NOTIFIKASI EMAIL
# ============================================================

def _tab_kirim_notifikasi(dm, auth):
    """Tab untuk kirim email notifikasi batch regulasi hari ini."""

    # Hanya admin/mutu yang bisa kirim
    can_send = auth.has_permission('regulasi', 'edit')

    st.subheader("📧 Kirim Notifikasi Regulasi")
    st.markdown(
        "<p style='color:#666;font-size:14px;'>"
        "Kirim email ke seluruh unit RS Hermina Solo berisi daftar regulasi "
        "yang diupload <b>hari ini</b>.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    if not can_send:
        st.warning("⛔ Anda tidak memiliki akses untuk mengirim notifikasi.")
        return

    try:
        from utils.email_sender import get_regulasi_hari_ini, kirim_notifikasi_batch, _get_email_list
    except ImportError:
        st.error("❌ Modul email_sender belum terpasang. "
                 "Pastikan file `utils/email_sender.py` sudah ada.")
        return

    col_preview, col_info = st.columns([3, 2])

    with col_preview:
        st.markdown("**📋 Regulasi yang akan dikirim (hari ini)**")
        with st.spinner("Mengambil data..."):
            docs_hari_ini = get_regulasi_hari_ini(dm)

        if not docs_hari_ini:
            st.info("📭 Tidak ada regulasi baru yang diupload hari ini.")
        else:
            for i, doc in enumerate(docs_hari_ini, 1):
                st.markdown(
                    f"<div style='padding:8px 14px;margin:4px 0;"
                    f"background:#f8f9fa;border-left:3px solid #00a859;"
                    f"border-radius:0 6px 6px 0;font-size:13px;'>"
                    f"<b>{i}.</b> {doc['nama']}"
                    f"<span style='color:#00a859;font-size:11px;"
                    f"margin-left:8px;'>[ {doc['kategori']} ]</span></div>",
                    unsafe_allow_html=True
                )

    with col_info:
        st.markdown("**📨 Penerima Email**")
        with st.spinner("Mengambil daftar penerima..."):
            penerima = _get_email_list(dm)

        if penerima:
            st.success(f"✅ **{len(penerima)} unit** terdaftar aktif")
            with st.expander("Lihat daftar penerima"):
                for e in penerima:
                    st.caption(f"• {e}")
        else:
            st.warning("⚠️ Tidak ada email unit aktif di sheet `email_unit`.")

    st.markdown("---")

    if not docs_hari_ini:
        st.info("💡 Upload regulasi terlebih dahulu, lalu kembali ke tab ini untuk kirim notifikasi.")
        return

    if not penerima:
        st.warning("Tambahkan email unit di Google Sheets → worksheet `email_unit` terlebih dahulu.")
        return

    # Tombol kirim
    col_btn, col_space = st.columns([2, 4])
    with col_btn:
        if st.button(
            f"📧 Kirim Notifikasi ke {len(penerima)} Unit",
            type="primary",
            use_container_width=True
        ):
            with st.spinner(f"Mengirim email ke {len(penerima)} unit..."):
                hasil = kirim_notifikasi_batch(dm, docs=docs_hari_ini)

            if hasil['success']:
                st.success(hasil['message'])
                st.balloons()
            else:
                st.error(f"❌ Gagal: {hasil['message']}")


# ============================================================
# TAB 1: DAFTAR DOKUMEN (search + filter + tabel + aksi)
# ============================================================

def _tab_daftar(dm, auth, current_user, status_filter=None, tab_key="t1", exclude_kat_keywords=None):
    can_edit   = auth.has_permission('regulasi', 'edit')
    can_delete = auth.has_permission('regulasi', 'hapus')

    # Load data
    with st.spinner("Memuat dokumen..."):
        docs    = dm.get_all_documents()
        df_kat  = dm.get_master_data('kategori_id')
        df_bid  = dm.get_master_data('bidang_id')
        df_unit = dm.get_master_data('unit_id')

    if not docs:
        st.info("Belum ada dokumen. Silakan upload dokumen terlebih dahulu.")
        return

    df = pd.DataFrame(docs).fillna('')

    # Lookup ID -> Nama
    kat_map_full = _build_map(df_kat,  'kategori_id', 'nama_kategori')
    bid_map      = _build_map(df_bid,  'bidang_id',   'nama_bidang')
    unit_map     = _build_map(df_unit, 'unit_id',      'nama_unit')

    # Exclude kategori yang sudah punya menu sendiri
    # Prioritas: filter by menu_id MENU001 (Regulasi) jika kolom tersedia
    # Fallback: keyword matching
    exclude_ids = set()
    if exclude_kat_keywords:
        # Coba filter by menu_id = MENU001 (hanya tampilkan Regulasi)
        menu_id_filter_available = (
            not df_kat.empty and 'menu_id' in df_kat.columns
        )
        if menu_id_filter_available:
            # Exclude semua yang BUKAN MENU001
            for _, row in df_kat.iterrows():
                kid = str(row.get('kategori_id', '')).strip()
                mid = str(row.get('menu_id', '')).strip()
                if kid and mid and mid != 'MENU001':
                    exclude_ids.add(kid)
        else:
            # Fallback: keyword matching lama
            for kid, kname in kat_map_full.items():
                for kw in exclude_kat_keywords:
                    if kw.lower() in kname.lower():
                        exclude_ids.add(str(kid))

        if exclude_ids and 'kategori_id' in df.columns:
            df = df[~df['kategori_id'].astype(str).isin(exclude_ids)]

    # kat_map hanya berisi kategori yang TIDAK di-exclude
    kat_map = {k: v for k, v in kat_map_full.items() if str(k) not in exclude_ids}

    # ----- Filter bar -----
    st.markdown("#### Filter & Pencarian")
    col1, col2 = st.columns([3, 2])

    with col1:
        keyword = st.text_input("Cari nama / nomor regulasi...",
                                 key=f"reg_keyword_{tab_key}", placeholder="Ketik untuk mencari...")
    with col2:
        kat_list = ["Semua"] + list(kat_map.values())
        sel_kat_nama = st.selectbox("Kategori", kat_list, key=f"reg_kat_{tab_key}")
        sel_kat_id = _reverse_map(kat_map, sel_kat_nama)

    sel_bid_id = None  # bidang filter dihapus
    # ----- Apply filter -----
    # Filter by status_filter (tab-level) dulu
    df_tab = df.copy()
    if status_filter:
        df_tab = df_tab[
            df_tab.get('status', pd.Series(dtype=str)).str.lower().isin(
                [s.lower() for s in status_filter]
            )
        ]

    df_result = df_tab.copy()
    if keyword:
        mask = (
            df_result.get('nama_regulasi',  pd.Series(dtype=str)).str.contains(keyword, case=False, na=False) |
            df_result.get('nomor_regulasi', pd.Series(dtype=str)).str.contains(keyword, case=False, na=False)
        )
        df_result = df_result[mask]
    if sel_kat_id:
        df_result = df_result[df_result.get('kategori_id', pd.Series(dtype=str)) == sel_kat_id]
    if sel_bid_id:
        df_result = df_result[df_result.get('bidang_id', pd.Series(dtype=str)) == sel_bid_id]

    # ----- Statistik -----
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    total_all  = len(df)
    total_tab  = len(df_tab)
    total_show = len(df_result)
    n_aktif = len(df[df.get('status', pd.Series(dtype=str)).str.lower() == 'aktif'])               if 'status' in df.columns else 0
    n_kal   = len(df[df.get('status', pd.Series(dtype=str)).str.lower().isin(['kadaluarsa','expired'])])               if 'status' in df.columns else 0
    c1.metric("Total Semua Dok", total_all)
    c2.metric("Dalam Tab Ini",   total_tab)
    c3.metric("Aktif",           n_aktif)
    c4.metric("Kadaluarsa",      n_kal)
    st.markdown("")

    if df_result.empty:
        st.warning("Tidak ada dokumen yang sesuai filter.")
        return

    # ----- Daftar dokumen -----
    _render_dokumen_list(df_result, dm, current_user,
                         kat_map, bid_map, unit_map, can_edit, can_delete,
                         page_key=f"reg_{tab_key}")


def _render_dokumen_list(df, dm, current_user, kat_map, bid_map, unit_map,
                          can_edit, can_delete, page_key="default",
                          show_tgl_terbit=True):
    if 'reg_edit_id'        not in st.session_state: st.session_state.reg_edit_id        = None
    if 'reg_confirm_delete' not in st.session_state: st.session_state.reg_confirm_delete = None

    st.markdown("""
    <style>
    /* ── Semua button di area tabel: seragam ukuran & font ── */
    [data-testid="stButton"] > button,
    [data-testid="stLinkButton"] > a {
        font-size: 12px !important;
        padding: 4px 8px !important;
        height: 30px !important;
        min-height: 30px !important;
        line-height: 1 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    /* ── Header tabel ── */
    .tbl-header {
        background: #f0f2f6;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 700;
        color: #444;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        margin-bottom: 4px;
    }
    /* ── Baris tabel ── */
    .tbl-row {
        border-bottom: 1px solid #f0f0f0;
        padding: 6px 0 2px 0;
    }
    .tbl-nama  { font-size: 13px; color: #1a1a1a; line-height: 1.4; }
    .tbl-kat   { font-size: 12px; color: #555; }
    .tbl-tgl   { font-size: 12px; color: #666; }
    /* ── Badge status ── */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-aktif    { background:#e6f4ea; color:#1e7e34; }
    .badge-draft    { background:#fff3cd; color:#856404; }
    .badge-expired  { background:#fde8e8; color:#b91c1c; }
    .badge-nonaktif { background:#f0f0f0; color:#666; }
    /* ── Padding antar kolom ── */
    div[data-testid="stHorizontalBlock"] > div {
        padding-top: 4px !important;
        padding-bottom: 4px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ===== PAGINATION =====
    PAGE_SIZE = 25
    total_rows  = len(df)
    total_pages = max(1, -(-total_rows // PAGE_SIZE))

    pg_key = f"_page_{page_key}"
    if pg_key not in st.session_state:
        st.session_state[pg_key] = 1
    if st.session_state[pg_key] > total_pages:
        st.session_state[pg_key] = 1

    current_page = st.session_state[pg_key]
    start_idx    = (current_page - 1) * PAGE_SIZE
    end_idx      = min(start_idx + PAGE_SIZE, total_rows)
    df_page      = df.iloc[start_idx:end_idx]

    # Info paginasi
    st.markdown(
        f"<div style='font-size:12px;color:#999;margin-bottom:8px'>"
        f"Menampilkan <b style='color:#555'>{start_idx+1}–{end_idx}</b> "
        f"dari <b style='color:#555'>{total_rows}</b> dokumen</div>",
        unsafe_allow_html=True,
    )

    # ── Header ──
    if show_tgl_terbit:
        COL = [2, 5, 2, 1.8, 2.8]
        headers = ["Kategori", "Nama Dokumen", "Tgl Terbit", "Status", "Aksi"]
    else:
        COL = [2, 6, 1.8, 2.8]
        headers = ["Kategori", "Nama Dokumen", "Status", "Aksi"]
    h = st.columns(COL)
    for col, label in zip(h, headers):
        col.markdown(f"<div class='tbl-header'>{label}</div>", unsafe_allow_html=True)

    # ── Baris data ──
    for i, (idx, row) in enumerate(df_page.iterrows()):
        dok_id   = str(row.get('dokumen_id', idx))
        nama     = str(row.get('nama_regulasi', ''))
        kat_id   = str(row.get('kategori_id', ''))
        kat_nama = kat_map.get(kat_id, kat_id)
        tgl_t    = str(row.get('tanggal_terbit', ''))
        status   = str(row.get('status', '')).lower()
        link     = str(row.get('google_drive_link', ''))

        # Badge status
        badge_map = {
            'aktif':       ('badge-aktif',    '✓ Aktif'),
            'draft':       ('badge-draft',    '✎ Draft'),
            'kadaluarsa':  ('badge-expired',  '✕ Kadaluarsa'),
            'expired':     ('badge-expired',  '✕ Expired'),
            'tidak aktif': ('badge-nonaktif', '○ Nonaktif'),
        }
        badge_cls, badge_lbl = badge_map.get(status, ('badge-nonaktif', status.capitalize()))
        row_bg = "background:#fafafa;border-radius:6px;" if i % 2 == 0 else ""

        c = st.columns(COL)
        c[0].markdown(
            f"<div class='tbl-row tbl-kat' style='{row_bg}padding-left:8px'>{kat_nama}</div>",
            unsafe_allow_html=True)
        c[1].markdown(
            f"<div class='tbl-row tbl-nama' style='{row_bg}'>{nama}</div>",
            unsafe_allow_html=True)

        if show_tgl_terbit:
            c[2].markdown(
                f"<div class='tbl-row tbl-tgl' style='{row_bg}'>{tgl_t}</div>",
                unsafe_allow_html=True)
            c[3].markdown(
                f"<div class='tbl-row' style='{row_bg}'>"
                f"<span class='badge {badge_cls}'>{badge_lbl}</span></div>",
                unsafe_allow_html=True)
            aksi_col = c[4]
        else:
            c[2].markdown(
                f"<div class='tbl-row' style='{row_bg}'>"
                f"<span class='badge {badge_cls}'>{badge_lbl}</span></div>",
                unsafe_allow_html=True)
            aksi_col = c[3]

        with aksi_col:
            b1, b2, b3 = st.columns(3)
            if link and link not in ('', 'nan', 'None'):
                b1.link_button("Lihat", url=link,
                               use_container_width=True, type="secondary")
            else:
                b1.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
            if can_edit:
                if b2.button("Edit", key=f"edit_{dok_id}_{idx}",
                             use_container_width=True):
                    st.session_state.reg_edit_id        = dok_id
                    st.session_state.reg_confirm_delete = None
            if can_delete:
                if b3.button("Hapus", key=f"hapus_{dok_id}_{idx}",
                             use_container_width=True):
                    st.session_state.reg_confirm_delete = dok_id
                    st.session_state.reg_edit_id        = None

        # Form edit / hapus inline
        if st.session_state.reg_edit_id == dok_id:
            _form_edit(dm, row, dok_id, current_user, ctx="main")
        if st.session_state.reg_confirm_delete == dok_id:
            _form_hapus(dm, row, dok_id, ctx="main")

    # ── Navigasi halaman ──
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        nav_cols = st.columns([1, 1, 3, 1, 1])
        with nav_cols[0]:
            if st.button("⏮ Pertama", key=f"pg_first_{page_key}",
                         disabled=(current_page == 1), use_container_width=True):
                st.session_state[pg_key] = 1; st.rerun()
        with nav_cols[1]:
            if st.button("◀ Prev", key=f"pg_prev_{page_key}",
                         disabled=(current_page == 1), use_container_width=True):
                st.session_state[pg_key] = current_page - 1; st.rerun()
        with nav_cols[2]:
            st.markdown(
                f"<div style='text-align:center;padding:8px 0;font-size:13px;color:#555'>"
                f"Halaman <b>{current_page}</b> dari <b>{total_pages}</b></div>",
                unsafe_allow_html=True)
        with nav_cols[3]:
            if st.button("Next ▶", key=f"pg_next_{page_key}",
                         disabled=(current_page == total_pages), use_container_width=True):
                st.session_state[pg_key] = current_page + 1; st.rerun()
        with nav_cols[4]:
            if st.button("Terakhir ⏭", key=f"pg_last_{page_key}",
                         disabled=(current_page == total_pages), use_container_width=True):
                st.session_state[pg_key] = total_pages; st.rerun()


def _form_edit(dm, row, dok_id, current_user, ctx=""):
    from dateutil.relativedelta import relativedelta

    masa_berlaku_opts = {
        "1 Tahun":   1,
        "2 Tahun":   2,
        "3 Tahun":   3,
        "5 Tahun":   5,
        "Selamanya": 0,
        "Manual":   -1,
    }

    # Deteksi default masa berlaku dari data yang sudah ada
    def _detect_masa(tgl_t, tgl_k_str):
        """Coba detect masa berlaku dari selisih tgl terbit & kadaluarsa"""
        tgl_k = _parse_date(tgl_k_str)
        if not tgl_k:
            return "Selamanya"
        if not tgl_t:
            return "Manual"
        for label, years in [("1 Tahun",1),("2 Tahun",2),("3 Tahun",3),("5 Tahun",5)]:
            if tgl_t + relativedelta(years=years) == tgl_k:
                return label
        return "Manual"

    tgl_t_current = _parse_date(str(row.get('tanggal_terbit', '')))
    tgl_k_current_str = str(row.get('tanggal_kadaluarsa', ''))
    default_masa = _detect_masa(tgl_t_current, tgl_k_current_str)

    with st.container():
        st.markdown("##### Edit Dokumen")
        col1, col2 = st.columns(2)
        with col1:
            nama_e  = st.text_input("Nama Regulasi",
                                     value=str(row.get('nama_regulasi', '')),
                                     key=f"e_nama_{dok_id}_{ctx}")

            # Tanggal terbit: input teks dd/mm/yyyy
            tgl_t_str_default = tgl_t_current.strftime('%d/%m/%Y') if tgl_t_current else ''
            tgl_t_input = st.text_input("Tanggal Terbit (dd/mm/yyyy)",
                                         value=tgl_t_str_default,
                                         placeholder="Contoh: 17/09/2025",
                                         key=f"e_tgl_t_{dok_id}_{ctx}")
            # Parse input user
            tgl_t_e = None
            tgl_t_err = ''
            if tgl_t_input.strip():
                try:
                    from datetime import datetime as _dt
                    tgl_t_e = _dt.strptime(tgl_t_input.strip(), '%d/%m/%Y').date()
                except ValueError:
                    tgl_t_err = "⚠️ Format tanggal salah, gunakan dd/mm/yyyy"
            if tgl_t_err:
                st.caption(tgl_t_err)

            # Masa berlaku
            masa_list = list(masa_berlaku_opts.keys())
            masa_idx  = masa_list.index(default_masa) if default_masa in masa_list else 0
            masa_e    = st.selectbox("Masa Berlaku", masa_list, index=masa_idx,
                                      key=f"e_masa_{dok_id}_{ctx}")
            masa_val  = masa_berlaku_opts[masa_e]

            # Tanggal kadaluarsa
            if masa_val > 0 and tgl_t_e:
                tgl_k_e = tgl_t_e + relativedelta(years=masa_val)
                st.text_input("Tanggal Kadaluarsa (otomatis)",
                               value=tgl_k_e.strftime('%d/%m/%Y'),
                               disabled=True, key=f"e_tgl_k_auto_{dok_id}_{ctx}")
            elif masa_val > 0 and not tgl_t_e:
                tgl_k_e = _parse_date(tgl_k_current_str)
                st.caption("Isi Tanggal Terbit dulu untuk hitung otomatis")
            elif masa_val == 0:
                tgl_k_e = None
                st.text_input("Tanggal Kadaluarsa", value="Tidak kadaluarsa",
                               disabled=True, key=f"e_tgl_k_auto_{dok_id}_{ctx}")
            else:
                # Manual
                tgl_k_default = _parse_date(tgl_k_current_str)
                tgl_k_input = st.text_input("Tanggal Kadaluarsa (dd/mm/yyyy)",
                                             value=tgl_k_default.strftime('%d/%m/%Y') if tgl_k_default else '',
                                             placeholder="Contoh: 17/09/2030",
                                             key=f"e_tgl_k_manual_{dok_id}_{ctx}")
                tgl_k_e = None
                if tgl_k_input.strip():
                    try:
                        from datetime import datetime as _dt
                        tgl_k_e = _dt.strptime(tgl_k_input.strip(), '%d/%m/%Y').date()
                    except ValueError:
                        st.caption("⚠️ Format tanggal kadaluarsa salah")

        with col2:
            status_opts = ["Aktif", "Draft", "Kadaluarsa", "Tidak Aktif"]
            cur_st      = str(row.get('status', 'Aktif'))
            status_e    = st.selectbox("Status", status_opts,
                                        index=status_opts.index(cur_st) if cur_st in status_opts else 0,
                                        key=f"e_status_{dok_id}_{ctx}")
            link_e = st.text_input("Google Drive Link",
                                    value=str(row.get('google_drive_link', '')),
                                    key=f"e_link_{dok_id}_{ctx}")

        bc1, bc2 = st.columns([1, 1])
        if bc1.button("Simpan", type="primary", key=f"save_{dok_id}_{ctx}"):
            if tgl_t_err:
                st.error("Perbaiki format tanggal terbit dulu.")
                return
            updates = {
                'nama_regulasi':      nama_e.strip(),
                'tanggal_terbit':     tgl_t_e.strftime('%Y-%m-%d') if tgl_t_e else '',
                'tanggal_kadaluarsa': tgl_k_e.strftime('%Y-%m-%d') if tgl_k_e else '',
                'status':             status_e,
                'google_drive_link':  link_e.strip(),
                'updated_by':         current_user.get('user_id', '') if current_user else '',
                'updated_at':         datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            with st.spinner("Menyimpan..."):
                ok = dm.update_rekap_database(dok_id, updates)
            if ok:
                # Kalau status diubah ke Tidak Aktif → pindahkan file ke Dokumen_Nonaktif
                if status_e == 'Tidak Aktif':
                    drive_id = str(row.get('google_drive_id', '')).strip()
                    if drive_id and drive_id not in ('', 'nan', 'None'):
                        try:
                            nonaktif_folder = dm.get_or_create_nonaktif_folder()
                            if nonaktif_folder:
                                dm.move_file_to_folder(drive_id, nonaktif_folder)
                        except Exception:
                            pass
                st.success("Tersimpan!")
                st.session_state.reg_edit_id = None
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Gagal menyimpan.")
        if bc2.button("Batal", key=f"cancel_edit_{dok_id}_{ctx}"):
            st.session_state.reg_edit_id = None
            st.rerun()


def _form_hapus(dm, row, dok_id, ctx=""):
    with st.container():
        nama = str(row.get('nama_regulasi', dok_id))
        st.warning(f"Hapus **{nama}**? Dokumen akan dinonaktifkan (tidak dihapus permanen).")
        bc1, bc2 = st.columns([1, 1])
        if bc1.button("Ya, Nonaktifkan", type="primary", key=f"yes_hapus_{dok_id}_{ctx}"):
            with st.spinner("Memproses..."):
                ok = dm.update_rekap_database(dok_id, {'status': 'Tidak Aktif'})
            if ok:
                # Pindahkan file ke folder Dokumen_Nonaktif di Drive
                drive_id = str(row.get('google_drive_id', '')).strip()
                if drive_id and drive_id not in ('', 'nan', 'None'):
                    try:
                        nonaktif_folder = dm.get_or_create_nonaktif_folder()
                        if nonaktif_folder:
                            dm.move_file_to_folder(drive_id, nonaktif_folder)
                    except Exception:
                        pass  # Gagal pindah folder bukan halangan — status tetap tersimpan
                st.success("Dokumen dinonaktifkan dan dipindahkan ke folder Dokumen_Nonaktif.")
                st.session_state.reg_confirm_delete = None
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Gagal.")
        if bc2.button("Batal", key=f"no_hapus_{dok_id}_{ctx}"):
            st.session_state.reg_confirm_delete = None
            st.rerun()


# ============================================================
# TAB 2: UPLOAD
# ============================================================

def _tab_kadaluarsa(dm, auth, current_user):
    """Tab khusus kadaluarsa: mendekati (<=6 bln) dan sudah kadaluarsa"""
    from datetime import date as _date
    from dateutil.relativedelta import relativedelta

    can_edit   = auth.has_permission('regulasi', 'edit')
    can_delete = auth.has_permission('regulasi', 'hapus')

    with st.spinner("Memuat dokumen..."):
        docs   = dm.get_all_documents()
        df_kat = dm.get_master_data('kategori_id')
        df_bid = dm.get_master_data('bidang_id')
        df_unit= dm.get_master_data('unit_id')

    if not docs:
        st.info("Belum ada dokumen.")
        return

    df = pd.DataFrame(docs).fillna('')
    kat_map_full = _build_map(df_kat,  'kategori_id', 'nama_kategori')
    bid_map      = _build_map(df_bid,  'bidang_id',   'nama_bidang')
    unit_map     = _build_map(df_unit, 'unit_id',      'nama_unit')

    # Exclude kategori yang sudah punya menu sendiri (sama seperti tab Daftar)
    exclude_ids = set()
    for kid, kname in kat_map_full.items():
        for kw in _EXCLUDE_KAT:
            if kw.lower() in kname.lower():
                exclude_ids.add(str(kid))
                break
    if exclude_ids and 'kategori_id' in df.columns:
        df = df[~df['kategori_id'].astype(str).isin(exclude_ids)]
    kat_map = {k: v for k, v in kat_map_full.items() if str(k) not in exclude_ids}

    today     = _date.today()
    batas_dekat = today + relativedelta(months=6)

    # Klasifikasikan berdasarkan tanggal_kadaluarsa
    rows_expired = []
    rows_dekat   = []

    # Juga masukkan yang status sudah 'kadaluarsa' meski tanggal tidak ada
    for _, row in df.iterrows():
        status = str(row.get('status', '')).lower()
        tgl_k_str = str(row.get('tanggal_kadaluarsa', '')).strip()
        tgl_k = _parse_date(tgl_k_str)

        if tgl_k:
            if tgl_k < today:
                rows_expired.append(row)
            elif tgl_k <= batas_dekat:
                rows_dekat.append(row)
        elif status in ('kadaluarsa', 'expired'):
            rows_expired.append(row)

    df_expired = pd.DataFrame(rows_expired) if rows_expired else pd.DataFrame()
    df_dekat   = pd.DataFrame(rows_dekat)   if rows_dekat   else pd.DataFrame()

    # Statistik ringkas
    c1, c2 = st.columns(2)
    c1.metric("⏳ Mendekati Kadaluarsa", len(df_dekat),
              help="Kadaluarsa dalam 6 bulan ke depan")
    c2.metric("❌ Sudah Kadaluarsa", len(df_expired))

    st.markdown("")

    # ---- Subtabel 1: Mendekati Kadaluarsa ----
    st.markdown("""
        <div style='background:#fff3cd;border-left:4px solid #ffc107;padding:10px 16px;border-radius:4px;margin-bottom:8px'>
            <b>⏳ Mendekati Kadaluarsa</b>
            <span style='font-size:12px;color:#666;margin-left:8px'>Masa berlaku habis dalam 6 bulan ke depan</span>
        </div>
    """, unsafe_allow_html=True)

    if df_dekat.empty:
        st.success("Tidak ada dokumen yang mendekati kadaluarsa.")
    else:
        _render_kadaluarsa_table(df_dekat, dm, current_user,
                                  kat_map, bid_map, unit_map,
                                  can_edit, can_delete, today, prefix="dekat")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Subtabel 2: Sudah Kadaluarsa ----
    st.markdown("""
        <div style='background:#f8d7da;border-left:4px solid #dc3545;padding:10px 16px;border-radius:4px;margin-bottom:8px'>
            <b>❌ Sudah Kadaluarsa</b>
            <span style='font-size:12px;color:#666;margin-left:8px'>Tanggal kadaluarsa sudah terlewat</span>
        </div>
    """, unsafe_allow_html=True)

    if df_expired.empty:
        st.success("Tidak ada dokumen yang kadaluarsa.")
    else:
        _render_kadaluarsa_table(df_expired, dm, current_user,
                                  kat_map, bid_map, unit_map,
                                  can_edit, can_delete, today, prefix="expired")


def _render_kadaluarsa_table(df, dm, current_user, kat_map, bid_map, unit_map,
                               can_edit, can_delete, today, prefix=""):
    """Render tabel kadaluarsa dengan kolom tambahan sisa hari"""
    from datetime import date as _date

    # ===== PAGINATION =====
    PAGE_SIZE = 25
    total_rows  = len(df)
    total_pages = max(1, -(-total_rows // PAGE_SIZE))
    pg_key  = f"_page_kal_{prefix}"
    if pg_key not in st.session_state:
        st.session_state[pg_key] = 1
    if st.session_state[pg_key] > total_pages:
        st.session_state[pg_key] = 1
    current_page = st.session_state[pg_key]
    start_idx    = (current_page - 1) * PAGE_SIZE
    end_idx      = min(start_idx + PAGE_SIZE, total_rows)
    df_page      = df.iloc[start_idx:end_idx]

    st.markdown(
        f"<div style='font-size:12px;color:#888;margin-bottom:6px'>"
        f"Menampilkan <b>{start_idx+1}–{end_idx}</b> dari <b>{total_rows}</b> dokumen"
        f"</div>",
        unsafe_allow_html=True,
    )

    h = st.columns([4, 2, 2, 2, 2, 3])
    for col, label in zip(h, ["Nama Dokumen", "Kategori", "Tgl Terbit", "Tgl Kadaluarsa", "Sisa / Lewat", "Aksi"]):
        col.markdown(f"<small><b>{label}</b></small>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

    for idx, row in df_page.iterrows():
        dok_id   = str(row.get('dokumen_id', idx))
        nama     = str(row.get('nama_regulasi', ''))
        kat_id   = str(row.get('kategori_id', ''))
        kat_nama = kat_map.get(kat_id, kat_id)
        tgl_t    = str(row.get('tanggal_terbit', ''))
        tgl_k_str= str(row.get('tanggal_kadaluarsa', ''))
        tgl_k    = _parse_date(tgl_k_str)
        link     = str(row.get('google_drive_link', ''))

        # Hitung sisa / lewat
        if tgl_k:
            delta = (tgl_k - today).days
            if delta < 0:
                sisa_html = f'<span style="color:red;font-size:12px;font-weight:600">Lewat {abs(delta)} hari</span>'
            elif delta == 0:
                sisa_html = '<span style="color:red;font-size:12px;font-weight:600">Hari ini!</span>'
            elif delta <= 30:
                sisa_html = f'<span style="color:red;font-size:12px">{delta} hari lagi</span>'
            elif delta <= 90:
                sisa_html = f'<span style="color:orange;font-size:12px">{delta} hari lagi</span>'
            else:
                sisa_html = f'<span style="color:#b8860b;font-size:12px">{delta} hari lagi</span>'
        else:
            sisa_html = '<span style="color:gray;font-size:12px">-</span>'

        c = st.columns([4, 2, 2, 2, 2, 3])
        c[0].markdown(f'<div style="font-size:13px;line-height:1.3">{nama}</div>', unsafe_allow_html=True)
        c[1].markdown(f'<small>{kat_nama}</small>', unsafe_allow_html=True)
        c[2].markdown(f'<small>{tgl_t}</small>', unsafe_allow_html=True)
        c[3].markdown(f'<small>{tgl_k_str}</small>', unsafe_allow_html=True)
        c[4].markdown(sisa_html, unsafe_allow_html=True)

        with c[5]:
            b1, b2, b3 = st.columns(3)
            if link and link not in ('', 'nan', 'None'):
                b1.link_button("Lihat", url=link, use_container_width=True)
            else:
                b1.markdown('<span style="font-size:11px;color:#ccc">-</span>', unsafe_allow_html=True)
            if can_edit:
                if b2.button("Edit", key=f"kal_edit_{prefix}_{dok_id}_{idx}", use_container_width=True):
                    st.session_state.reg_edit_id        = dok_id
                    st.session_state.reg_confirm_delete = None
            if can_delete:
                if b3.button("Hapus", key=f"kal_hapus_{prefix}_{dok_id}_{idx}", use_container_width=True):
                    st.session_state.reg_confirm_delete = dok_id
                    st.session_state.reg_edit_id        = None

        if st.session_state.get('reg_edit_id') == dok_id:
            _form_edit(dm, row, dok_id, current_user, ctx=f"kal_{prefix}")
        if st.session_state.get('reg_confirm_delete') == dok_id:
            _form_hapus(dm, row, dok_id, ctx=f"kal_{prefix}")

        st.markdown("<hr style='margin:2px 0'>", unsafe_allow_html=True)

    # ===== NAVIGASI HALAMAN =====
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        nav_cols = st.columns([1, 1, 3, 1, 1])
        with nav_cols[0]:
            if st.button("⏮ Pertama", key=f"kpg_first_{prefix}",
                         disabled=(current_page == 1), use_container_width=True):
                st.session_state[pg_key] = 1; st.rerun()
        with nav_cols[1]:
            if st.button("◀ Prev", key=f"kpg_prev_{prefix}",
                         disabled=(current_page == 1), use_container_width=True):
                st.session_state[pg_key] = current_page - 1; st.rerun()
        with nav_cols[2]:
            st.markdown(
                f"<div style='text-align:center;padding:6px 0;font-size:13px'>"
                f"Halaman <b>{current_page}</b> dari <b>{total_pages}</b></div>",
                unsafe_allow_html=True,
            )
        with nav_cols[3]:
            if st.button("Next ▶", key=f"kpg_next_{prefix}",
                         disabled=(current_page == total_pages), use_container_width=True):
                st.session_state[pg_key] = current_page + 1; st.rerun()
        with nav_cols[4]:
            if st.button("Terakhir ⏭", key=f"kpg_last_{prefix}",
                         disabled=(current_page == total_pages), use_container_width=True):
                st.session_state[pg_key] = total_pages; st.rerun()


def _tab_upload(dm, current_user):
    # Version counter untuk reset form
    if 'upload_version' not in st.session_state:
        st.session_state.upload_version = 0
    v = st.session_state.upload_version
    st.subheader("Upload Dokumen Baru")

    with st.spinner("Memuat master data..."):
        df_kat  = dm.get_master_data('kategori_id')
        df_bid  = dm.get_master_data('bidang_id')
        df_unit = dm.get_master_data('unit_id')
        df_sub  = dm.get_master_data('subkategori_id')

    if df_kat.empty:
        st.error("Tidak dapat memuat data kategori.")
        return

    def aktif(df):
        return df[df['status'].str.lower() == 'aktif'] if 'status' in df.columns else df

    df_kat  = aktif(df_kat)
    df_bid  = aktif(df_bid)
    df_unit = aktif(df_unit)
    df_sub  = aktif(df_sub)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Informasi Dokumen**")

        # Upload file dulu supaya nama bisa dipakai sebagai default nama regulasi
        uploaded_file_early = st.file_uploader(
            "Upload File (PDF/Word)",
            type=['pdf', 'doc', 'docx'],
            key=f"up_file_{v}"
        )

        # Nama otomatis dari nama file, bisa diedit manual
        nama_default = ""
        if uploaded_file_early:
            import os as _os
            nama_default, _ = _os.path.splitext(uploaded_file_early.name)
            nama_default = nama_default.strip()

        nama   = st.text_input("Nama Regulasi *",
                                value=nama_default,
                                placeholder="Otomatis dari nama file, atau isi manual",
                                key=f"up_nama_{v}")
        tgl_t_input = st.text_input("Tanggal Terbit * (dd/mm/yyyy)",
                                     value=date.today().strftime('%d/%m/%Y'),
                                     placeholder="Contoh: 21/05/2021",
                                     key=f"up_tgl_t_{v}")
        tgl_t = None
        tgl_t_err = ''
        if tgl_t_input.strip():
            try:
                from datetime import datetime as _dt2
                tgl_t = _dt2.strptime(tgl_t_input.strip(), '%d/%m/%Y').date()
            except ValueError:
                tgl_t_err = "⚠️ Format tanggal salah, gunakan dd/mm/yyyy"
        if tgl_t_err:
            st.caption(tgl_t_err)

        from dateutil.relativedelta import relativedelta
        masa_berlaku_opts = {
            "1 Tahun":    1,
            "2 Tahun":    2,
            "3 Tahun":    3,
            "5 Tahun":    5,
            "Selamanya":  0,
            "Manual":    -1,
        }
        masa = st.selectbox("Masa Berlaku", list(masa_berlaku_opts.keys()), key=f"up_masa_{v}")
        masa_val = masa_berlaku_opts[masa]

        if masa_val > 0:
            if tgl_t:
                tgl_k = tgl_t + relativedelta(years=masa_val)
                st.text_input("Tanggal Kadaluarsa (otomatis)", value=tgl_k.strftime('%d/%m/%Y'), disabled=True, key=f"up_tgl_k_show_{v}")
            else:
                tgl_k = None
                st.text_input("Tanggal Kadaluarsa (otomatis)", value="Isi tanggal terbit dulu", disabled=True, key=f"up_tgl_k_show_{v}")
        elif masa_val == 0:
            st.text_input("Tanggal Kadaluarsa", value="Tidak kadaluarsa", disabled=True, key=f"up_tgl_k_show_{v}")
            tgl_k = None
        else:
            tgl_k_input = st.text_input("Tanggal Kadaluarsa (dd/mm/yyyy)",
                                         placeholder="Contoh: 21/05/2030",
                                         key=f"up_tgl_k_manual_{v}")
            tgl_k = None
            if tgl_k_input.strip():
                try:
                    from datetime import datetime as _dt2
                    tgl_k = _dt2.strptime(tgl_k_input.strip(), '%d/%m/%Y').date()
                except ValueError:
                    st.caption("⚠️ Format tanggal kadaluarsa salah")

        status = st.selectbox("Status Dokumen", ["Aktif", "Draft"], key=f"up_status_dok_{v}")

    with col2:
        st.markdown("**Klasifikasi**")

        kat_opts = _build_select_opts(df_kat, 'nama_kategori', 'kategori_id')
        sel_kat_nama = st.selectbox("Kategori *", list(kat_opts.keys()), key=f"up_kat_{v}")
        sel_kat_id   = kat_opts.get(sel_kat_nama, '')

        df_bid_f = df_bid[df_bid['kategori_id'] == sel_kat_id] \
                   if sel_kat_id and 'kategori_id' in df_bid.columns else df_bid
        bid_opts = {"-- Tidak Ada --": ""}
        bid_opts.update(_build_select_opts(df_bid_f, 'nama_bidang', 'bidang_id'))
        sel_bid_nama = st.selectbox("Bidang", list(bid_opts.keys()), key=f"up_bid_{v}")
        sel_bid_id   = bid_opts.get(sel_bid_nama, '')

        df_unit_f = df_unit[df_unit['bidang_id'] == sel_bid_id] \
                    if sel_bid_id and 'bidang_id' in df_unit.columns else pd.DataFrame()
        unit_opts = {"-- Tidak Ada --": ""}
        unit_opts.update(_build_select_opts(df_unit_f, 'nama_unit', 'unit_id'))
        sel_unit_nama = st.selectbox("Unit", list(unit_opts.keys()), key=f"up_unit_{v}")
        sel_unit_id   = unit_opts.get(sel_unit_nama, '')

        df_sub_f = df_sub.copy() if not df_sub.empty else pd.DataFrame()
        if not df_sub_f.empty:
            if sel_kat_id and 'kategori_id' in df_sub_f.columns:
                df_sub_f = df_sub_f[df_sub_f['kategori_id'] == sel_kat_id]
            if sel_bid_id and 'bidang_id' in df_sub_f.columns:
                t = df_sub_f[df_sub_f['bidang_id'] == sel_bid_id]
                if not t.empty: df_sub_f = t
            if sel_unit_id and 'unit_id' in df_sub_f.columns:
                t = df_sub_f[df_sub_f['unit_id'] == sel_unit_id]
                if not t.empty: df_sub_f = t
        sub_opts = {"-- Tidak Ada --": ""}
        sub_opts.update(_build_select_opts(df_sub_f, 'nama_subkategori', 'subkategori_id'))
        sel_sub_nama = st.selectbox("Subkategori", list(sub_opts.keys()), key=f"up_sub_{v}")
        sel_sub_id   = sub_opts.get(sel_sub_nama, '')

    st.markdown("")
    st.markdown("**Atau masukkan Google Drive Link**")
    manual_link = st.text_input("",
                                 placeholder="https://drive.google.com/...",
                                 label_visibility="collapsed",
                                 key=f"up_link_{v}")
    uploaded_file = uploaded_file_early

    st.markdown("")
    if st.button("Simpan Dokumen", type="primary", key="btn_simpan_doc"):
        errors = []
        if not nama.strip():  errors.append("Nama Regulasi wajib diisi")
        if not sel_kat_id:    errors.append("Kategori wajib dipilih")
        if not uploaded_file and not manual_link.strip():
            errors.append("File atau Link Google Drive wajib diisi")

        for err in errors:
            st.error(err)
        if errors:
            return

        drive_link = manual_link.strip()
        drive_id   = ''

        if uploaded_file and not drive_link:
            with st.spinner("Mengupload file ke Google Drive..."):
                try:
                    target = _get_target_folder(dm, df_kat, df_bid, df_unit, df_sub,
                                                 sel_kat_id, sel_bid_id, sel_unit_id, sel_sub_id)
                    result = dm.upload_file_to_drive(
                        file_content=uploaded_file.read(),
                        file_name=uploaded_file.name,
                        mime_type=uploaded_file.type or 'application/octet-stream',
                        folder_id=target
                    )
                    if result:
                        drive_id   = result.get('id', '')
                        drive_link = result.get('link', '')
                        st.success(f"File berhasil diupload: {uploaded_file.name}")
                    else:
                        st.error("Gagal mengupload file ke Google Drive.")
                        return
                except Exception as e:
                    st.error(f"Error upload: {str(e)}")
                    return

        data = {
            'nomor_regulasi':     '',
            'nama_regulasi':      nama.strip(),
            'kategori_id':        sel_kat_id,
            'bidang_id':          sel_bid_id,
            'unit_id':            sel_unit_id,
            'subkategori_id':     sel_sub_id,
            'tanggal_terbit':     tgl_t.strftime('%Y-%m-%d') if tgl_t else '',
            'tanggal_kadaluarsa': tgl_k.strftime('%Y-%m-%d') if tgl_k else '',
            'google_drive_id':    drive_id,
            'google_drive_link':  drive_link,
            'status':             status,
            'created_by':         current_user.get('user_id', '') if current_user else '',
        }

        with st.spinner("Menyimpan ke database..."):
            success = dm.log_to_sheets(data)

        if success:
            st.success(f"Dokumen '{nama}' berhasil disimpan!")
            st.balloons()
            st.cache_data.clear()
            # Reset form: increment version → semua widget key berubah → fresh
            st.session_state.upload_version = st.session_state.get('upload_version', 0) + 1
            import time; time.sleep(1)
            st.rerun()
        else:
            st.error("Gagal menyimpan ke database.")


# ============================================================
# HELPERS
# ============================================================

def _build_map(df, id_col, name_col):
    if df is None or df.empty or id_col not in df.columns or name_col not in df.columns:
        return {}
    return dict(zip(df[id_col].astype(str), df[name_col].astype(str)))


def _reverse_map(d, value):
    if not value or value == 'Semua':
        return None
    for k, v in d.items():
        if v == value:
            return k
    return None


def _build_select_opts(df, name_col, id_col):
    if df is None or df.empty or name_col not in df.columns or id_col not in df.columns:
        return {}
    return dict(zip(df[name_col].astype(str), df[id_col].astype(str)))


def _parse_date(s):
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d-%b-%Y', '%d %b %Y'):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except:
            pass
    return date.today()


def _get_target_folder(dm, df_kat, df_bid, df_unit, df_sub,
                        kat_id, bid_id, unit_id, sub_id):
    """
    Cari / buat folder tujuan upload secara dinamis berdasarkan nama.
    Hierarki: root → Kategori → Bidang → Unit → Subkategori
    Jika folder belum ada, otomatis dibuat.
    """
    def _get_name(df, id_col, id_val, name_col):
        if not id_val or df.empty or id_col not in df.columns:
            return None
        row = df[df[id_col] == id_val]
        if row.empty: return None
        val = str(row.iloc[0].get(name_col, '')).strip()
        return val if val and val not in ('nan', 'None', '') else None

    root = dm.DRIVE_FOLDER_ID
    current_parent = root

    # Level 1: Kategori
    kat_name = _get_name(df_kat, 'kategori_id', kat_id, 'nama_kategori')
    if kat_name:
        fid = dm.search_folder(kat_name, current_parent)
        if not fid:
            fid = dm.create_folder(kat_name, current_parent)
        if fid:
            current_parent = fid

    # Level 2: Bidang
    bid_name = _get_name(df_bid, 'bidang_id', bid_id, 'nama_bidang')
    if bid_name:
        fid = dm.search_folder(bid_name, current_parent)
        if not fid:
            fid = dm.create_folder(bid_name, current_parent)
        if fid:
            current_parent = fid

    # Level 3: Unit
    unit_name = _get_name(df_unit, 'unit_id', unit_id, 'nama_unit')
    if unit_name:
        fid = dm.search_folder(unit_name, current_parent)
        if not fid:
            fid = dm.create_folder(unit_name, current_parent)
        if fid:
            current_parent = fid

    # Level 4: Subkategori
    sub_name = _get_name(df_sub, 'subkategori_id', sub_id, 'nama_subkategori')
    if sub_name:
        fid = dm.search_folder(sub_name, current_parent)
        if not fid:
            fid = dm.create_folder(sub_name, current_parent)
        if fid:
            current_parent = fid

    return current_parent


# ============================================================
# TAB 3: IMPORT DARI GOOGLE DRIVE
# ============================================================


def _tab_import_drive(dm, current_user):
    st.subheader("Import Dokumen dari Google Drive")
    st.info(
        "Scan file yang sudah ada di folder Google Drive, "
        "lalu daftarkan ke database tanpa perlu upload ulang."
    )

    with st.spinner("Memuat master data..."):
        df_kat  = dm.get_master_data('kategori_id')
        df_bid  = dm.get_master_data('bidang_id')
        df_unit = dm.get_master_data('unit_id')
        df_sub  = dm.get_master_data('subkategori_id')

    def aktif(df):
        return df[df['status'].str.lower() == 'aktif'] if 'status' in df.columns else df

    df_kat  = aktif(df_kat)
    df_bid  = aktif(df_bid)
    df_unit = aktif(df_unit)
    df_sub  = aktif(df_sub)

    kat_map  = _build_map(df_kat,  'kategori_id', 'nama_kategori')
    bid_map  = _build_map(df_bid,  'bidang_id',   'nama_bidang')

    # --------------------------------------------------------
    # Folder map: nama folder Drive -> (kategori_id, bidang_id)
    # --------------------------------------------------------
    FOLDER_KAT_MAP = {
        # Regulasi
        dm.DRIVE_FOLDER_ID: ("", ""),
    }
    # Build dari master data jika ada folder_id di sheet
    if not df_kat.empty and 'folder_id' in df_kat.columns:
        for _, row in df_kat.iterrows():
            fid = str(row.get('folder_id','')).strip()
            kid = str(row.get('kategori_id','')).strip()
            if fid and kid:
                FOLDER_KAT_MAP[fid] = (kid, "")

    if not df_bid.empty and 'folder_id' in df_bid.columns:
        for _, row in df_bid.iterrows():
            fid = str(row.get('folder_id','')).strip()
            kid = str(row.get('kategori_id','')).strip()
            bid = str(row.get('bidang_id','')).strip()
            if fid and kid:
                FOLDER_KAT_MAP[fid] = (kid, bid)

    # Daftar folder yang bisa discan
    ALL_FOLDERS = {
        "Semua Folder Sekaligus": "__ALL__",
        "--- Regulasi ---": None,
        "01. KEBIJAKAN":      "1RP3WkkQJq0l7a7R9swh1WoxsWxXVKwzt",
        "02. PEDOMAN/PANDUAN":"1Kb9eovI8etJoGEWvQVWXK9qal4Q-HJMx",
        "03. SPO":            "1CA5maktqBRRhn_7jM3CxK98EYVJ7P67M",
        "04. PPK":            "1bz4zzJ5GBhCJsK4_7B9OS1W2Isi5chGa",
        "05. PPF":            "1aFi0DrkYpmbujdUU9ziK1jinT3Gn-cyq",
        "06. PAK":            "1hs1v1m-ZyypZkmhLq1PT1CT3G-DZC73m",
        "07. PAKeb":          "1hTovIwZkGMfwPjU4ntMIjcUaCeeLHIIN",
        "08. Keputusan Komdik":"1K_9G4dDuZSMDqPz2aDyNsF4XJh5NFS2m",
        "--- Perijinan & PKS ---": None,
        "PKS / Perijinan":    dm.PKS_PERIJINAN_FOLDER_ID,
        "PKS / Klinis":       dm.PKS_KLINIS_FOLDER_ID,
        "PKS / Manajerial":   dm.PKS_MANAJERIAL_FOLDER_ID,
        "--- e-Library ---": None,
        "e-Library / PNPK":           dm.LIB_PNPK_FOLDER_ID,
        "e-Library / Clinical Pathway":dm.LIB_CLINICAL_FOLDER_ID,
        "e-Library / Lainnya":        dm.LIB_LAINNYA_FOLDER_ID,
        "--- Dokumen Lainnya ---": None,
        "Program Kerja":   dm.DOK_PROGJA_FOLDER_ID,
        "SPK":             dm.DOK_SPK_FOLDER_ID,
        "RKK":             dm.DOK_RKK_FOLDER_ID,
        "Notulen MM":      dm.DOK_NOTULEN_FOLDER_ID,
        "--- Atau masukkan manual ---": None,
        "Custom (masukkan ID/link)": "__CUSTOM__",
    }

    st.markdown("---")
    st.markdown("#### Langkah 1 — Pilih Folder yang Akan Discan")

    # Filter hanya pilihan yang punya value (bukan separator)
    valid_opts = [k for k, v in ALL_FOLDERS.items() if v is not None]
    sel_label  = st.selectbox("Pilih folder", valid_opts, key="import_folder_sel")
    sel_val    = ALL_FOLDERS.get(sel_label, "")

    custom_input = ""
    if sel_val == "__CUSTOM__":
        custom_input = st.text_input(
            "Folder ID atau Link Google Drive",
            placeholder="Paste ID atau link Drive...",
            key="import_custom_input"
        )

    # ============================================================
    # SUB-FOLDER SELECTOR (NEW FEATURE!)
    # ============================================================
    
    # Initialize session state untuk subfolders
    if 'subfolders' not in st.session_state:
        st.session_state.subfolders = []
    if 'show_subfolder_selector' not in st.session_state:
        st.session_state.show_subfolder_selector = False
    if 'selected_subfolder_ids' not in st.session_state:
        st.session_state.selected_subfolder_ids = []
    
    # Tentukan folder_id untuk detect sub-folder
    detect_folder_id = None
    if sel_val == "__CUSTOM__" and custom_input:
        detect_folder_id = _extract_folder_id(custom_input)
    elif sel_val and sel_val not in ("__ALL__", "__CUSTOM__"):
        detect_folder_id = sel_val
    
    # Button: Detect Sub-folders
    if detect_folder_id:
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("🔍 Detect Sub-folder", key="detect_subfolder_btn"):
                with st.spinner("Mencari sub-folder..."):
                    subfolders = _scan_subfolders(dm, detect_folder_id)
                    
                    if subfolders:
                        st.session_state.subfolders = subfolders
                        st.session_state.show_subfolder_selector = True
                        st.success(f"✅ Ditemukan {len(subfolders)} sub-folder dengan file!")
                        st.rerun()
                    else:
                        st.info("ℹ️ Tidak ada sub-folder, atau folder ini berisi file langsung.")
                        st.session_state.show_subfolder_selector = False
        
        with col2:
            if st.session_state.show_subfolder_selector:
                if st.button("❌ Reset", key="reset_subfolder"):
                    st.session_state.show_subfolder_selector = False
                    st.session_state.subfolders = []
                    st.session_state.selected_subfolder_ids = []
                    st.rerun()
    
    # ============================================================
    # SUB-FOLDER SELECTOR UI
    # ============================================================
    
    if st.session_state.show_subfolder_selector and st.session_state.subfolders:
        st.markdown("---")
        st.markdown("#### 📂 Pilih Sub-folder yang Akan Di-scan")
        
        subfolders = st.session_state.subfolders
        
        # Select All checkbox
        col_all, col_info = st.columns([1, 3])
        with col_all:
            select_all = st.checkbox("✅ Pilih Semua", value=True, key="subfolder_select_all")
        with col_info:
            total_files = sum(f['file_count'] for f in subfolders)
            st.info(f"📊 Total: {len(subfolders)} sub-folder, {total_files} file")
        
        st.markdown("")
        
        # Checkbox untuk setiap subfolder (2 kolom layout)
        selected_ids = []
        num_cols = 2
        cols = st.columns(num_cols)
        
        for i, subfolder in enumerate(subfolders):
            col_idx = i % num_cols
            with cols[col_idx]:
                checked = st.checkbox(
                    f"📁 **{subfolder['name']}** — {subfolder['file_count']} file",
                    value=select_all,
                    key=f"subfolder_check_{i}"
                )
                if checked:
                    selected_ids.append(subfolder['id'])
        
        st.session_state.selected_subfolder_ids = selected_ids
        
        st.markdown("---")
        if selected_ids:
            selected_count = len(selected_ids)
            selected_files = sum(f['file_count'] for f in subfolders if f['id'] in selected_ids)
            st.success(f"✅ **{selected_count} sub-folder dipilih** ({selected_files} file akan di-scan)")
        else:
            st.warning("⚠️ Pilih minimal 1 sub-folder untuk di-scan!")

    # ============================================================
    # SCAN FILES
    # ============================================================
    
    include_sub = st.checkbox("Scan subfolder juga (rekursif)", value=False, key="import_recursive")
    
    # Dynamic button label
    scan_button_label = "🔍 Scan File di Folder"
    if st.session_state.show_subfolder_selector and st.session_state.selected_subfolder_ids:
        num_selected = len(st.session_state.selected_subfolder_ids)
        scan_button_label = f"🔍 Scan {num_selected} Sub-folder yang Dipilih"

    # Tombol scan
    if st.button(scan_button_label, type="primary", key="btn_scan_drive"):
        st.session_state['import_files'] = None
        st.session_state['import_scan_meta'] = {}

        # Determine folders to scan
        folders_to_scan = []
        folder_labels = {}
        
        # Case 1: Sub-folder selector active
        if st.session_state.show_subfolder_selector and st.session_state.selected_subfolder_ids:
            for subfolder_id in st.session_state.selected_subfolder_ids:
                folders_to_scan.append(subfolder_id)
                # Find folder name
                for sf in st.session_state.subfolders:
                    if sf['id'] == subfolder_id:
                        folder_labels[subfolder_id] = sf['name']
                        break
        
        # Case 2: Scan all folders
        elif sel_val == "__ALL__":
            folder_targets = {k: v for k, v in ALL_FOLDERS.items()
                              if v and v not in ("__ALL__", "__CUSTOM__")
                              and not k.startswith("---")}
            
            for fname, fid in folder_targets.items():
                folders_to_scan.append(fid)
                folder_labels[fid] = fname
        
        # Case 3: Custom folder
        elif sel_val == "__CUSTOM__":
            fid = _extract_folder_id(custom_input)
            if not fid:
                st.error("❌ Format folder tidak valid.")
                return
            folders_to_scan.append(fid)
            folder_labels[fid] = "Custom"
        
        # Case 4: Single folder selection
        else:
            fid = sel_val
            folders_to_scan.append(fid)
            folder_labels[fid] = sel_label
        
        # Scan files dari folder-folder yang dipilih
        if not folders_to_scan:
            st.error("❌ Tidak ada folder yang akan di-scan!")
            return
        
        all_files = []
        progress_bar = st.progress(0)
        
        for idx, folder_id in enumerate(folders_to_scan):
            folder_name = folder_labels.get(folder_id, "Folder")
            
            with st.spinner(f"Scanning {folder_name}..."):
                files = _scan_drive_folder(dm, folder_id, recursive=include_sub)
                kid, bid = FOLDER_KAT_MAP.get(folder_id, ("", ""))
                
                # Tag files dengan folder info
                for f in files:
                    f['_kat_id'] = kid
                    f['_bid_id'] = bid
                    f['_folder_label'] = folder_name
                    f['_folder_id'] = folder_id
                
                all_files.extend(files)
            
            progress_bar.progress((idx + 1) / len(folders_to_scan))
        
        progress_bar.empty()
        st.session_state['import_files'] = all_files

    # ---- Tampilkan hasil scan ----
    files = st.session_state.get('import_files')
    if files is None:
        return
    if not files:
        st.warning("Tidak ada file ditemukan.")
        return

    # Cek yang sudah terdaftar (berdasarkan Drive ID DAN Nama File)
    existing_docs = dm.get_all_documents() or []
    registered_ids = set()
    registered_names = set()
    if existing_docs:
        df_ex = pd.DataFrame(existing_docs)
        if 'google_drive_id' in df_ex.columns:
            registered_ids = set(df_ex['google_drive_id'].astype(str).str.strip())
        if 'nama_regulasi' in df_ex.columns:
            # Normalize nama: lowercase, strip, hilangkan ekstensi
            registered_names = set(
                str(n).lower().strip().replace('.pdf','').replace('.docx','').replace('.xlsx','')
                for n in df_ex['nama_regulasi'] if pd.notna(n)
            )

    # File dianggap sudah terdaftar jika Drive ID ATAU Nama File match
    new_files  = []
    done_files = []
    for f in files:
        file_id = f['id']
        file_name = str(f.get('name', '')).lower().strip().replace('.pdf','').replace('.docx','').replace('.xlsx','')
        
        if file_id in registered_ids:
            done_files.append(f)
            f['_duplicate_reason'] = 'Drive ID sudah terdaftar'
        elif file_name in registered_names:
            done_files.append(f)
            f['_duplicate_reason'] = 'Nama file sudah terdaftar'
        else:
            new_files.append(f)

    st.markdown(f"**Ditemukan {len(files)} file** — "
                f":green[{len(new_files)} belum terdaftar] | "
                f":orange[{len(done_files)} sudah terdaftar]")
    
    # Tampilkan file yang sudah terdaftar (jika ada)
    if done_files:
        with st.expander(f"🟠 File yang Sudah Terdaftar ({len(done_files)} file)", expanded=False):
            st.info("File-file ini **tidak akan didaftarkan ulang** untuk menghindari duplikasi.")
            for f in done_files:
                fname = f.get('name', '')
                reason = f.get('_duplicate_reason', 'Sudah terdaftar')
                st.markdown(f"- **{fname}** — _{reason}_")
    
    st.markdown("---")
    st.markdown("#### Langkah 2 — Pilih Klasifikasi & File")

    # Grupkan per folder_label untuk tampilan
    from collections import defaultdict
    groups = defaultdict(list)
    for f in new_files:
        groups[f.get('_folder_label', 'Lainnya')].append(f)

    selected_files = []
    kat_opts = _build_select_opts(df_kat, 'nama_kategori', 'kategori_id')

    for grp_label, grp_files in groups.items():
        with st.expander(f"📂 {grp_label} ({len(grp_files)} file)", expanded=True):
            # Klasifikasi per grup
            auto_kat = grp_files[0].get('_kat_id', '') if grp_files else ''
            auto_bid = grp_files[0].get('_bid_id', '') if grp_files else ''

            g_key = grp_label.replace(" ", "_").replace("/","_")
            c1, c2, c3, c4 = st.columns(4)

            # Default ke auto-detected
            kat_keys  = list(kat_opts.keys())
            kat_vals  = list(kat_opts.values())
            
            # Filter out empty options
            valid_kat_opts = {k: v for k, v in kat_opts.items() if k and v}
            if not valid_kat_opts:
                st.error("❌ Tidak ada kategori tersedia. Tambahkan kategori di Master Data terlebih dahulu.")
                return
            
            kat_keys = list(valid_kat_opts.keys())
            kat_vals = list(valid_kat_opts.values())
            
            def_kat_i = kat_vals.index(auto_kat) if auto_kat in kat_vals else 0
            sel_kat_n = c1.selectbox("Kategori *", kat_keys, index=def_kat_i, key=f"gkat_{g_key}")
            sel_kat_id = valid_kat_opts.get(sel_kat_n, '')

            df_bid_f = df_bid[df_bid['kategori_id'] == sel_kat_id] \
                       if sel_kat_id and 'kategori_id' in df_bid.columns else df_bid
            bid_opts = {"-- Tidak Ada --": ""}
            bid_opts.update(_build_select_opts(df_bid_f, 'nama_bidang', 'bidang_id'))
            bid_keys = list(bid_opts.keys())
            bid_vals = list(bid_opts.values())
            def_bid_i = bid_vals.index(auto_bid) if auto_bid in bid_vals else 0
            sel_bid_n  = c2.selectbox("Bidang", bid_keys, index=def_bid_i, key=f"gbid_{g_key}")
            sel_bid_id = bid_opts.get(sel_bid_n, '')

            df_unit_f = df_unit[df_unit['bidang_id'] == sel_bid_id] \
                        if sel_bid_id and 'bidang_id' in df_unit.columns else pd.DataFrame()
            unit_opts = {"-- Tidak Ada --": ""}
            unit_opts.update(_build_select_opts(df_unit_f, 'nama_unit', 'unit_id'))
            sel_unit_n  = c3.selectbox("Unit", list(unit_opts.keys()), key=f"gunit_{g_key}")
            sel_unit_id = unit_opts.get(sel_unit_n, '')

            tgl_grp = c4.date_input("Tgl Terbit", value=date.today(), key=f"gtgl_{g_key}")

            st.markdown("")

            # Checkbox select all
            col_all, _ = st.columns([1, 8])
            select_all = col_all.checkbox("Pilih Semua", value=True, key=f"gall_{g_key}")

            # Daftar file
            for i, f in enumerate(grp_files):
                fname = f.get('name', '')
                flink = f.get('webViewLink', '')
                c_chk, c_name = st.columns([1, 10])
                with c_chk:
                    checked = st.checkbox("", value=select_all, key=f"chk_{g_key}_{i}")
                with c_name:
                    if flink:
                        st.markdown(f"[{fname}]({flink})")
                    else:
                        st.write(fname)
                if checked:
                    selected_files.append({
                        'id': f['id'], 'name': fname, 'link': flink,
                        'kat_id': sel_kat_id, 'bid_id': sel_bid_id,
                        'unit_id': sel_unit_id, 'tgl': str(tgl_grp),
                    })

    st.markdown("---")
    st.markdown(f"**{len(selected_files)} file dipilih untuk didaftarkan.**")

    if not selected_files:
        st.info("Pilih minimal 1 file.")
        return
    
    # Validasi: Pastikan semua file punya kategori_id
    files_no_kat = [f for f in selected_files if not f.get('kat_id')]
    if files_no_kat:
        st.error(f"❌ **{len(files_no_kat)} file belum memiliki kategori!**")
        st.warning("Pastikan Anda sudah memilih kategori dari dropdown untuk semua file.")
        with st.expander("🔍 File yang belum punya kategori"):
            for f in files_no_kat:
                st.write(f"- {f['name']}")
        st.info("💡 **Cara fix:** Pilih kategori dari dropdown di atas, lalu checklist ulang file-nya.")
        return

    if st.button(f"Daftarkan {len(selected_files)} File ke Database",
                  type="primary", key="btn_import_confirm"):
        progress = st.progress(0)
        results  = []
        total    = len(selected_files)

        for i, f in enumerate(selected_files):
            nama_bersih = _clean_filename(f['name'])
            data = {
                'nomor_regulasi':     '',
                'nama_regulasi':      nama_bersih,
                'kategori_id':        f['kat_id'],
                'bidang_id':          f['bid_id'],
                'unit_id':            f['unit_id'],
                'subkategori_id':     '',
                'tanggal_terbit':     f['tgl'],
                'tanggal_kadaluarsa': '',
                'google_drive_id':    f['id'],
                'google_drive_link':  f['link'],
                'status':             'Aktif',
                'created_by':         current_user.get('user_id', '') if current_user else '',
            }
            
            # Debug: Log data untuk file pertama
            if i == 0:
                with st.expander("🔍 Debug: Data file pertama yang akan dikirim", expanded=False):
                    st.json({
                        'nama_regulasi': data['nama_regulasi'],
                        'kategori_id': data['kategori_id'],
                        'bidang_id': data['bidang_id'],
                        'unit_id': data['unit_id'],
                        'status': data['status']
                    })
            
            ok = dm.log_to_sheets(data)
            results.append({'Nama File': f['name'], 'Status': 'OK' if ok else 'GAGAL'})
            progress.progress((i + 1) / total)

        st.cache_data.clear()
        df_res = pd.DataFrame(results)
        n_ok  = len(df_res[df_res['Status'] == 'OK'])
        n_err = len(df_res[df_res['Status'] == 'GAGAL'])
        st.success(f"Selesai! {n_ok} file berhasil, {n_err} gagal.")
        if n_err:
            st.dataframe(df_res[df_res['Status'] == 'GAGAL'])
        st.session_state['import_files'] = None
        st.rerun()


def _extract_folder_id(text):
    """Ekstrak folder ID dari link Drive atau ID langsung."""
    if not text or not text.strip():
        return None
    text = text.strip()
    # Link format: .../folders/ID?... atau .../folders/ID
    if 'drive.google.com' in text:
        import re
        match = re.search(r'/folders/([a-zA-Z0-9_-]+)', text)
        if match:
            return match.group(1)
        return None
    # Anggap langsung ID jika tidak ada spasi dan panjang wajar
    if ' ' not in text and len(text) > 10:
        return text
    return None


def _scan_drive_folder(dm, folder_id, recursive=False):
    """
    Scan file di folder Google Drive.
    Support My Drive dan Shared Drive.
    Returns list of dicts: {id, name, webViewLink, mimeType}
    """
    if not dm.is_initialized():
        return []

    files = []
    try:
        query = (
            f"'{folder_id}' in parents "
            f"and mimeType != 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )

        # Params untuk support Shared Drive
        list_params = dict(
            q=query,
            fields="nextPageToken, files(id, name, webViewLink, mimeType, parents)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageSize=500,
        )

        # Pagination - ambil semua halaman
        while True:
            result = dm.drive_service.files().list(**list_params).execute()
            files.extend(result.get('files', []))
            next_token = result.get('nextPageToken')
            if not next_token:
                break
            list_params['pageToken'] = next_token

        # Jika rekursif, scan subfolder
        if recursive:
            sub_query = (
                f"'{folder_id}' in parents "
                f"and mimeType = 'application/vnd.google-apps.folder' "
                f"and trashed = false"
            )
            sub_result = dm.drive_service.files().list(
                q=sub_query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives",
            ).execute()
            for subfolder in sub_result.get('files', []):
                sub_files = _scan_drive_folder(dm, subfolder['id'], recursive=True)
                files.extend(sub_files)

    except Exception as e:
        st.error(f"Error scan folder {folder_id}: {str(e)}")

    return files


def _clean_filename(filename):
    """Bersihkan nama file: hilangkan ekstensi."""
    import os
    name, _ = os.path.splitext(filename)
    return name


# ============================================================
# SUB-FOLDER SELECTOR FUNCTIONS (NEW!)
# ============================================================

def _count_files_in_folder(dm, folder_id):
    """
    Count jumlah file (bukan folder) dalam folder.
    Returns: int (jumlah file)
    """
    if not dm.is_initialized():
        return 0
    
    try:
        query = (
            f"'{folder_id}' in parents "
            f"and mimeType != 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        
        result = dm.drive_service.files().list(
            q=query,
            fields="files(id)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageSize=1000
        ).execute()
        
        return len(result.get('files', []))
    except Exception as e:
        return 0


def _scan_subfolders(dm, parent_folder_id):
    """
    Scan sub-folder dalam parent folder.
    Returns: List of {id, name, file_count}
    """
    if not dm.is_initialized():
        return []
    
    try:
        query = (
            f"'{parent_folder_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        
        result = dm.drive_service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageSize=100
        ).execute()
        
        subfolders = []
        for folder in result.get('files', []):
            # Count files in each subfolder
            file_count = _count_files_in_folder(dm, folder['id'])
            
            if file_count > 0:  # Hanya tampilkan folder yang ada file-nya
                subfolders.append({
                    'id': folder['id'],
                    'name': folder['name'],
                    'file_count': file_count
                })
        
        # Sort by name
        subfolders.sort(key=lambda x: x['name'])
        return subfolders
        
    except Exception as e:
        st.error(f"❌ Error scanning subfolders: {str(e)}")
        return []