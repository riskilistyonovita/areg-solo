# modules/ratifikasi.py
"""
Modul Ratifikasi Regulasi - RS Hermina Solo
Menu gabungan: Ratifikasi + Upload File + Folder Manager

Sub-menu:
  1. 📋 Daftar Proses  — tabel dengan tombol aksi per baris
  2. 📤 Upload Draft   — upload Word → GDocs
  3. ✅ Proses Approval — approval manajer & tim regulasi
  4. 📬 Distribusi     — pindah file antar folder Drive
  5. 📁 Folder         — kelola folder Drive (scan, buat, sinkronisasi)
"""

import streamlit as st
import pandas as pd
import io
import base64
from datetime import datetime
from utils.google_drive_manager import get_drive_manager
from utils.auth_manager import get_auth_manager


# ============================================================
# KONSTANTA
# ============================================================

JENIS_REGULASI = ["SPO", "Kebijakan", "Panduan", "SK (Surat Keputusan)", "Program Kerja", "Pedoman"]

STATUS_COLORS = {
    'DRAFT':             '#6c757d',
    'REVIEW':            '#fd7e14',
    'APPROVED_DOC':      '#0d6efd',
    'APPROVED_MANAJER':  '#6610f2',
    'MENUNGGU_TTD':      '#20c997',
    'TERBIT':            '#198754',
    'DIDISTRIBUSI':      '#0a9396',
    'DITOLAK':           '#dc3545',
}

STATUS_LABELS = {
    'DRAFT':             '📝 Draft',
    'REVIEW':            '👁️ Cek Manajer',
    'APPROVED_DOC':      '📄 Menunggu Approve',
    'APPROVED_MANAJER':  '✅ Approved Manajer',
    'MENUNGGU_TTD':      '⏳ Menunggu TTD Direktur',
    'TERBIT':            '🟢 Terbit',
    'DIDISTRIBUSI':      '📬 Didistribusi',
    'DITOLAK':           '🔴 Ditolak',
}

ROLES_UPLOAD   = ['Mutu dan PPI', 'Sekretaris']
ROLES_MANAJER  = ['Managemen']
ROLES_REGULASI = ['Mutu dan PPI', 'Sekretaris', 'Admin', 'IT']
ROLES_DIREKTUR = ['Direktur', 'Managemen']


# ============================================================
# ENTRY POINT
# ============================================================

def show():
    dm   = get_drive_manager()
    auth = get_auth_manager(dm)
    cu   = auth.get_current_user()
    role = cu.get('role', '') if cu else ''

    st.title("✍️ Ratifikasi Regulasi")
    st.markdown("---")

    # ── Tentukan tab berdasarkan permission ──────────────────────────
    # Semua yang bisa buka Ratifikasi → Daftar Proses selalu tampil
    tabs_def = [("📋 Daftar Proses", _tab_daftar, None)]

    # Upload Draft → Tim Regulasi (punya approve_t2 atau distribusi)
    if auth.has_permission('ratifikasi', 'approve_t2') or        auth.has_permission('ratifikasi', 'distribusi'):
        tabs_def.append(("📤 Upload Draft", _tab_upload_draft, None))

    # Proses Approval → Manajer Bidang (T1) atau Tim Regulasi (T2)
    if auth.has_permission('ratifikasi', 'approve_t1') or        auth.has_permission('ratifikasi', 'approve_t2'):
        tabs_def.append(("✅ Proses Approval", _tab_proses_approval, role))

    # Distribusi → punya aksi distribusi
    if auth.has_permission('ratifikasi', 'distribusi'):
        tabs_def.append(("📬 Distribusi", _tab_distribusi, None))

    # Folder Manager → hanya Tim Regulasi & Admin/IT (punya distribusi)
    if auth.has_permission('ratifikasi', 'distribusi'):
        tabs_def.append(("📁 Folder", _tab_folder_manager, None))

    tab_labels = [t[0] for t in tabs_def]
    tab_funcs  = [(t[1], t[2]) for t in tabs_def]
    tabs       = st.tabs(tab_labels)

    for i, (func, extra) in enumerate(tab_funcs):
        with tabs[i]:
            if extra is not None:
                func(dm, cu, extra)
            else:
                func(dm, cu)


# ============================================================
# TAB 1: DAFTAR PROSES — TABEL
# ============================================================

def _tab_daftar(dm, cu):
    st.subheader("📋 Daftar Proses Ratifikasi")
    with st.spinner("Memuat data..."):
        records = dm.get_ratifikasi_list()

    if not records:
        st.info("Belum ada dokumen dalam proses ratifikasi.")
        return

    df = pd.DataFrame(records).fillna('')

    # Metrik ringkasan
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Total", len(df))
    in_prog = ['DRAFT','REVIEW','APPROVED_DOC','APPROVED_MANAJER']
    m2.metric("Dalam Proses", len(df[df['status'].isin(in_prog)]) if 'status' in df.columns else 0)
    m3.metric("Menunggu TTD", len(df[df['status']=='MENUNGGU_TTD']) if 'status' in df.columns else 0)
    m4.metric("Terbit", len(df[df['status'].isin(['TERBIT','DIDISTRIBUSI'])]) if 'status' in df.columns else 0)
    m5.metric("Ditolak", len(df[df['status']=='DITOLAK']) if 'status' in df.columns else 0)

    st.markdown("---")

    # Filter
    fa, fb, fc = st.columns([3,2,2])
    with fa: kw  = st.text_input("🔍 Cari...", key="daf_kw")
    with fb: sj  = st.selectbox("Jenis", ['Semua']+JENIS_REGULASI, key="daf_jenis")
    with fc: sst = st.selectbox("Status", ['Semua']+list(STATUS_COLORS.keys()), key="daf_st")

    df2 = df.copy()
    if kw:           df2 = df2[df2.get('nama_dokumen', pd.Series(dtype=str)).str.contains(kw, case=False, na=False)]
    if sj  != 'Semua': df2 = df2[df2.get('jenis_regulasi', pd.Series(dtype=str)) == sj]
    if sst != 'Semua': df2 = df2[df2.get('status', pd.Series(dtype=str)) == sst]

    if df2.empty:
        st.info("Tidak ada dokumen yang sesuai filter.")
        return

    # Header tabel
    st.markdown("""
    <div style='display:grid;grid-template-columns:3fr 1fr 1.5fr 1fr 1.5fr;
                gap:8px;padding:8px 12px;background:#f8f9fa;border-radius:6px;
                font-size:12px;font-weight:600;color:#495057;margin-bottom:4px'>
      <span>Nama Dokumen</span>
      <span>Kategori</span>
      <span>Status</span>
      <span>Preview</span>
      <span>Aksi</span>
    </div>
    """, unsafe_allow_html=True)

    for _, row in df2.iterrows():
        _render_table_row(row, dm, cu)


def _render_table_row(row, dm, cu):
    status   = str(row.get('status','DRAFT'))
    color    = STATUS_COLORS.get(status, '#6c757d')
    label    = STATUS_LABELS.get(status, status)
    nama     = str(row.get('nama_dokumen','-'))
    jenis    = str(row.get('jenis_regulasi','-'))
    nomor    = str(row.get('nomor_dokumen','-'))
    id_rat   = str(row.get('id_ratifikasi','-'))
    tgl      = str(row.get('tgl_upload','-'))[:10]
    word_id  = str(row.get('file_word_id',''))
    pdf_id   = str(row.get('file_pdf_id',''))

    # Row dengan 5 kolom: Nama | Kategori | Status | Preview | Aksi
    c1, c2, c3, c4, c5 = st.columns([3, 1, 1.5, 1, 1.5])

    with c1:
        st.markdown(f"""
        <div style='padding:8px 4px'>
          <div style='font-size:13px;font-weight:600;color:#212529'>{nama}</div>
          <div style='font-size:11px;color:#aaa'>No: {nomor} | {tgl}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style='padding:8px 4px;font-size:12px;color:#555'>{jenis}</div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div style='padding:8px 4px'>
          <span style='background:{color};color:white;padding:3px 8px;
                       border-radius:10px;font-size:11px;font-weight:600'>{label}</span>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        if pdf_id:
            st.link_button("📕 PDF", f"https://drive.google.com/file/d/{pdf_id}/view",
                           use_container_width=True, type="secondary")
        elif word_id:
            st.link_button("📝 Doc", f"https://docs.google.com/document/d/{word_id}/edit",
                           use_container_width=True, type="secondary")

    with c5:
        if status == 'MENUNGGU_TTD':
            if st.button("📤 Upload TTD", key=f"up_{id_rat}",
                         use_container_width=True, type="primary"):
                st.session_state[f'show_up_{id_rat}'] = not st.session_state.get(f'show_up_{id_rat}', False)

    # Garis pemisah
    st.markdown("<hr style='margin:2px 0;border-color:#f0f0f0'>", unsafe_allow_html=True)

    # Panel upload TTD (expand inline jika diklik)
    if st.session_state.get(f'show_up_{id_rat}'):
        with st.container():
            _panel_upload_ttd_inline(row, dm, cu)
            if st.button("✖️ Tutup", key=f"cls_{id_rat}", type="secondary"):
                st.session_state.pop(f'show_up_{id_rat}', None)
                st.rerun()
        st.markdown("---")


def _panel_upload_ttd_inline(row, dm, cu):
    """Panel upload PDF bertanda tangan Direktur — tampil inline di tabel."""
    id_rat   = str(row.get('id_ratifikasi',''))
    nama     = str(row.get('nama_dokumen','-'))
    nomor    = str(row.get('nomor_dokumen','-'))
    jenis    = str(row.get('jenis_regulasi','-'))
    pdf_id   = str(row.get('file_pdf_id',''))
    bid_id   = str(row.get('bidang_id',''))
    bid_nama = str(row.get('bidang_nama',''))

    st.markdown(f"""
    <div style='background:#e8f5e9;border-left:3px solid #198754;
                padding:10px 14px;border-radius:4px;font-size:13px'>
    📋 Upload PDF final yang sudah ditandatangani Direktur.<br>
    File akan disimpan di folder <b>Ratifikasi_Draft</b> dulu — pindah folder via menu <b>Distribusi</b>.
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload PDF final (TTD Direktur) *",
                                 type=['pdf'], key=f"upf_{id_rat}")
    tgl_terbit = st.date_input("Tanggal terbit", value=datetime.now().date(),
                                key=f"tgl_{id_rat}")

    if st.button("💾 Simpan PDF Final", key=f"savef_{id_rat}",
                  type="primary", use_container_width=True,
                  disabled=not uploaded):

        safe   = nama.strip().replace(' ','_')[:60]
        fname  = f"{nomor.replace('/','_')}_{safe}_TTD.pdf"
        folder = dm.get_or_create_ratifikasi_folder()

        with st.spinner("📤 Mengupload..."):
            res = dm.upload_file_to_drive(
                file_content=uploaded.read(),
                file_name=fname,
                mime_type='application/pdf',
                folder_id=folder
            )
        if not res:
            st.error("❌ Gagal upload.")
            return

        new_id   = res.get('id','')
        new_link = res.get('link', f"https://drive.google.com/file/d/{new_id}/view")

        # Hapus PDF lama
        if pdf_id and pdf_id != new_id:
            try: dm.drive_service.files().delete(fileId=pdf_id, supportsAllDrives=True).execute()
            except: pass

        dm.update_ratifikasi_record(id_rat, {
            'status':        'TERBIT',
            'file_pdf_id':   new_id,
            'file_pdf_link': new_link,
            'tgl_terbit':    str(tgl_terbit),
        })

        st.success(f"✅ PDF final tersimpan! Gunakan menu **Distribusi** untuk memindahkan ke folder yang sesuai.")
        st.session_state.pop(f'show_upload_ttd_{id_rat}', None)
        st.rerun()


