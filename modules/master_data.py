# modules/master_data.py
"""
Modul Master Data - AREG SOLO
Kelola Kategori, Bidang, Unit, Subkategori
"""

import streamlit as st
import pandas as pd
from utils.google_drive_manager import get_drive_manager
from utils.auth_manager import get_auth_manager


def show():
    dm  = get_drive_manager()
    auth = get_auth_manager(dm)
    current_user = auth.get_current_user()
    role = current_user.get('role', '') if current_user else ''

    st.title("Master Data")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["Kategori", "Bidang", "Unit", "Subkategori"])

    with tab1:
        _tab_kategori(dm)
    with tab2:
        _tab_bidang(dm)
    with tab3:
        _tab_unit(dm)
    with tab4:
        _tab_subkategori(dm)


# ========== HELPER ==========

def _render_table(df, hide_cols=None):
    """Tampilkan dataframe bersih"""
    if df.empty:
        st.info("Belum ada data.")
        return
    show_df = df.copy().fillna('')
    if hide_cols:
        show_df = show_df.drop(columns=[c for c in hide_cols if c in show_df.columns], errors='ignore')
    st.dataframe(show_df, use_container_width=True, hide_index=True)


def _status_badge(status):
    s = str(status).lower()
    if s == 'aktif':
        return "Aktif"
    return "Tidak Aktif"


# ========== TAB KATEGORI ==========

def _tab_kategori(dm):
    st.subheader("Kategori Regulasi")

    with st.spinner("Memuat..."):
        df      = dm.get_master_data('kategori_id')
        df_menu = dm.get_master_data('menu_id')

    col_tbl, col_form = st.columns([2, 1])

    with col_tbl:
        if not df.empty:
            aktif = len(df[df['status'].str.lower() == 'aktif']) if 'status' in df.columns else len(df)
            st.metric("Total Kategori Aktif", aktif)
            st.markdown("")
            _render_table(df)
        else:
            st.info("Belum ada data kategori.")

    with col_form:
        st.markdown("**Tambah Kategori Baru**")

        # Fix: pakai max+1 bukan len+1
        if not df.empty and 'kategori_id' in df.columns:
            nums = [int(v[3:]) for v in df['kategori_id'].astype(str)
                    if v.startswith('KAT') and v[3:].isdigit()]
            new_id = f"KAT{(max(nums)+1 if nums else 1):03d}"
        else:
            new_id = "KAT001"

        st.text_input("ID (otomatis)", value=new_id, disabled=True, key="kat_id_show")
        nama = st.text_input("Nama Kategori *", key="kat_nama",
                             placeholder="Contoh: KEBIJAKAN")
        kode = st.text_input("Kode *", key="kat_kode",
                             placeholder="Contoh: KP")

        # Fix: tambah dropdown Menu → isi menu_id
        menu_options = {"-- Pilih Menu --": ""}
        if not df_menu.empty and 'nama_menu' in df_menu.columns:
            for _, r in df_menu.iterrows():
                mid  = str(r.get('menu_id','')).strip()
                mnam = str(r.get('nama_menu','')).strip()
                if mid and mnam: menu_options[mnam] = mid
        sel_menu = st.selectbox("Menu *", list(menu_options.keys()), key="kat_menu")
        sel_menu_id = menu_options.get(sel_menu, '')

        folder_id = st.text_input("Google Drive Folder ID",
                                  key="kat_folder",
                                  placeholder="Opsional - ID folder di Drive")

        if st.button("Tambah Kategori", type="primary", key="btn_kat"):
            if not nama.strip() or not kode.strip():
                st.error("Nama dan Kode wajib diisi!")
            elif not sel_menu_id:
                st.error("Menu wajib dipilih!")
            else:
                data = {
                    'kategori_id':   new_id,
                    'nama_kategori': nama.strip().upper(),
                    'kode':          kode.strip().upper(),
                    'menu_id':       sel_menu_id,
                    'status':        'Aktif',
                    'folder_id':     folder_id.strip(),
                }
                with st.spinner("Menyimpan..."):
                    ok = dm.add_master_data('kategori_id', data)
                if ok:
                    st.success(f"Kategori '{nama}' berhasil ditambahkan!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Gagal menyimpan.")


# ========== TAB BIDANG ==========

