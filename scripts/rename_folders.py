# utils/rename_folders.py
"""
Script untuk rename folder di Google Drive
sesuai dengan nama_kategori/nama_bidang/dll di Google Sheets.

Cara pakai:
  Jalankan sebagai Streamlit page tersendiri:
  streamlit run utils/rename_folders.py
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.google_drive_manager import get_drive_manager

st.set_page_config(page_title="Rename Folders", page_icon="✏️", layout="wide")
st.title("✏️ Rename Folder Google Drive")
st.markdown("Script ini akan **rename folder di Drive** sesuai nama terbaru di Google Sheets.")
st.markdown("---")

dm = get_drive_manager()

if not dm or not dm.is_initialized():
    st.error("Google Drive Manager tidak tersedia!")
    st.stop()

st.success("Google Drive Manager siap.")

# ---- Pilih sheet yang mau di-sync ----
sheet_options = {
    "Kategori (kategori_id)":       ('kategori_id',    'kategori_id',    'nama_kategori'),
    "Bidang (bidang_id)":           ('bidang_id',       'bidang_id',      'nama_bidang'),
    "Unit (unit_id)":               ('unit_id',         'unit_id',        'nama_unit'),
    "Subkategori (subkategori_id)": ('subkategori_id',  'subkategori_id', 'nama_subkategori'),
}

selected_label = st.selectbox("Pilih data yang mau di-rename foldernya:", list(sheet_options.keys()))
worksheet_name, id_col, name_col = sheet_options[selected_label]

# ---- Preview data ----
st.markdown("### Preview Data")
with st.spinner("Memuat data dari sheet..."):
    df = dm.get_master_data(worksheet_name)

if df.empty:
    st.warning(f"Sheet '{worksheet_name}' kosong atau tidak dapat diakses.")
    st.stop()

# Cek kolom yang dibutuhkan
required_cols = [id_col, name_col, 'folder_id']
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Kolom berikut tidak ditemukan di sheet: {missing}")
    st.stop()

# Filter hanya yang punya folder_id
df_valid = df[
    df['folder_id'].notna() &
    (df['folder_id'].astype(str).str.strip() != '') &
    (~df['folder_id'].astype(str).str.lower().isin(['nan', 'none', '-']))
].copy()

df_no_folder = df[~df.index.isin(df_valid.index)]

col1, col2 = st.columns(2)
col1.metric("Total data di sheet",       len(df))
col2.metric("Punya folder_id (akan diproses)", len(df_valid))

if not df_no_folder.empty:
    with st.expander(f"⚠️ {len(df_no_folder)} data TANPA folder_id (dilewati)"):
        st.dataframe(df_no_folder[[id_col, name_col]].fillna(''), use_container_width=True, hide_index=True)

st.markdown("")
st.markdown("**Data yang akan di-rename:**")
st.dataframe(
    df_valid[[id_col, name_col, 'folder_id']].fillna(''),
    use_container_width=True,
    hide_index=True
)

st.markdown("---")
st.warning("Tombol di bawah akan **mengubah nama folder di Google Drive** sesuai kolom `nama` di atas. "
           "Proses ini tidak dapat dibatalkan.")

if st.button("🚀 Rename Semua Folder", type="primary", use_container_width=True):
    results = []
    progress = st.progress(0)
    status_text = st.empty()
    total = len(df_valid)

    for i, (_, row) in enumerate(df_valid.iterrows()):
        rid      = str(row.get(id_col, ''))
        new_name = str(row.get(name_col, '')).strip()
        folder_id = str(row.get('folder_id', '')).strip()

        status_text.text(f"[{i+1}/{total}] Rename: {new_name}...")

        if not folder_id or not new_name:
            results.append({'ID': rid, 'Nama Baru': new_name, 'Status': '⏭️ Dilewati (kosong)'})
            continue

        try:
            dm.drive_service.files().update(
                fileId=folder_id,
                body={'name': new_name},
                supportsAllDrives=True
            ).execute()
            results.append({'ID': rid, 'Nama Baru': new_name, 'Status': '✅ Berhasil'})
        except Exception as e:
            err_msg = str(e)
            if 'notFound' in err_msg or '404' in err_msg:
                results.append({'ID': rid, 'Nama Baru': new_name, 'Status': '❌ Folder tidak ditemukan'})
            elif 'insufficientPermissions' in err_msg or '403' in err_msg:
                results.append({'ID': rid, 'Nama Baru': new_name, 'Status': '❌ Tidak ada izin'})
            else:
                results.append({'ID': rid, 'Nama Baru': new_name, 'Status': f'❌ Error: {err_msg[:60]}'})

        progress.progress((i + 1) / total)

    status_text.text("Selesai!")
    st.markdown("---")
    st.markdown("### Hasil")

    import pandas as pd
    df_result = pd.DataFrame(results)
    n_ok  = len(df_result[df_result['Status'].str.startswith('✅')])
    n_err = len(df_result[~df_result['Status'].str.startswith('✅')])

    rc1, rc2 = st.columns(2)
    rc1.metric("Berhasil",   n_ok)
    rc2.metric("Gagal/Skip", n_err)

    st.dataframe(df_result, use_container_width=True, hide_index=True)

    if n_ok == total:
        st.success("Semua folder berhasil di-rename!")
        st.balloons()
    elif n_ok > 0:
        st.warning(f"{n_ok} folder berhasil, {n_err} gagal. Cek detail di atas.")
    else:
        st.error("Semua folder gagal di-rename. Periksa folder_id dan permission service account.")