# ============================================================
# TAB 2: UPLOAD DRAFT
# ============================================================

def _tab_upload_draft(dm, cu):
    st.subheader("📤 Upload Draft Dokumen")
    st.markdown("<p style='color:#666;font-size:13px'>Upload file Word → otomatis dikonversi ke <b>Google Docs</b> di Drive.</p>",
                unsafe_allow_html=True)

    with st.spinner("Memuat data..."):
        all_users = dm.get_users() or []
        df_bid    = dm.get_master_data('bidang_id')

    bid_opts = {}
    if not df_bid.empty and 'bidang_id' in df_bid.columns:
        for _, r in df_bid.iterrows():
            if str(r.get('status','aktif')).lower() == 'aktif':
                bid_opts[str(r.get('nama_bidang',''))] = str(r.get('bidang_id',''))

    reviewer_opts = _build_user_options(all_users)

    with st.form("form_upload", clear_on_submit=False):
        st.markdown("##### 📝 Informasi Dokumen")
        c1, c2 = st.columns(2)
        with c1:
            jenis    = st.selectbox("Jenis Regulasi *", JENIS_REGULASI)
            nama_dok = st.text_input("Nama Dokumen *", placeholder="Contoh: SPO Cuci Tangan")
        with c2:
            nomor_dok = st.text_input("Nomor Dokumen *", placeholder="001/SPO/2026")
            catatan   = st.text_area("Catatan", placeholder="Opsional", height=68)

        st.markdown("---")
        st.markdown("##### 🏷️ Bidang / Unit")
        if bid_opts:
            sel_bid_label = st.selectbox("Bidang *", ["— Pilih —"]+list(bid_opts.keys()))
            sel_bid_id    = bid_opts.get(sel_bid_label,'') if sel_bid_label != "— Pilih —" else ''
        else:
            sel_bid_label, sel_bid_id = '', ''
            st.info("Data bidang belum tersedia.")

        st.markdown("---")
        st.markdown("##### 📁 File Draft Word")
        uploaded_file = st.file_uploader("Upload file .docx *", type=['docx'])

        st.markdown("---")
        st.markdown("##### 👁️ Reviewer Unit Terkait")
        sel_reviewers = st.multiselect("Pilih reviewer (opsional)",
                                        options=list(reviewer_opts.keys())) if reviewer_opts else []

        st.markdown("---")
        manajer_opts = _build_manajer_options(all_users, sel_bid_label if sel_bid_label != "— Pilih —" else '')
        st.markdown("##### ✅ Manajer Bidang")
        sel_manajer = st.selectbox("Pilih Manajer Bidang *",
                                    ["— Pilih —"]+list(manajer_opts.keys())) if manajer_opts else "— Pilih —"

        submitted = st.form_submit_button("📤 Upload & Mulai Proses Ratifikasi",
                                           type="primary", use_container_width=True)

    if submitted:
        _process_upload(dm, cu, jenis, nama_dok, nomor_dok, catatan, uploaded_file,
                         [reviewer_opts[k] for k in sel_reviewers if k in reviewer_opts],
                         manajer_opts.get(sel_manajer,'') if sel_manajer != "— Pilih —" else '',
                         sel_manajer if sel_manajer != "— Pilih —" else '',
                         sel_bid_id, sel_bid_label if sel_bid_label != "— Pilih —" else '')


def _process_upload(dm, cu, jenis, nama_dok, nomor_dok, catatan, uploaded_file,
                     reviewer_emails, manajer_email, manajer_nama, bid_id, bid_nama):
    errors = []
    if not nama_dok.strip():  errors.append("Nama dokumen wajib diisi.")
    if not nomor_dok.strip(): errors.append("Nomor dokumen wajib diisi.")
    if not uploaded_file:     errors.append("File .docx wajib diupload.")
    if not manajer_email:     errors.append("Manajer Bidang wajib dipilih.")
    for e in errors: st.error(e)
    if errors: return

    folder_id = dm.get_or_create_ratifikasi_folder()
    if not folder_id:
        st.error("❌ Gagal mendapatkan folder Ratifikasi.")
        return

    safe = f"{nomor_dok.replace('/','_')}_{nama_dok.strip().replace(' ','_')}"[:80]
    with st.spinner("📝 Mengupload dan mengkonversi ke Google Docs..."):
        result = dm.upload_docx_as_gdoc(file_content=uploaded_file.read(),
                                          file_name=safe, folder_id=folder_id)
    if not result:
        st.error("❌ Gagal mengkonversi ke Google Docs.")
        return

    gdoc_id, gdoc_link = result.get('id',''), result.get('link','')
    all_emails = list(set(reviewer_emails + ([manajer_email] if manajer_email else [])))
    if all_emails:
        with st.spinner("🔗 Membagikan akses..."):
            for email in all_emails:
                dm.share_gdrive_file_reader(gdoc_id, email)

    existing = dm.get_ratifikasi_list()
    new_id   = _gen_id(existing)
    record   = {
        'id_ratifikasi':    new_id,
        'jenis_regulasi':   jenis,
        'nama_dokumen':     nama_dok.strip(),
        'nomor_dokumen':    nomor_dok.strip(),
        'bidang_id':        bid_id,
        'bidang_nama':      bid_nama,
        'status':           'REVIEW',
        'file_word_id':     gdoc_id,
        'file_word_link':   gdoc_link,
        'file_pdf_id':      '',
        'file_pdf_link':    '',
        'reviewer_emails':  ','.join(reviewer_emails),
        'manajer_email':    manajer_email,
        'manajer_nama':     manajer_nama,
        'uploaded_by':      cu.get('user_id','') if cu else '',
        'uploaded_by_name': cu.get('nama_lengkap','') if cu else '',
        'catatan':          catatan.strip(),
        'tgl_upload':       datetime.now().strftime('%Y-%m-%d'),
    }
    with st.spinner("💾 Menyimpan..."):
        ok = dm.add_ratifikasi_record(record)
    if ok:
        st.success(f"✅ **{nama_dok}** berhasil diupload! ID: `{new_id}`")
        st.balloons()
        st.rerun()
    else:
        st.error("❌ Gagal menyimpan ke database.")


# ============================================================
# TAB 3: PROSES APPROVAL
# ============================================================

def _tab_proses_approval(dm, cu, role):
    st.subheader("✅ Proses Approval & Tanda Tangan")

    canvas_ok = False
    try:
        from streamlit_drawable_canvas import st_canvas
        canvas_ok = True
    except ImportError:
        pass

    with st.spinner("Memuat data..."):
        records = dm.get_ratifikasi_list()
    if not records:
        st.info("Belum ada dokumen.")
        return

    df      = pd.DataFrame(records).fillna('')
    my_docs = _get_relevant_docs(df, role, cu)

    if my_docs.empty:
        st.info("Tidak ada dokumen yang memerlukan tindakan dari Anda saat ini.")
        return

    st.markdown(f"**{len(my_docs)} dokumen** memerlukan tindakan Anda:")
    for _, row in my_docs.iterrows():
        _render_approval_panel(row, dm, cu, role, canvas_ok)


def _get_relevant_docs(df, role, cu):
    if df.empty or 'status' not in df.columns:
        return pd.DataFrame()
    user_email = (cu.get('email','') if cu else '').strip().lower()
    relevant   = set()
    if role in ROLES_MANAJER:
        relevant.update(['REVIEW','APPROVED_DOC'])
    if role in ROLES_REGULASI:
        relevant.add('APPROVED_MANAJER')
    if role in ['Admin','IT']:
        relevant = {'REVIEW','APPROVED_DOC','APPROVED_MANAJER'}
    if not relevant:
        return pd.DataFrame()
    mask = df['status'].isin(relevant)
    if role in ROLES_MANAJER and user_email and 'manajer_email' in df.columns:
        em = df['manajer_email'].str.strip().str.lower() == user_email
        mst = df['status'].isin(['REVIEW','APPROVED_DOC'])
        other = df['status'].isin(relevant - {'REVIEW','APPROVED_DOC'})
        if em.any():
            mask = (mst & em) | other
    return df[mask].drop_duplicates(subset=['id_ratifikasi'])


def _render_approval_panel(row, dm, cu, role, canvas_ok):
    id_rat  = str(row.get('id_ratifikasi',''))
    nama    = str(row.get('nama_dokumen','-'))
    jenis   = str(row.get('jenis_regulasi','-'))
    nomor   = str(row.get('nomor_dokumen','-'))
    status  = str(row.get('status',''))
    color   = STATUS_COLORS.get(status,'#6c757d')
    label   = STATUS_LABELS.get(status,status)
    word_id = str(row.get('file_word_id',''))
    pdf_id  = str(row.get('file_pdf_id',''))

    with st.expander(f"{'📕' if pdf_id else '📝'} {nama} — {jenis} | {nomor}", expanded=True):
        hc1, hc2 = st.columns([3,1])
        with hc1:
            st.markdown(f"**ID:** `{id_rat}`")
            if word_id: st.markdown(f"[📝 Buka Google Docs](https://docs.google.com/document/d/{word_id}/edit)")
            if pdf_id:  st.markdown(f"[📕 Buka PDF](https://drive.google.com/file/d/{pdf_id}/view)")
        with hc2:
            st.markdown(f"<span style='background:{color};color:white;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600'>{label}</span>",
                        unsafe_allow_html=True)
        st.markdown("---")

        if status == 'REVIEW' and (role in ROLES_MANAJER or role in ['Admin','IT']):
            _panel_cek_gdocs(id_rat, dm, cu, word_id, nama_dok=nama)
        elif status == 'APPROVED_DOC' and (role in ROLES_MANAJER or role in ['Admin','IT']):
            _panel_signing(id_rat, 'manajer', 'Manajer Bidang', dm, cu,
                            next_status='APPROVED_MANAJER', pdf_id=pdf_id, nama_dok=nama)
        elif status == 'APPROVED_MANAJER' and role in ROLES_REGULASI:
            _panel_signing(id_rat, 'regulasi', 'Tim Regulasi', dm, cu,
                            next_status='MENUNGGU_TTD', pdf_id=pdf_id, nama_dok=nama,
                            extra_fields={'tgl_terbit': datetime.now().strftime('%Y-%m-%d')})

        if role in ['Admin','IT'] and status == 'DITOLAK':
            st.markdown("---")
            if st.button("🔄 Reset ke DRAFT", key=f"rst_{id_rat}", type="secondary"):
                ok = dm.update_ratifikasi_record(id_rat, {'status':'DRAFT','catatan':''})
                if ok: st.rerun()