def _tab_bidang(dm):
    st.subheader("Bidang")

    with st.spinner("Memuat..."):
        df     = dm.get_master_data('bidang_id')
        df_kat = dm.get_master_data('kategori_id')

    col_tbl, col_form = st.columns([2, 1])

    with col_tbl:
        if not df.empty:
            aktif = len(df[df['status'].str.lower() == 'aktif']) if 'status' in df.columns else len(df)
            st.metric("Total Bidang Aktif", aktif)
            st.markdown("")
            _render_table(df)
        else:
            st.info("Belum ada data bidang.")

    with col_form:
        st.markdown("**Tambah Bidang Baru**")

        if not df.empty and 'bidang_id' in df.columns:
            nums = [int(v[3:]) for v in df['bidang_id'].astype(str) if v.startswith('BID') and v[3:].isdigit()]
            new_id = f"BID{(max(nums)+1 if nums else 1):03d}"
        else:
            new_id = "BID001"

        st.text_input("ID (otomatis)", value=new_id, disabled=True, key="bid_id_show")
        nama = st.text_input("Nama Bidang *", key="bid_nama",
                             placeholder="Contoh: HRD")

        # Dropdown Kategori
        kat_options = {}
        if not df_kat.empty and 'nama_kategori' in df_kat.columns:
            df_kat_aktif = df_kat[df_kat['status'].str.lower() == 'aktif'] if 'status' in df_kat.columns else df_kat
            kat_options = dict(zip(df_kat_aktif['nama_kategori'], df_kat_aktif['kategori_id']))
        sel_kat = st.selectbox("Kategori *", list(kat_options.keys()) or ["(Kosong)"], key="bid_kat")
        sel_kat_id = kat_options.get(sel_kat, '')

        has_unit = st.checkbox("Punya Unit?", value=True, key="bid_has_unit")
        folder_id = st.text_input("Google Drive Folder ID", key="bid_folder",
                                  placeholder="Opsional")

        if st.button("Tambah Bidang", type="primary", key="btn_bid"):
            if not nama.strip() or not sel_kat_id:
                st.error("Nama dan Kategori wajib diisi!")
            else:
                data = {
                    'bidang_id':    new_id,
                    'nama_bidang':  nama.strip(),
                    'kategori_id':  sel_kat_id,
                    'has_unit':     'TRUE' if has_unit else 'FALSE',
                    'status':       'Aktif',
                    'folder_id':    folder_id.strip(),
                }
                with st.spinner("Menyimpan..."):
                    ok = dm.add_master_data('bidang_id', data)
                if ok:
                    st.success(f"Bidang '{nama}' berhasil ditambahkan!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Gagal menyimpan.")


# ========== TAB UNIT ==========

def _tab_unit(dm):
    st.subheader("Unit")

    with st.spinner("Memuat..."):
        df     = dm.get_master_data('unit_id')
        df_bid = dm.get_master_data('bidang_id')

    col_tbl, col_form = st.columns([2, 1])

    with col_tbl:
        if not df.empty:
            aktif = len(df[df['status'].str.lower() == 'aktif']) if 'status' in df.columns else len(df)
            col_a, col_b = st.columns(2)
            col_a.metric("Total Unit", len(df))
            col_b.metric("Unit Aktif", aktif)
            st.markdown("")

            # Filter by bidang
            bid_filter_list = ["Semua Bidang"]
            if not df_bid.empty and 'nama_bidang' in df_bid.columns:
                bid_filter_list += df_bid['nama_bidang'].tolist()
            sel_filter = st.selectbox("Filter Bidang", bid_filter_list, key="unit_filter")

            df_show = df.copy()
            if sel_filter != "Semua Bidang" and not df_bid.empty:
                bid_row = df_bid[df_bid['nama_bidang'] == sel_filter]
                if not bid_row.empty:
                    df_show = df_show[df_show['bidang_id'] == bid_row.iloc[0]['bidang_id']]

            _render_table(df_show)
        else:
            st.info("Belum ada data unit.")

    with col_form:
        st.markdown("**Tambah Unit Baru**")

        if not df.empty and 'unit_id' in df.columns:
            nums = [int(v[4:]) for v in df['unit_id'].astype(str) if v.startswith('UNIT') and v[4:].isdigit()]
            new_id = f"UNIT{(max(nums)+1 if nums else 1):03d}"
        else:
            new_id = "UNIT001"

        st.text_input("ID (otomatis)", value=new_id, disabled=True, key="unit_id_show")
        nama = st.text_input("Nama Unit *", key="unit_nama",
                             placeholder="Contoh: HRD - Diklat")

        bid_options = {}
        if not df_bid.empty and 'nama_bidang' in df_bid.columns:
            df_bid_aktif = df_bid[df_bid['has_unit'].astype(str).str.upper().isin(['TRUE', 'YA', '1', 'YES'])] \
                if 'has_unit' in df_bid.columns else df_bid
            bid_options = dict(zip(df_bid_aktif['nama_bidang'], df_bid_aktif['bidang_id']))
        sel_bid = st.selectbox("Bidang *", list(bid_options.keys()) or ["(Kosong)"], key="unit_bid")
        sel_bid_id = bid_options.get(sel_bid, '')

        folder_id = st.text_input("Google Drive Folder ID", key="unit_folder",
                                  placeholder="Opsional")

        if st.button("Tambah Unit", type="primary", key="btn_unit"):
            if not nama.strip() or not sel_bid_id:
                st.error("Nama dan Bidang wajib diisi!")
            else:
                data = {
                    'unit_id':    new_id,
                    'nama_unit':  nama.strip(),
                    'bidang_id':  sel_bid_id,
                    'status':     'Aktif',
                    'folder_id':  folder_id.strip(),
                }
                with st.spinner("Menyimpan..."):
                    ok = dm.add_master_data('unit_id', data)
                if ok:
                    st.success(f"Unit '{nama}' berhasil ditambahkan!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Gagal menyimpan.")