def _panel_cek_gdocs(id_rat, dm, cu, word_id, nama_dok=''):
    st.markdown("#### 📝 Cek & Verifikasi Google Docs")
    st.markdown("""
    <div style='background:#e8f4fd;border-left:3px solid #0d6efd;padding:10px;border-radius:4px;font-size:13px'>
    Buka GDocs di atas → pastikan isi sudah benar → klik <b>Approve & Konversi ke PDF</b>
    </div>""", unsafe_allow_html=True)
    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Approve & Konversi ke PDF", key=f"appDoc_{id_rat}",
                     type="primary", use_container_width=True):
            with st.spinner("🔄 Mengekspor ke PDF..."):
                pdf_bytes = dm.export_gdoc_as_pdf(word_id)
            if not pdf_bytes:
                st.error("❌ Gagal ekspor. Coba lagi.")
                return
            safe = (nama_dok.strip().replace(' ','_')[:60] if nama_dok else id_rat)
            with st.spinner("📤 Menyimpan PDF..."):
                folder_id = dm.get_or_create_ratifikasi_folder()
                res = dm.upload_file_to_drive(pdf_bytes, f"{safe}.pdf", 'application/pdf', folder_id)
            if not res:
                st.error("❌ Gagal menyimpan PDF.")
                return
            ok = dm.update_ratifikasi_record(id_rat, {
                'status': 'APPROVED_DOC',
                'file_pdf_id': res.get('id',''),
                'file_pdf_link': res.get('link',''),
            })
            if ok:
                st.success("✅ GDocs disetujui → PDF siap untuk approval!")
                st.rerun()
    with c2:
        _tolak_button(id_rat, dm, cu, 'Manajer Bidang')


def _panel_signing(id_rat, signer_key, signer_label, dm, cu,
                    next_status, pdf_id='', nama_dok='', extra_fields=None):
    user_id  = cu.get('user_id','') if cu else ''
    nama     = cu.get('nama_lengkap','') if cu else ''
    now_str  = datetime.now().strftime('%d/%m/%Y %H:%M')

    if pdf_id:
        st.markdown(f"[📕 Buka PDF untuk direview](https://drive.google.com/file/d/{pdf_id}/view)")

    st.markdown(f"""
    <div style='background:#e8f4fd;border-left:3px solid #0d6efd;
                padding:10px;border-radius:4px;font-size:13px;margin:8px 0'>
    Review PDF di atas lalu klik <b>✅ Approve</b>.<br>
    <small>Footer approval akan ditambahkan ke setiap halaman PDF.</small>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"**Approver:** {nama} ({user_id}) — {signer_label} | {now_str}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"✅ Approve sebagai {signer_label}",
                     key=f"app_{id_rat}_{signer_key}",
                     type="primary", use_container_width=True):
            _do_approve(id_rat, signer_key, signer_label, dm, cu,
                         next_status, pdf_id, nama_dok, extra_fields)
    with c2:
        _tolak_button(id_rat, dm, cu, signer_label)


def _do_approve(id_rat, signer_key, signer_label, dm, cu,
                 next_status, pdf_id, nama_dok, extra_fields):
    user_id     = cu.get('user_id','') if cu else ''
    nama        = cu.get('nama_lengkap','') if cu else ''
    now_str     = datetime.now().strftime('%d/%m/%Y %H:%M')
    footer_text = f"Checked & Approved by: {user_id} ({signer_label}) | {now_str}"

    now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    updates = {
        f'ttd_{signer_key}':      'APPROVED',
        f'ttd_{signer_key}_nama': nama,
        f'ttd_{signer_key}_tgl':  now_iso,
        'status':                  next_status,
    }
    if extra_fields: updates.update(extra_fields)

    with st.spinner("💾 Menyimpan status..."):
        ok = dm.update_ratifikasi_record(id_rat, updates)
    if not ok:
        st.error("❌ Gagal menyimpan."); return

    msgs = {
        'MENUNGGU_TTD':     "✅ Approved! PDF siap dikirim ke Direktur via ManPro. Upload PDF TTD via Daftar Proses.",
        'APPROVED_MANAJER': "✅ Approved oleh Manajer! Menunggu Tim Regulasi.",
    }
    st.success(msgs.get(next_status, "✅ Approved!"))

    if pdf_id:
        try:
            with st.spinner("📄 Menambahkan footer ke PDF..."):
                pdf_bytes = dm.download_file_from_drive(pdf_id)
            if pdf_bytes:
                annotated = _add_approval_footer(pdf_bytes, footer_text, signer_key)
                dm.update_file_in_drive(pdf_id, annotated)
        except Exception:
            pass
    st.rerun()


def _add_approval_footer(pdf_bytes: bytes, text: str, signer_key: str) -> bytes:
    import fitz
    colors = {'manajer':(0.0,0.35,0.7),'regulasi':(0.3,0.0,0.6)}
    color  = colors.get(signer_key,(0.3,0.3,0.3))
    y_offs = {'manajer':8,'regulasi':14}
    y_from = y_offs.get(signer_key,8)
    doc    = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        ph,pw = page.rect.height, page.rect.width
        if signer_key == 'manajer':
            page.draw_line(fitz.Point(pw*0.45,ph-10), fitz.Point(pw-15,ph-10),
                           color=(0.7,0.7,0.7), width=0.3)
        try: tw = fitz.get_text_length(text, fontname="helv", fontsize=5)
        except: tw = len(text)*2.5
        xp = max(pw-tw-15, pw*0.45)
        page.insert_text(fitz.Point(xp, ph-y_from), text, fontsize=5, color=color)
    out = io.BytesIO(); doc.save(out); doc.close()
    return out.getvalue()


def _tolak_button(id_rat, dm, cu, signer_label):
    slug = signer_label.replace(' ','_').replace('(','').replace(')','')[:20]
    key_show = f"tolakShow_{id_rat}_{slug}"
    if st.button("❌ Tolak", key=f"tolakBtn_{id_rat}_{slug}",
                 type="secondary", use_container_width=True):
        st.session_state[key_show] = True
    if st.session_state.get(key_show):
        cat = st.text_area("Alasan:", key=f"tolakCat_{id_rat}_{slug}", placeholder="Jelaskan...")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("✅ Konfirmasi", key=f"konfTolak_{id_rat}_{slug}",
                         type="primary", use_container_width=True):
                dm.update_ratifikasi_record(id_rat,{
                    'status':'DITOLAK',
                    'catatan':f"Ditolak ({signer_label}): {cat.strip() or '-'}"
                })
                st.session_state.pop(key_show,None); st.rerun()
        with c2:
            if st.button("Batal", key=f"batal_{id_rat}_{slug}", use_container_width=True):
                st.session_state.pop(key_show,None); st.rerun()


# ============================================================
# TAB 4: DISTRIBUSI
# ============================================================

def _tab_distribusi(dm, cu):
    st.subheader("📬 Distribusi Dokumen")
    st.markdown("Pindahkan PDF dari folder Ratifikasi_Draft ke folder tujuan yang sesuai.")

    with st.spinner("Memuat data..."):
        records = dm.get_ratifikasi_list()
    if not records:
        st.info("Belum ada data."); return

    df = pd.DataFrame(records).fillna('')
    df_dist = df[df.get('status', pd.Series(dtype=str)).isin(['TERBIT'])] \
        if 'status' in df.columns else pd.DataFrame()

    if df_dist.empty:
        st.success("✅ Semua dokumen sudah didistribusi atau belum ada yang TERBIT.")
        df_done = df[df.get('status', pd.Series(dtype=str)) == 'DIDISTRIBUSI'] \
            if 'status' in df.columns else pd.DataFrame()
        if not df_done.empty:
            st.markdown(f"**{len(df_done)} dokumen sudah didistribusi:**")
            for _, row in df_done.iterrows():
                nama   = str(row.get('nama_dokumen','-'))
                folder = str(row.get('folder_distribusi','-'))
                tgl    = str(row.get('tgl_distribusi','-'))[:10]
                pdf_id = str(row.get('file_pdf_id',''))
                c1,c2 = st.columns([4,1])
                with c1: st.markdown(f"✅ **{nama}** → {folder} | {tgl}")
                with c2:
                    if pdf_id:
                        st.link_button("📕", f"https://drive.google.com/file/d/{pdf_id}/view",
                                       use_container_width=True)
        return

    # ── Hierarchical folder picker dari master data ──────────────────────
    st.markdown("#### 📂 Pilih Folder Tujuan")

    def _get_master(sheet):
        try: return dm.get_master_data(sheet)
        except: return pd.DataFrame()

    df_menu = _get_master('menu_id')
    df_kat  = _get_master('kategori_id')
    df_bid  = _get_master('bidang_id')
    df_unit = _get_master('unit_id')

    def _opts_all(df, id_col, nama_col):
        opts = {"📁 Pilih folder...": None}
        if df.empty: return opts
        for _, r in df.iterrows():
            fid  = str(r.get('folder_id','')).strip()
            nam  = str(r.get(nama_col,'')).strip()
            rid  = str(r.get(id_col,'')).strip()
            if not fid or fid in ('nan','None',''): continue
            opts[f"{nam}  ({rid})"] = fid
        return opts

    def _opts_by_parent(df, id_col, nama_col, parent_fid):
        if not parent_fid:
            return _opts_all(df, id_col, nama_col)
        opts = {"📁 Pilih folder...": None}
        if df.empty: return opts
        # Pakai cache subfolder Drive
        cache_key = f"_dist_subs_{parent_fid}"
        if cache_key not in st.session_state:
            subs = _drive_list_sub(dm, parent_fid)
            st.session_state[cache_key] = {s['id'] for s in subs}
        valid = st.session_state.get(cache_key, set())
        if 'folder_id' not in df.columns: return _opts_all(df, id_col, nama_col)
        matched = set(df['folder_id'].astype(str).str.strip()) & valid
        if not matched: return _opts_all(df, id_col, nama_col)
        for _, r in df.iterrows():
            fid  = str(r.get('folder_id','')).strip()
            nam  = str(r.get(nama_col,'')).strip()
            rid  = str(r.get(id_col,'')).strip()
            if fid not in matched: continue
            opts[f"{nam}  ({rid})"] = fid
        return opts

    col1, col2 = st.columns(2)
    # Level 1 — Menu
    menu_opts = _opts_all(df_menu, 'menu_id', 'nama_menu')
    sel_menu_lbl = col1.selectbox("Menu", list(menu_opts.keys()), key="dist_menu")
    sel_menu_fid = menu_opts.get(sel_menu_lbl)

    # Level 2 — Kategori
    kat_opts = _opts_by_parent(df_kat, 'kategori_id', 'nama_kategori', sel_menu_fid)
    sel_kat_lbl = col2.selectbox("Kategori", list(kat_opts.keys()), key="dist_kat")
    sel_kat_fid = kat_opts.get(sel_kat_lbl)

    col3, col4 = st.columns(2)
    # Level 3 — Bidang
    bid_opts = _opts_by_parent(df_bid, 'bidang_id', 'nama_bidang', sel_kat_fid)
    sel_bid_lbl = col3.selectbox("Bidang", list(bid_opts.keys()), key="dist_bid")
    sel_bid_fid = bid_opts.get(sel_bid_lbl)

    # Level 4 — Unit
    unit_opts = _opts_by_parent(df_unit, 'unit_id', 'nama_unit', sel_bid_fid)
    sel_unit_lbl = col4.selectbox("Unit (opsional)", list(unit_opts.keys()), key="dist_unit")
    sel_unit_fid = unit_opts.get(sel_unit_lbl)

    # Tentukan folder target: paling dalam yang dipilih
    target_fid, target_name = None, ''
    for fid, lbl in [
        (sel_unit_fid, sel_unit_lbl),
        (sel_bid_fid,  sel_bid_lbl),
        (sel_kat_fid,  sel_kat_lbl),
        (sel_menu_fid, sel_menu_lbl),
    ]:
        if fid:
            target_fid  = fid
            target_name = lbl.split('  (')[0].strip()
            break

    if target_fid:
        st.success(f"🎯 Folder tujuan: **{target_name}**")
    else:
        st.info("⬆️ Pilih folder tujuan di atas")

    st.markdown("---")

    # ── Daftar dokumen siap distribusi ───────────────────────────────────
    st.markdown(f"**{len(df_dist)} dokumen** siap didistribusi:")
    for _, row in df_dist.iterrows():
        id_rat  = str(row.get('id_ratifikasi',''))
        nama    = str(row.get('nama_dokumen','-'))
        jenis   = str(row.get('jenis_regulasi','-'))
        nomor   = str(row.get('nomor_dokumen','-'))
        pdf_id  = str(row.get('file_pdf_id',''))

        st.markdown(f"""
        <div style='border:1px solid #dee2e6;border-radius:8px;padding:10px 14px;
                    margin-bottom:6px;background:#fff;border-left:5px solid #198754'>
          <b>{nama}</b> <span style='color:#888;font-size:12px'>{jenis} | {nomor}</span>
        </div>""", unsafe_allow_html=True)

        dc1, dc2 = st.columns([2, 1])
        with dc1:
            if pdf_id:
                st.link_button("📕 Preview PDF",
                               f"https://drive.google.com/file/d/{pdf_id}/view",
                               use_container_width=True, type="secondary")
            else:
                st.warning("⚠️ Tidak ada PDF")
        with dc2:
            btn_disabled = not target_fid or not pdf_id
            if st.button("📬 Distribusikan", key=f"distBtn_{id_rat}",
                         use_container_width=True, type="primary",
                         disabled=btn_disabled):

                if not pdf_id:
                    st.error("❌ Tidak ada file PDF!"); st.stop()
                if not target_fid:
                    st.error("❌ Pilih folder tujuan dulu!"); st.stop()

                # Langkah 1: pindahkan file
                with st.spinner(f"Memindahkan ke {target_name}..."):
                    ok_mv = dm.move_file_to_folder(pdf_id, target_fid)

                if not ok_mv:
                    st.error(
                        f"❌ Gagal memindahkan **{nama}** ke {target_name}!\n\n"
                        "Status TIDAK diubah. Cek akses service account ke folder tujuan."
                    )
                    st.stop()

                # Langkah 2: daftarkan ke rekap_database
                with st.spinner("Mendaftarkan ke database..."):
                    # Ambil kat_id & bid_id dari master untuk isi kolom
                    kat_id_val, bid_id_val = '', ''
                    if sel_kat_fid and not df_kat.empty and 'folder_id' in df_kat.columns:
                        kr = df_kat[df_kat['folder_id'].astype(str) == sel_kat_fid]
                        if not kr.empty: kat_id_val = str(kr.iloc[0].get('kategori_id','')).strip()
                    if sel_bid_fid and not df_bid.empty and 'folder_id' in df_bid.columns:
                        br = df_bid[df_bid['folder_id'].astype(str) == sel_bid_fid]
                        if not br.empty: bid_id_val = str(br.iloc[0].get('bidang_id','')).strip()

                    ok_log = dm.log_to_sheets({
                        'nama_regulasi':     nama,
                        'nomor_regulasi':    nomor,
                        'jenis_regulasi':    jenis,
                        'kategori_id':       kat_id_val,
                        'bidang_id':         bid_id_val,
                        'google_drive_id':   pdf_id,
                        'google_drive_link': f"https://drive.google.com/file/d/{pdf_id}/view",
                        'tanggal_terbit':    str(row.get('tgl_terbit', '')),
                        'status':            'aktif',
                        'created_by':        cu.get('user_id', '') if cu else '',
                    })

                # Langkah 3: update status
                dm.update_ratifikasi_record(id_rat, {
                    'status':            'DIDISTRIBUSI',
                    'folder_distribusi': target_name,
                    'tgl_distribusi':    datetime.now().strftime('%Y-%m-%d'),
                })

                if ok_log:
                    st.success(f"🎉 **{nama}** berhasil dipindah ke **{target_name}** dan terdaftar!")
                else:
                    st.warning(
                        f"⚠️ **{nama}** dipindah ke **{target_name}** "
                        "tapi gagal otomatis daftar ke database. "
                        "Gunakan **Folder → Sync File** untuk daftar manual."
                    )
                st.rerun()


# ============================================================
# TAB 5: FOLDER MANAGER
# ============================================================

def _tab_folder_manager(dm, cu):
    st.subheader("📁 Kelola Folder & Sinkronisasi Drive")

    sub1, sub2, sub3, sub4 = st.tabs([
        "🗂️ Sync Master Data",
        "📄 Sync File",
        "📋 Daftar Folder",
        "➕ Buat Folder",
    ])
    with sub1:
        _tab_sync_master(dm, cu)
    with sub2:
        _tab_sync_file(dm, cu)
    with sub3:
        _tab_folder_list(dm)
    with sub4:
        _tab_folder_create(dm)


# ═══════════════════════════════════════════════════════════════════════════
# SINKRONISASI DRIVE — hierarki: menu → kat → bid → unit → sub
# ═══════════════════════════════════════════════════════════════════════════

LEVEL_ORDER = ["menu", "kat", "bid", "unit", "sub"]
LEVEL_NEXT  = {"menu": "kat", "kat": "bid", "bid": "unit", "unit": "sub", "sub": None}
LEVEL_META  = {
    "menu": ("Menu",        "menu_id",        "menu_id",        "nama_menu",        "MENU", None),
    "kat":  ("Kategori",    "kategori_id",    "kategori_id",    "nama_kategori",    "KAT",  "menu_id"),
    "bid":  ("Bidang",      "bidang_id",      "bidang_id",      "nama_bidang",      "BID",  "kategori_id"),
    "unit": ("Unit",        "unit_id",        "unit_id",        "nama_unit",        "UNIT", "bidang_id"),
    "sub":  ("Subkategori", "subkategori_id", "subkategori_id", "nama_subkategori", "SUB",  "unit_id"),
}
LEVEL_BADGE = {
    "menu": "#6610f2", "kat": "#0d6efd",
    "bid":  "#fd7e14", "unit": "#198754", "sub": "#6c757d",
}


def _areg_roots(dm):
    return [
        ("Regulasi",        dm.DRIVE_FOLDER_ID),
        ("Perijinan & PKS", dm.PKS_FOLDER_ID),
        ("e-Library",       dm.ELIBRARY_FOLDER_ID),
        ("Dokumen Lainnya", dm.DOK_LAINNYA_FOLDER_ID),
    ]


def _load_by_fid(dm):
    by_fid = {}
    for level in LEVEL_ORDER:
        lbl, sheet, id_col, nama_col, prefix, parent_col = LEVEL_META[level]
        try:
            df = dm.get_master_data(sheet)
        except Exception:
            continue
        if df.empty: continue
        for _, r in df.iterrows():
            fid = str(r.get('folder_id', '')).strip()
            rid = str(r.get(id_col, '')).strip()
            nam = str(r.get(nama_col, '')).strip()
            if not fid or fid in ('nan', 'None', ''): continue
            entry = {'id': rid, 'nama': nam, 'level': level}
            for lv2 in LEVEL_ORDER:
                ic = LEVEL_META[lv2][2]
                v  = str(r.get(ic, '')).strip()
                if v and v not in ('nan', 'None', ''): entry[ic] = v
            by_fid[fid] = entry
    return by_fid


def _next_id(dm, level):
    _, sheet, id_col, _, prefix, _ = LEVEL_META[level]
    try:
        df = dm.get_master_data(sheet)
        if df.empty or id_col not in df.columns: return f"{prefix}001"
        nums = [int(v[len(prefix):]) for v in df[id_col].astype(str)
                if v.startswith(prefix) and v[len(prefix):].isdigit()]
        return f"{prefix}{(max(nums)+1 if nums else 1):03d}"
    except Exception:
        return f"{prefix}001"


def _drive_list_pdf(dm, fid):
    files = []
    try:
        p = dict(
            q=f"'{fid}' in parents and trashed=false and mimeType='application/pdf'",
            fields="nextPageToken,files(id,name,webViewLink)",
            supportsAllDrives=True, includeItemsFromAllDrives=True, pageSize=500)
        while True:
            res = dm.drive_service.files().list(**p).execute()
            files.extend(res.get('files', []))
            tok = res.get('nextPageToken')
            if not tok: break
            p['pageToken'] = tok
    except Exception: pass
    return files


def _drive_list_sub(dm, fid):
    try:
        res = dm.drive_service.files().list(
            q=f"'{fid}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'",
            fields="files(id,name)", supportsAllDrives=True,
            includeItemsFromAllDrives=True, pageSize=200).execute()
        return sorted(res.get('files', []), key=lambda x: x.get('name', ''))
    except Exception: return []


def _discover_tree(dm, fid, fname, fpath, reg_ids, reg_names, by_fid,
                   self_level, parent_chain, depth=0, max_depth=8, sb=None):
    if depth > max_depth: return None
    if sb:
        s = fpath if len(fpath) < 72 else '…' + fpath[-70:]
        sb.caption(f"🔍 {s}")

    info       = by_fid.get(fid)
    registered = info is not None

    my_ids = dict(parent_chain)
    if registered and info:
        _, _, id_col, _, _, _ = LEVEL_META[self_level]
        my_ids[id_col] = info['id']

    files_new, sync_count = [], 0
    for f in _drive_list_pdf(dm, fid):
        fi    = f.get('id', '')
        fname2 = str(f.get('name', '')).lower().strip().replace('.pdf','').replace('.PDF','')
        if fi in reg_ids or fname2 in reg_names:
            sync_count += 1
        else:
            files_new.append({
                'id': fi, 'name': f.get('name', ''),
                'webViewLink': f.get('webViewLink', ''),
                'kat_id':  my_ids.get('kategori_id', ''),
                'bid_id':  my_ids.get('bidang_id', ''),
                'unit_id': my_ids.get('unit_id', ''),
                'sub_id':  my_ids.get('subkategori_id', ''),
                'folder_label': fpath,
            })

    child_level = LEVEL_NEXT.get(self_level)
    children, new_master = [], []

    if child_level:
        for sub in _drive_list_sub(dm, fid):
            si, sn = sub['id'], sub['name']
            sp = f"{fpath}/{sn}"
            sub_info = by_fid.get(si)
            sub_reg  = sub_info is not None

            child_chain = dict(my_ids)
            if registered and info:
                _, _, id_col, _, _, _ = LEVEL_META[self_level]
                child_chain[id_col] = info['id']

            if not sub_reg:
                new_master.append({
                    'id': si, 'name': sn, 'path': sp,
                    'level': child_level,
                    'parent_folder_id': fid,
                    'chain': {lv: (fid, v) for lv, v in child_chain.items()
                               if not isinstance(v, tuple)},
                })

            child = _discover_tree(
                dm, si, sn, sp, reg_ids, reg_names, by_fid,
                self_level=child_level, parent_chain=child_chain,
                depth=depth+1, max_depth=max_depth, sb=sb,
            )
            if child:
                children.append(child)
                new_master.extend(child.get('new_master', []))

    total_new  = len(files_new)  + sum(c['total_new']  for c in children)
    total_sync = sync_count      + sum(c['total_sync'] for c in children)

    return {
        'id': fid, 'name': fname, 'path': fpath,
        'self_level': self_level, 'registered': registered, 'info': info,
        'my_ids': my_ids,
        'files_new': files_new, 'files_sync_count': sync_count,
        'total_new': total_new, 'total_sync': total_sync,
        'total_files': total_new + total_sync,
        'children': children, 'new_master': new_master,
    }


def _collect_new_files(node):
    r = list(node.get('files_new', []))
    for c in node.get('children', []): r.extend(_collect_new_files(c))
    return r


def _write_master_entries(dm, items_by_level):
    import time as _t
    added, skipped_dup, errors = 0, 0, 0
    fid_to_id = {}

    # Pre-load existing folder_ids per sheet
    existing_fids = {}
    existing_ids  = {}
    for level in LEVEL_ORDER:
        _, sheet, id_col, _, _, _ = LEVEL_META[level]
        try:
            df = dm.get_master_data(sheet)
            fids = set(df['folder_id'].astype(str).str.strip()) if not df.empty and 'folder_id' in df.columns else set()
            ids  = set(df[id_col].astype(str).str.strip()) if not df.empty and id_col in df.columns else set()
        except Exception:
            fids, ids = set(), set()
        existing_fids[sheet] = fids
        existing_ids[sheet]  = ids

    for level in LEVEL_ORDER:
        lbl, sheet, id_col, nama_col, prefix, parent_col = LEVEL_META[level]
        items = items_by_level.get(level, [])
        if not items: continue

        for item in items:
            drive_fid = item['id']

            if drive_fid in existing_fids.get(sheet, set()):
                try:
                    df_tmp = dm.get_master_data(sheet)
                    if not df_tmp.empty and 'folder_id' in df_tmp.columns:
                        match = df_tmp[df_tmp['folder_id'].astype(str).str.strip() == drive_fid]
                        if not match.empty:
                            fid_to_id[drive_fid] = str(match.iloc[0][id_col]).strip()
                except Exception:
                    pass
                skipped_dup += 1
                continue

            new_id = _next_id(dm, level)
            while new_id in existing_ids.get(sheet, set()):
                num = int(new_id[len(prefix):]) + 1
                new_id = f"{prefix}{num:03d}"

            data = {
                id_col:      new_id,
                nama_col:    item['name'],
                'status':    'Aktif',
                'folder_id': drive_fid,
            }

            chain = item.get('chain', {})
            pfid  = item.get('parent_folder_id', '')

            if level == 'kat':
                mid = fid_to_id.get(pfid, '')
                if not mid:
                    me = chain.get('menu')
                    if me and isinstance(me, tuple): mid = me[1] or ''
                    elif me: mid = me or ''
                if mid: data['menu_id'] = mid

            elif level == 'bid':
                kid = fid_to_id.get(pfid, '')
                if not kid:
                    ke = chain.get('kat')
                    if ke and isinstance(ke, tuple): kid = ke[1] or ''
                    elif ke: kid = ke or ''
                data['kategori_id'] = kid
                data['has_unit']    = 'TRUE'

            elif level == 'unit':
                bid = fid_to_id.get(pfid, '')
                if not bid:
                    be = chain.get('bid')
                    if be and isinstance(be, tuple): bid = be[1] or ''
                    elif be: bid = be or ''
                data['bidang_id'] = bid
                ke = chain.get('kat')
                if ke and isinstance(ke, tuple) and ke[1]: data['kategori_id'] = ke[1]

            elif level == 'sub':
                uid = fid_to_id.get(pfid, '')
                if not uid:
                    ue = chain.get('unit')
                    if ue and isinstance(ue, tuple): uid = ue[1] or ''
                    elif ue: uid = ue or ''
                data['unit_id'] = uid
                be = chain.get('bid')
                if be and isinstance(be, tuple) and be[1]: data['bidang_id'] = be[1]
                ke = chain.get('kat')
                if ke and isinstance(ke, tuple) and ke[1]: data['kategori_id'] = ke[1]
                data['tipe'] = 'unit_level'

            ok = False
            for attempt in range(3):
                try:
                    ok = dm.add_master_data(sheet, data)
                    break
                except Exception as e:
                    if '429' in str(e) or 'Quota' in str(e):
                        _t.sleep((attempt + 1) * 15)
                    else:
                        break

            if ok:
                added += 1
                fid_to_id[drive_fid] = new_id
                existing_fids.setdefault(sheet, set()).add(drive_fid)
                existing_ids.setdefault(sheet,  set()).add(new_id)
                _t.sleep(1.5)
            else:
                errors += 1
                _t.sleep(3)

        if items: _t.sleep(5)

    return added, skipped_dup, errors


def _write_files_to_db(dm, cu, files, reg_ids, reg_names):
    import time as _t
    added, skipped, errors = 0, 0, 0
    n = len(files)
    prog, status = st.progress(0), st.empty()

    # Pre-load master data untuk enrichment kat_id dari bid
    # (fallback jika kat_id kosong karena folder kat tidak ada di by_fid)
    try:
        df_bid  = dm.get_master_data('bidang_id')
        df_unit = dm.get_master_data('unit_id')
        bid_to_kat  = {}  # bid_id → kat_id
        unit_to_bid = {}  # unit_id → bid_id
        unit_to_kat = {}  # unit_id → kat_id
        if not df_bid.empty and 'bidang_id' in df_bid.columns:
            for _, r in df_bid.iterrows():
                bid = str(r.get('bidang_id','')).strip()
                kat = str(r.get('kategori_id','')).strip()
                if bid and kat: bid_to_kat[bid] = kat
        if not df_unit.empty and 'unit_id' in df_unit.columns:
            for _, r in df_unit.iterrows():
                uid = str(r.get('unit_id','')).strip()
                bid = str(r.get('bidang_id','')).strip()
                kat = str(r.get('kategori_id','')).strip()
                if uid and bid: unit_to_bid[uid] = bid
                if uid and kat: unit_to_kat[uid] = kat
    except Exception:
        bid_to_kat, unit_to_bid, unit_to_kat = {}, {}, {}

    for i, f in enumerate(files):
        fid = f['id']
        nm  = str(f['name']).replace('.pdf', '').replace('.PDF', '').strip()
        nl  = nm.lower().strip()
        prog.progress((i+1)/n)
        status.caption(f"({i+1}/{n}) {nm[:65]}...")
        if fid in reg_ids or nl in reg_names: skipped += 1; continue

        # Ambil IDs dari file
        bid_id  = f.get('bid_id',  '') or ''
        unit_id = f.get('unit_id', '') or ''
        kat_id  = f.get('kat_id',  '') or ''
        sub_id  = f.get('sub_id',  '') or ''

        # Enrichment: isi kat_id dari master data jika kosong
        if not kat_id:
            if bid_id and bid_id in bid_to_kat:
                kat_id = bid_to_kat[bid_id]
            elif unit_id and unit_id in unit_to_kat:
                kat_id = unit_to_kat[unit_id]

        # Enrichment: isi bid_id dari unit jika kosong
        if not bid_id and unit_id and unit_id in unit_to_bid:
            bid_id = unit_to_bid[unit_id]

        data = {
            'nama_regulasi':    nm,
            'nomor_regulasi':   '',
            'jenis_regulasi':   _guess_jenis(f.get('folder_label', '')),
            'kategori_id':      kat_id,
            'bidang_id':        bid_id,
            'unit_id':          unit_id,
            'subkategori_id':   sub_id,
            'tanggal_terbit':   '',
            'tanggal_kadaluarsa': '',
            'google_drive_id':  fid,
            'google_drive_link': f"https://drive.google.com/file/d/{fid}/view",
            'status':           'aktif',
            'created_by':       cu.get('user_id', '') if cu else 'SYNC',
        }
        try:
            if dm.log_to_sheets(data):
                added += 1; reg_ids.add(fid); reg_names.add(nl)
                if added % 10 == 0: status.caption("⏸️ Jeda..."); _t.sleep(3)
            else: errors += 1
        except Exception: errors += 1; _t.sleep(2)
    prog.empty(); status.empty()
    return added, skipped, errors


def _show_banner(added, skipped, errors):
    c = "#d4edda" if not errors else "#fff3cd"
    st.markdown(
        f"<div style='background:{c};border-left:4px solid #28a745;"
        f"padding:9px 14px;border-radius:6px;margin:6px 0;'>"
        f"✅ <b>Selesai!</b>  📥 +{added}  ⏭️ {skipped} lewat"
        f"{'  ❌ ' + str(errors) + ' error' if errors else ''}"
        f"</div>", unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — SYNC MASTER DATA (struktur folder → meta data sheets)
# ═══════════════════════════════════════════════════════════════════════════

def _tab_sync_master(dm, cu):
    """Scan Drive → sinkronisasi struktur folder ke master data sheets SAJA."""
    st.markdown("#### 🗂️ Sinkronisasi Struktur Folder → Master Data")
    st.markdown("""
    <div style='background:#e8f4fd;border-left:3px solid #0d6efd;padding:9px 14px;
                border-radius:4px;font-size:13px;margin-bottom:14px'>
    Scan folder Drive → daftarkan folder baru ke
    <b>Menu / Kategori / Bidang / Unit / Subkategori</b>.<br>
    <span style='color:#555;font-size:12px;'>
    ✔ folder_id = kunci unik &nbsp;|&nbsp;
    ✔ parent chain otomatis &nbsp;|&nbsp;
    ✔ tidak duplikat walau dijalankan ulang
    </span></div>
    """, unsafe_allow_html=True)

    roots = _areg_roots(dm)
    opts  = {"🔁 Semua Folder AREG SOLO": "__ALL__"}
    opts.update({f"📁 {lbl}": fid for lbl, fid in roots if fid and 'GANTI' not in fid})

    c1, c2 = st.columns([2, 3])
    sel = c1.selectbox("Pilih folder:", list(opts.keys()), key="smaster_root")
    c2.info(f"⏱️ {'~2–5 menit' if sel=='🔁 Semua Folder AREG SOLO' else '~30–90 detik'}")

    if st.button("🔍 Scan Struktur Folder", type="primary", key="smaster_scan",
                 use_container_width=True):
        st.session_state.pop('smaster_trees', None)
        prog = st.progress(0, text="Memuat master data...")
        by_fid = _load_by_fid(dm)

        scan_targets = roots if sel == "🔁 Semua Folder AREG SOLO" else \
                       [(sel.replace("📁 ", ""), opts[sel])]

        sb, trees = st.empty(), []
        for i, (rl, rfid) in enumerate(scan_targets):
            prog.progress(10 + int(i/len(scan_targets)*87), text=f"Scanning {rl}...")
            node = _discover_tree(dm, rfid, rl, rl, set(), set(), by_fid,
                                  self_level="menu", parent_chain={},
                                  depth=0, max_depth=8, sb=sb)
            if node: trees.append(node)

        prog.progress(100); prog.empty(); sb.empty()
        st.session_state['smaster_trees'] = trees
        st.rerun()

    trees = st.session_state.get('smaster_trees')
    if not trees:
        st.info("Klik **🔍 Scan Struktur Folder** untuk melihat folder yang belum terdaftar.")
        return

    # Kumpulkan new_master per level
    items_by_level = {lv: [] for lv in LEVEL_ORDER}
    for t in trees:
        if not t['registered']:
            items_by_level['menu'].append({
                'id': t['id'], 'name': t['name'], 'path': t['path'],
                'level': 'menu', 'parent_folder_id': '', 'chain': {},
            })
        for item in t.get('new_master', []):
            lv = item.get('level', 'bid')
            items_by_level.setdefault(lv, []).append(item)

    n_per_level = {lv: len(items_by_level[lv]) for lv in LEVEL_ORDER}
    n_total = sum(n_per_level.values())

    st.markdown("---")

    if n_total == 0:
        st.success("🎉 Semua folder sudah terdaftar di master data!")
        return

    # Ringkasan
    parts = []
    for lv in LEVEL_ORDER:
        n = n_per_level[lv]
        if n: parts.append(
            f"<b style='color:{LEVEL_BADGE[lv]};'>{n} {LEVEL_META[lv][0]}</b>")
    st.markdown(
        f"<div style='background:#fff3cd;border-left:4px solid #ffc107;"
        f"padding:9px 14px;border-radius:6px;margin-bottom:10px;font-size:13px;'>"
        f"Folder baru ditemukan: {' + '.join(parts)}<br>"
        f"<span style='color:#666;font-size:12px;'>Urutan sync: Menu → Kategori → Bidang → Unit → Subkategori</span>"
        f"</div>", unsafe_allow_html=True
    )

    if st.button(f"⚡ Sync Semua Master Data ({n_total} folder)",
                 key="smaster_sync_all", type="primary", use_container_width=True):
        added_m, skip_m, err_m = _write_master_entries(dm, items_by_level)
        st.success(
            f"✅ Master data diperbarui! +{added_m} baru"
            + (f"  ⏭️ {skip_m} sudah ada" if skip_m else "")
            + (f"  ❌ {err_m} error" if err_m else "")
        )
        st.cache_data.clear()
        st.session_state.pop('smaster_trees', None)
        import time as _t; _t.sleep(1); st.rerun()

    # Detail tree
    for tree in trees:
        nm = tree.get('new_master', [])
        root_unreg = not tree.get('registered')
        if not nm and not root_unreg: continue

        with st.expander(
            f"{'🆕 ' if root_unreg else '📁 '}{tree['name']} ({len(nm)} folder baru)",
            expanded=True
        ):
            if root_unreg:
                st.markdown(
                    f"<div style='padding:2px 0 6px 0;font-size:13px;'>"
                    f"🔴 <b>{tree['name']}</b> "
                    f"<span style='background:{LEVEL_BADGE['menu']};color:white;"
                    f"border-radius:8px;padding:1px 7px;font-size:11px;font-weight:700;'>"
                    f"Menu Baru</span></div>",
                    unsafe_allow_html=True
                )
            _render_master_tree(tree)


def _render_master_tree(node, indent=0):
    for child in node.get('children', []):
        lv  = child.get('self_level', 'kat')
        reg = child.get('registered', True)
        dot = "🔴" if not reg else "✅"
        col = LEVEL_BADGE.get(lv, '#aaa')
        lbl = LEVEL_META.get(lv, ('?',)*6)[0]
        badge = (
            f"<span style='background:{col};color:white;border-radius:8px;"
            f"padding:1px 6px;font-size:11px;font-weight:700;margin-left:4px;'>"
            f"{lbl} Baru</span>"
        ) if not reg else (
            f"<span style='color:#aaa;font-size:11px;'> ({child.get('info',{}).get('id','') if child.get('info') else ''})</span>"
        )
        st.markdown(
            f"<div style='padding:2px 0 2px {indent*18}px;font-size:13px;'>"
            f"{dot} <b>{child['name']}</b>{badge}</div>",
            unsafe_allow_html=True
        )
        _render_master_tree(child, indent+1)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — SYNC FILE (hierarchical dropdown dari master data)
# ═══════════════════════════════════════════════════════════════════════════

def _tab_sync_file(dm, cu):
    """Sinkronisasi file PDF ke rekap_database via hierarchical folder picker."""
    st.markdown("#### 📄 Sinkronisasi File ke Database")
    st.markdown(
        "<div style='background:#e8f4fd;border-left:3px solid #0d6efd;"
        "padding:9px 14px;border-radius:4px;font-size:13px;margin-bottom:14px;'>"
        "Pilih folder secara bertingkat (Menu → Kategori → Bidang → Unit), "
        "lalu scan file PDF yang belum terdaftar.<br>"
        "<span style='color:#555;font-size:12px;'>"
        "Hanya folder yang sudah terdaftar di master data yang bisa dipilih.</span>"
        "</div>",
        unsafe_allow_html=True
    )

    # Load semua master data
    def _get(sheet):
        try: return dm.get_master_data(sheet)
        except: return pd.DataFrame()

    # Cache master data di session_state supaya tidak query ulang setiap rerun
    if 'fsync_master_cache' not in st.session_state:
        st.session_state['fsync_master_cache'] = {}
    _mc = st.session_state['fsync_master_cache']

    # Tombol reset cache (jika data terlihat salah)
    if st.button("🔄 Refresh Data Master", key="fsync_refresh_cache",
                 type="secondary", help="Klik jika dropdown tidak muncul/salah"):
        st.session_state['fsync_master_cache'] = {}
        # Hapus juga cache subfolder Drive
        for k in list(st.session_state.keys()):
            if k.startswith('_drive_subs_'):
                del st.session_state[k]
        st.rerun()

    def _get_cached(sheet):
        # Load jika belum ada atau sebelumnya kosong (mungkin karena 429)
        if sheet not in _mc or _mc[sheet].empty:
            try:
                df_loaded = dm.get_master_data(sheet)
                _mc[sheet] = df_loaded
            except Exception:
                if sheet not in _mc:
                    _mc[sheet] = pd.DataFrame()
        return _mc[sheet]

    df_menu = _get_cached('menu_id')
    df_kat  = _get_cached('kategori_id')
    df_bid  = _get_cached('bidang_id')
    df_unit = _get_cached('unit_id')
    # df_sub hanya diload kalau unit sudah dipilih (hemat quota)
    df_sub  = pd.DataFrame()   # placeholder

    # Build parent-child maps dari folder_id hierarchy
    # Setiap entry di kategori_id harus punya parent = salah satu folder menu
    # Cara filter: cek parent folder Drive dari tiap kategori folder_id
    # → tapi mahal (API call). Alternatif: filter via kolom parent_id jika ada,
    #   atau via Drive folder ID intersection.

    def _opts_all(df, id_col, nama_col):
        """Semua entri sebagai opts dict."""
        opts = {"📁 Semua": "__ALL__"}
        if df.empty: return opts
        for _, r in df.iterrows():
            fid  = str(r.get('folder_id','')).strip()
            rid  = str(r.get(id_col,'')).strip()
            nam  = str(r.get(nama_col,'')).strip()
            if not fid or fid in ('nan','None',''): continue
            opts[f"{nam}  ({rid})"] = fid
        return opts

    def _opts_by_parent_fid(df, id_col, nama_col, parent_fid):
        """
        Filter entri yang folder_id-nya adalah subfolder langsung dari parent_fid.
        Dua cara:
        1. Kolom parent_id di sheet (jika ada dan terisi)
        2. Cek via Drive subfolder list (fallback, akurat)
        """
        if not parent_fid or parent_fid == "__ALL__":
            return _opts_all(df, id_col, nama_col)
        if df.empty:
            return {"📁 Semua": "__ALL__"}

        # Ambil semua folder_id yang ada di df
        all_fids = set(df['folder_id'].astype(str).str.strip().tolist()) if 'folder_id' in df.columns else set()
        if not all_fids:
            return _opts_all(df, id_col, nama_col)

        # Ambil subfolder langsung dari Drive (cached per parent_fid)
        cache_key = f"_drive_subs_{parent_fid}"
        if cache_key not in st.session_state:
            subs = _drive_list_sub(dm, parent_fid)
            st.session_state[cache_key] = {s['id'] for s in subs}
        valid_fids = st.session_state[cache_key]

        # Filter df: hanya yang folder_id-nya ada di subfolder parent
        matched_fids = all_fids & valid_fids
        if not matched_fids:
            # Tidak ada match dari Drive → fallback ke kolom parent di sheet
            return _opts_all(df, id_col, nama_col)

        opts = {"📁 Semua": "__ALL__"}
        for _, r in df.iterrows():
            fid  = str(r.get('folder_id','')).strip()
            rid  = str(r.get(id_col,'')).strip()
            nam  = str(r.get(nama_col,'')).strip()
            if fid not in matched_fids: continue
            opts[f"{nam}  ({rid})"] = fid
        return opts

    # ── Level 1: Menu ─────────────────────────────────────────────────────
    st.markdown("**📂 Pilih Folder Target**")
    menu_opts = _opts_all(df_menu, 'menu_id', 'nama_menu')

    col1, col2 = st.columns(2)
    sel_menu_lbl = col1.selectbox("Menu", list(menu_opts.keys()), key="fsync_menu")
    sel_menu_fid = menu_opts[sel_menu_lbl]

    # ── Level 2: Kategori — filter by subfolder Drive dari menu folder ────
    kat_opts = _opts_by_parent_fid(df_kat, 'kategori_id', 'nama_kategori', sel_menu_fid)
    sel_kat_lbl = col2.selectbox("Kategori", list(kat_opts.keys()), key="fsync_kat")
    sel_kat_fid = kat_opts[sel_kat_lbl]

    sel_kat_id = ''
    if sel_kat_fid != "__ALL__" and not df_kat.empty:
        krow = df_kat[df_kat['folder_id'].astype(str) == sel_kat_fid]
        if not krow.empty:
            sel_kat_id = str(krow.iloc[0].get('kategori_id', '')).strip()

    # ── Level 3: Bidang — filter by subfolder Drive dari kat folder ───────
    col3, col4 = st.columns(2)
    bid_opts = _opts_by_parent_fid(df_bid, 'bidang_id', 'nama_bidang', sel_kat_fid)
    sel_bid_lbl = col3.selectbox("Bidang", list(bid_opts.keys()), key="fsync_bid")
    sel_bid_fid = bid_opts[sel_bid_lbl]

    sel_bid_id = ''
    if sel_bid_fid != "__ALL__" and not df_bid.empty:
        brow = df_bid[df_bid['folder_id'].astype(str) == sel_bid_fid]
        if not brow.empty:
            sel_bid_id = str(brow.iloc[0].get('bidang_id', '')).strip()

    # ── Level 4: Unit — filter by subfolder Drive dari bid folder ─────────
    unit_opts = _opts_by_parent_fid(df_unit, 'unit_id', 'nama_unit', sel_bid_fid)
    sel_unit_lbl = col4.selectbox("Unit", list(unit_opts.keys()), key="fsync_unit")
    sel_unit_fid = unit_opts[sel_unit_lbl]

    sel_unit_id = ''
    if sel_unit_fid != "__ALL__" and not df_unit.empty:
        urow = df_unit[df_unit['folder_id'].astype(str) == sel_unit_fid]
        if not urow.empty:
            sel_unit_id = str(urow.iloc[0].get('unit_id', '')).strip()

    # ── Level 5: Subkategori (filter by subfolder Drive dari unit folder) ──
    col5, _ = st.columns(2)
    # Load subkategori hanya kalau unit sudah dipilih (hemat API quota)
    if sel_unit_fid and sel_unit_fid != "__ALL__":
        # Coba load dari sheet, tapi jangan crash kalau 429
        try:
            df_sub = _get_cached('subkategori_id')
        except Exception:
            df_sub = pd.DataFrame()

        # Ambil subfolder Drive dari unit folder (cached)
        cache_key = f"_drive_subs_{sel_unit_fid}"
        if cache_key not in st.session_state:
            subs = _drive_list_sub(dm, sel_unit_fid)
            st.session_state[cache_key] = subs
        drive_subs = st.session_state.get(cache_key, [])

        if drive_subs:
            # Tampilkan subfolder Drive + cocokkan ke sheet jika ada
            sub_fid_to_info = {}
            if not df_sub.empty and 'folder_id' in df_sub.columns:
                for _, r in df_sub.iterrows():
                    fid = str(r.get('folder_id','')).strip()
                    sid = str(r.get('subkategori_id','')).strip()
                    nam = str(r.get('nama_subkategori','')).strip()
                    if fid: sub_fid_to_info[fid] = (sid, nam)

            sub_opts = {"📁 Semua": "__ALL__"}
            for s in drive_subs:
                sfid  = s['id']
                sname = s['name']
                if sfid in sub_fid_to_info:
                    sid, snam = sub_fid_to_info[sfid]
                    sub_opts[f"{snam}  ({sid})"] = sfid
                else:
                    # Subfolder belum terdaftar di sheet → tampilkan dari Drive
                    sub_opts[f"📂 {sname}  (belum terdaftar)"] = sfid
        else:
            sub_opts = {"📁 Semua": "__ALL__"}

        if len(sub_opts) <= 1:
            col5.caption("(tidak ada subfolder)")
    else:
        sub_opts = {"📁 Semua": "__ALL__"}
    sel_sub_lbl = col5.selectbox("Subkategori", list(sub_opts.keys()), key="fsync_sub")
    sel_sub_fid = sub_opts[sel_sub_lbl]

    # ── Tentukan folder target scan ───────────────────────────────────────
    # Prioritas: sub > unit > bid > kat > menu > semua
    target_fid, target_lbl, t_kat_id, t_bid_id, t_unit_id = "__ALL__", "Semua Folder", '', '', ''
    for fid_sel, lbl_sel, df_src, id_col, kat_col, bid_col, uid_col in [
        (sel_sub_fid,  sel_sub_lbl,  df_sub,  'subkategori_id', 'kategori_id', 'bidang_id', 'unit_id'),
        (sel_unit_fid, sel_unit_lbl, df_unit, 'unit_id',         'kategori_id', 'bidang_id', None),
        (sel_bid_fid,  sel_bid_lbl,  df_bid,  'bidang_id',        'kategori_id', None,        None),
        (sel_kat_fid,  sel_kat_lbl,  df_kat,  'kategori_id',      None,          None,        None),
        (sel_menu_fid, sel_menu_lbl, df_menu, 'menu_id',           None,          None,        None),
    ]:
        if fid_sel and fid_sel != "__ALL__":
            target_fid, target_lbl = fid_sel, lbl_sel.split('  (')[0].strip()
            if not df_src.empty and 'folder_id' in df_src.columns:
                row = df_src[df_src['folder_id'].astype(str) == fid_sel]
                if not row.empty:
                    if kat_col and kat_col in row.columns:
                        t_kat_id  = str(row.iloc[0].get(kat_col, '')).strip()
                    if bid_col and bid_col in row.columns:
                        t_bid_id  = str(row.iloc[0].get(bid_col, '')).strip()
                    if uid_col and uid_col in row.columns:
                        t_unit_id = str(row.iloc[0].get(uid_col, '')).strip()
            break

    if target_fid == "__ALL__":
        st.info("🔍 Target: **Semua Folder AREG SOLO**")
    else:
        st.success(f"🎯 Target: **{target_lbl}**")

    # ── Tombol Scan ───────────────────────────────────────────────────────
    if st.button("🔍 Scan Folder", type="primary", key="fsync_scan",
                 use_container_width=True):
        st.session_state.pop('fsync_result', None)
        prog = st.progress(0, text="Memuat database...")
        try: existing = dm.get_all_documents() or []
        except Exception: existing = []

        reg_ids   = {str(r.get('google_drive_id','')).strip() for r in existing}
        reg_names = {
            str(r.get('nama_regulasi','')).lower().strip()
             .replace('.pdf','').replace('.docx','').replace('.doc','')
            for r in existing if str(r.get('nama_regulasi','')) not in ('','nan','None')
        }

        by_fid = _load_by_fid(dm)
        prog.progress(20, text="Scanning Drive...")
        sb = st.empty()

        if target_fid == "__ALL__":
            roots = _areg_roots(dm)
            trees = []
            for i, (rl, rfid) in enumerate(roots):
                prog.progress(20 + int(i/len(roots)*75), text=f"Scanning {rl}...")
                node = _discover_tree(dm, rfid, rl, rl, reg_ids, reg_names, by_fid,
                                      self_level="menu", parent_chain={},
                                      depth=0, max_depth=8, sb=sb)
                if node: trees.append(node)
        else:
            # Tentukan self_level dari folder target
            target_level = "sub"  # default paling dalam
            for lv in LEVEL_ORDER:
                _, sheet, id_col, _, _, _ = LEVEL_META[lv]
                try:
                    df_t = dm.get_master_data(sheet)
                    if not df_t.empty and 'folder_id' in df_t.columns:
                        if target_fid in df_t['folder_id'].astype(str).values:
                            target_level = lv; break
                except Exception:
                    pass

            init_chain = {}
            if t_kat_id:  init_chain['kategori_id'] = t_kat_id
            if t_bid_id:  init_chain['bidang_id']   = t_bid_id
            if t_unit_id: init_chain['unit_id']      = t_unit_id

            prog.progress(40, text=f"Scanning {target_lbl}...")
            node = _discover_tree(
                dm, target_fid, target_lbl, target_lbl,
                reg_ids, reg_names, by_fid,
                self_level=target_level, parent_chain=init_chain,
                depth=0, max_depth=8, sb=sb,
            )
            trees = [node] if node else []

        prog.progress(100); prog.empty(); sb.empty()

        all_new = []
        for t in trees: all_new.extend(_collect_new_files(t))
        total_sync = sum(t['total_sync'] for t in trees)

        st.session_state['fsync_result'] = {
            'trees':      trees,
            'new_files':  all_new,
            'reg_ids':    reg_ids,
            'reg_names':  reg_names,
            'total_sync': total_sync,
            'total_new':  len(all_new),
            'scanned_at': datetime.now().strftime('%d %b %Y %H:%M'),
            'target':     target_lbl,
        }
        st.rerun()

    # ── Tampilkan hasil ───────────────────────────────────────────────────
    res = st.session_state.get('fsync_result')
    if not res: return

    trees      = res['trees']
    new_files  = res['new_files']
    reg_ids    = res['reg_ids']
    reg_names  = res['reg_names']
    total_sync = res['total_sync']
    total_new  = res['total_new']
    grand_total = total_sync + total_new
    pct = int(total_sync/grand_total*100) if grand_total else 0

    st.markdown("---")
    st.caption(f"🎯 {res['target']}  •  Scan: {res['scanned_at']}")

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("📂 File di Drive", grand_total)
    mc2.metric("✅ Sudah Sinkron", total_sync, delta=f"{pct}%", delta_color="normal")
    mc3.metric("❗ Belum Sinkron", total_new,
               delta=f"{100-pct}% belum",
               delta_color="inverse" if total_new > 0 else "off")

    if grand_total:
        bc = "#198754" if pct==100 else "#fd7e14" if pct>=50 else "#dc3545"
        st.markdown(
            f"<div style='background:#e9ecef;border-radius:8px;height:10px;"
            f"margin:6px 0 14px;overflow:hidden;'>"
            f"<div style='background:{bc};width:{pct}%;height:100%;border-radius:8px;'>"
            f"</div></div>", unsafe_allow_html=True
        )

    if total_new == 0:
        st.success("🎉 Semua file di folder ini sudah sinkron!"); return

    st.markdown(f"### ❗ {total_new} File Belum Terdaftar")

    with st.expander("🔍 Preview file (maks 100)", expanded=False):
        rows = [{'Nama File': f['name'], 'Folder': f.get('folder_label',''),
                 'kat_id': f.get('kat_id','') or '⚠️', 'bid_id': f.get('bid_id','') or '-'}
                for f in new_files[:100]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if total_new > 100: st.caption(f"_(+{total_new-100} lagi)_")

    if st.button(f"⚡ Sinkronisasi Semua ({total_new} file)",
                 type="primary", key="fsync_all", use_container_width=True):
        added, sk, err = _write_files_to_db(dm, cu, new_files, reg_ids, reg_names)
        _show_banner(added, sk, err)
        st.session_state.pop('fsync_result', None)
        import time as _t; _t.sleep(1); st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='font-size:12px;color:#888;margin-bottom:8px;'>"
        "🟢 sinkron | 🟡 sebagian | 🔴 semua belum | ⬜ kosong</div>",
        unsafe_allow_html=True
    )
    for tree in trees:
        nu, ns, tot = tree['total_new'], tree['total_sync'], tree['total_files']
        dot = "🟢" if nu==0 and ns>0 else "🔴" if ns==0 and nu>0 else "🟡" if nu>0 else "⬜"
        with st.expander(
            f"{dot} {tree['name']}  —  {tot} file, ✔ {ns}"
            + (f", ❗ {nu} belum" if nu else ""),
            expanded=(nu > 0)
        ):
            if tot == 0: st.caption("_(kosong)_"); continue
            rn = _collect_new_files(tree)
            if rn:
                if st.button(f"⚡ Sync ({len(rn)} file)",
                             key=f"fs_root_{tree['id']}", type="secondary"):
                    added, sk, err = _write_files_to_db(dm, cu, rn, reg_ids, reg_names)
                    _show_banner(added, sk, err)
                    st.session_state.pop('fsync_result', None)
                    import time as _t; _t.sleep(1); st.rerun()
            for child in tree.get('children', []):
                _render_file_row(child, dm, cu, reg_ids, reg_names, indent=0)


def _render_file_row(node, dm, cu, reg_ids, reg_names, indent=0):
    nu, ns, tot = node['total_new'], node['total_sync'], node['total_files']
    dot = "🟢" if nu==0 and ns>0 else "🔴" if ns==0 and nu>0 else "🟡" if nu>0 else "⬜"
    st.markdown(
        f"<div style='margin-left:{indent*18}px;padding:2px 0;font-size:13px;'>"
        f"{dot} <b>{node['name']}</b>"
        f"<span style='color:#666;font-size:12px;'> ✔{ns}/{tot}</span>"
        + (f"<span style='color:#dc3545;font-size:12px;font-weight:700;'> +{nu} belum</span>"
           if nu else "")
        + "</div>", unsafe_allow_html=True
    )
    all_new = _collect_new_files(node)
    if all_new:
        cb, ci = st.columns([2, 5])
        with cb:
            if st.button(f"⚡ Sync ({len(all_new)})",
                         key=f"fs_{node['id']}", type="secondary"):
                added, sk, err = _write_files_to_db(dm, cu, all_new, reg_ids, reg_names)
                _show_banner(added, sk, err)
                st.session_state.pop('fsync_result', None)
                import time as _t; _t.sleep(1); st.rerun()
        with ci:
            if node.get('children'): st.caption(f"termasuk {len(node['children'])} subfolder")
    if node['files_new']:
        with st.expander(f"📄 {len(node['files_new'])} file baru di '{node['name']}'",
                         expanded=False):
            for f in node['files_new']:
                lnk, nm = f.get('webViewLink',''), f.get('name','')
                st.markdown(f"&nbsp;&nbsp;↳ [{nm}]({lnk})" if lnk else f"&nbsp;&nbsp;↳ {nm}")
    for child in node.get('children', []):
        _render_file_row(child, dm, cu, reg_ids, reg_names, indent+1)
    if indent == 0:
        st.markdown("<hr style='margin:4px 0;border-color:#eee;'>", unsafe_allow_html=True)


def _scan_drive_recursive(dm, folder_id, rekursif=True, folder_path="", depth=0):
    """Scan folder Drive secara rekursif, kembalikan list file PDF."""
    if depth > 8:  # batas kedalaman
        return []

    all_files = []
    try:
        # Ambil file PDF di folder ini
        query_files = (f"'{folder_id}' in parents and trashed=false "
                       f"and mimeType='application/pdf'")
        res = dm.drive_service.files().list(
            q=query_files,
            fields="files(id, name, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=200
        ).execute()
        for f in res.get('files', []):
            f['folder_path'] = folder_path
            all_files.append(f)

        # Rekursif ke subfolder
        if rekursif:
            query_folders = (f"'{folder_id}' in parents and trashed=false "
                             f"and mimeType='application/vnd.google-apps.folder'")
            res_f = dm.drive_service.files().list(
                q=query_folders,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=100
            ).execute()
            for sub in res_f.get('files', []):
                sub_path = f"{folder_path}/{sub['name']}" if folder_path else sub['name']
                all_files.extend(_scan_drive_recursive(dm, sub['id'], rekursif,
                                                        sub_path, depth+1))
    except Exception:
        pass
    return all_files


def _guess_jenis(folder_path):
    """Tebak jenis regulasi dari nama folder."""
    p = folder_path.upper()
    if 'SPO' in p: return 'SPO'
    if 'KEBIJAKAN' in p: return 'Kebijakan'
    if 'PANDUAN' in p or 'PEDOMAN' in p: return 'Panduan'
    if 'SK ' in p or 'SURAT' in p: return 'SK (Surat Keputusan)'
    if 'PROGRAM' in p or 'PAK' in p: return 'Program Kerja'
    return 'SPO'


def _guess_bidang(folder_path):
    """Tebak bidang dari path folder."""
    return folder_path.split('/')[0] if folder_path else ''


def _tab_folder_list(dm):
    st.markdown("#### 📋 Folder di Google Drive A-REG Solo")

    if st.button("🔄 Refresh", key="ref_folders", type="secondary"):
        st.rerun()

    with st.spinner("Memuat folder..."):
        subfolders = dm.list_subfolders(dm.DRIVE_FOLDER_ID)

    if not subfolders:
        st.info("Belum ada subfolder.")
        return

    st.markdown(f"**{len(subfolders)} folder:**")
    for f in subfolders:
        fc1, fc2 = st.columns([5, 2])
        with fc1:
            st.markdown(f"📁 **{f['name']}**")
        with fc2:
            st.link_button("🔗 Buka Drive",
                           f"https://drive.google.com/drive/folders/{f['id']}",
                           use_container_width=True, type="secondary")


def _tab_folder_create(dm):
    st.markdown("#### ➕ Buat Folder Baru")
    st.caption("Folder dengan nama yang sama tidak akan dibuat ulang.")

    with st.form("form_folder"):
        folder_name  = st.text_input("Nama Folder *", placeholder="Contoh: 01. KEBIJAKAN")
        parent_label = st.selectbox("Buat di", ["Root A-REG Solo", "Di dalam Ratifikasi_Draft"])
        submitted    = st.form_submit_button("➕ Buat Folder", type="primary")

    if submitted and folder_name.strip():
        parent_id = dm.DRIVE_FOLDER_ID
        if parent_label == "Di dalam Ratifikasi_Draft":
            parent_id = dm.get_or_create_ratifikasi_folder() or parent_id

        existing = dm.list_subfolders(parent_id) or []
        if any(f['name'] == folder_name.strip() for f in existing):
            st.warning(f"⚠️ Folder **{folder_name}** sudah ada.")
        else:
            try:
                meta = {'name': folder_name.strip(),
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [parent_id]}
                res = dm.drive_service.files().create(
                    body=meta, fields='id', supportsAllDrives=True
                ).execute()
                st.success(f"✅ Folder **{folder_name}** dibuat!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal: {e}")




# ============================================================
# HELPERS
# ============================================================

def _build_user_options(users):
    result = {}
    for u in users:
        if str(u.get('status','')).lower() != 'aktif': continue
        email = str(u.get('email','')).strip()
        if not email or '@' not in email: continue
        nama  = str(u.get('nama_lengkap','')).strip()
        unit  = str(u.get('unit_kerja','')).strip()
        label = f"{nama} — {unit}" if unit else nama
        if label: result[label] = email
    return result


def _build_manajer_options(users, bid_nama=''):
    result, all_mgmt = {}, {}
    for u in users:
        if str(u.get('status','')).lower() != 'aktif': continue
        if str(u.get('role','')).strip() != 'Managemen': continue
        email = str(u.get('email','')).strip()
        if not email or '@' not in email: continue
        nama  = str(u.get('nama_lengkap','')).strip()
        unit  = str(u.get('unit_kerja','')).strip()
        label = f"{nama} — {unit}" if unit else nama
        if not label: continue
        all_mgmt[label] = email
        if bid_nama and bid_nama.lower() in unit.lower():
            result[label] = email
    return result if result else all_mgmt


def _gen_id(existing_list):
    if not existing_list: return 'RAT001'
    nums = [int(r['id_ratifikasi'][3:]) for r in existing_list
            if str(r.get('id_ratifikasi','')).startswith('RAT')
            and str(r.get('id_ratifikasi',''))[3:].isdigit()]
    return f"RAT{(max(nums)+1 if nums else 1):03d}"