# ========== TAB SUBKATEGORI ==========

def _tab_subkategori(dm):
    st.subheader("Subkategori")

    with st.spinner("Memuat..."):
        df      = dm.get_master_data('subkategori_id')
        df_kat  = dm.get_master_data('kategori_id')
        df_bid  = dm.get_master_data('bidang_id')
        df_unit = dm.get_master_data('unit_id')

    col_tbl, col_form = st.columns([2, 1])

    with col_tbl:
        if not df.empty:
            aktif = len(df[df['status'].str.lower() == 'aktif']) if 'status' in df.columns else len(df)
            col_a, col_b = st.columns(2)
            col_a.metric("Total Subkategori", len(df))
            col_b.metric("Aktif", aktif)
            st.markdown("")

            # Filter cepat
            keyword_sub = st.text_input("Cari subkategori...", key="sub_search")
            df_show = df.copy().fillna('')
            if keyword_sub:
                df_show = df_show[
                    df_show.get('nama_subkategori', pd.Series(dtype=str))
                    .str.contains(keyword_sub, case=False, na=False)
                ]
            _render_table(df_show, hide_cols=['folder_id'])
        else:
            st.info("Belum ada data subkategori.")

    with col_form:
        st.markdown("**Tambah Subkategori Baru**")

        if not df.empty and 'subkategori_id' in df.columns:
            nums = [int(v[3:]) for v in df['subkategori_id'].astype(str) if v.startswith('SUB') and v[3:].isdigit()]
            new_id = f"SUB{(max(nums)+1 if nums else 1):03d}"
        else:
            new_id = "SUB001"

        st.text_input("ID (otomatis)", value=new_id, disabled=True, key="sub_id_show")
        nama = st.text_input("Nama Subkategori *", key="sub_nama",
                             placeholder="Contoh: Administrasi Pelayanan")

        # Tipe
        tipe = st.radio("Tipe", ["unit_level", "bidang_level"], horizontal=True, key="sub_tipe")

        # Kategori
        kat_options = {}
        if not df_kat.empty and 'nama_kategori' in df_kat.columns:
            kat_aktif = df_kat[df_kat['status'].str.lower() == 'aktif'] if 'status' in df_kat.columns else df_kat
            kat_options = dict(zip(kat_aktif['nama_kategori'], kat_aktif['kategori_id']))
        sel_kat = st.selectbox("Kategori *", list(kat_options.keys()) or ["(Kosong)"], key="sub_kat")
        sel_kat_id = kat_options.get(sel_kat, '')

        # Bidang
        bid_options = {"-- Tidak Ada --": ""}
        if not df_bid.empty and 'nama_bidang' in df_bid.columns and sel_kat_id:
            df_bid_f = df_bid[df_bid['kategori_id'] == sel_kat_id] if 'kategori_id' in df_bid.columns else df_bid
            bid_options.update(dict(zip(df_bid_f['nama_bidang'], df_bid_f['bidang_id'])))
        sel_bid = st.selectbox("Bidang", list(bid_options.keys()), key="sub_bid")
        sel_bid_id = bid_options.get(sel_bid, '')

        # Unit (hanya jika unit_level)
        sel_unit_id = ''
        if tipe == "unit_level":
            unit_options = {"-- Tidak Ada --": ""}
            if not df_unit.empty and 'nama_unit' in df_unit.columns and sel_bid_id:
                df_unit_f = df_unit[df_unit['bidang_id'] == sel_bid_id] if 'bidang_id' in df_unit.columns else df_unit
                unit_options.update(dict(zip(df_unit_f['nama_unit'], df_unit_f['unit_id'])))
            sel_unit = st.selectbox("Unit", list(unit_options.keys()), key="sub_unit")
            sel_unit_id = unit_options.get(sel_unit, '')

        folder_id = st.text_input("Google Drive Folder ID", key="sub_folder",
                                  placeholder="Opsional")

        if st.button("Tambah Subkategori", type="primary", key="btn_sub"):
            if not nama.strip() or not sel_kat_id:
                st.error("Nama dan Kategori wajib diisi!")
            else:
                data = {
                    'subkategori_id':   new_id,
                    'nama_subkategori': nama.strip(),
                    'kategori_id':      sel_kat_id,
                    'bidang_id':        sel_bid_id,
                    'unit_id':          sel_unit_id,
                    'tipe':             tipe,
                    'status':           'Aktif',
                    'folder_id':        folder_id.strip(),
                }
                with st.spinner("Menyimpan..."):
                    ok = dm.add_master_data('subkategori_id', data)
                if ok:
                    st.success(f"Subkategori '{nama}' berhasil ditambahkan!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Gagal menyimpan.")