# modules/dashboard.py
"""
Dashboard Module untuk AREG SOLO
Tampilan modern mirip DocRS
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from utils.google_drive_manager import get_drive_manager
from utils.auth_manager import get_auth_manager


def show():
    dm = get_drive_manager()
    auth = get_auth_manager(dm)
    current_user = auth.get_current_user()

    nama = current_user.get('nama_lengkap', 'User') if current_user else 'User'
    role = current_user.get('role', '') if current_user else ''

    # Load data
    with st.spinner("Memuat data..."):
        docs    = dm.get_all_documents() or []
        df_kat  = dm.get_master_data('kategori_id')

    df = pd.DataFrame(docs).fillna('') if docs else pd.DataFrame()

    # Hitung statistik
    total_dok   = len(df)
    n_aktif     = len(df[df.get('status', pd.Series(dtype=str)).str.lower() == 'aktif']) if not df.empty and 'status' in df.columns else 0
    n_kadaluarsa = 0
    n_dekat     = 0
    today = date.today()

    if not df.empty and 'tanggal_kadaluarsa' in df.columns:
        for _, row in df.iterrows():
            tgl_k_str = str(row.get('tanggal_kadaluarsa', '')).strip()
            if not tgl_k_str or tgl_k_str in ('nan', 'None', ''):
                continue
            try:
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d-%b-%Y', '%d %b %Y', '%-d-%b-%Y'):
                    try:
                        tgl_k = datetime.strptime(tgl_k_str, fmt).date()
                        break
                    except:
                        tgl_k = None
                if tgl_k:
                    if tgl_k < today:
                        n_kadaluarsa += 1
                    elif tgl_k <= today + timedelta(days=180):
                        n_dekat += 1
            except:
                pass

    # Distribusi per kategori
    kat_dist = {}
    if not df.empty and 'kategori_id' in df.columns and not df_kat.empty:
        kat_map = {}
        if 'kategori_id' in df_kat.columns and 'nama_kategori' in df_kat.columns:
            for _, r in df_kat.iterrows():
                kat_map[str(r['kategori_id'])] = str(r['nama_kategori'])
        for kid, grp in df.groupby('kategori_id'):
            nama_kat = kat_map.get(str(kid), str(kid))
            kat_dist[nama_kat] = len(grp)
    kat_dist_sorted = dict(sorted(kat_dist.items(), key=lambda x: -x[1])[:6])

    # Dokumen terbaru (5 terakhir aktif)
    df_terbaru = pd.DataFrame()
    if not df.empty:
        df_aktif = df[df.get('status', pd.Series(dtype=str)).str.lower().isin(['aktif', 'draft'])]
        if 'created_at' in df_aktif.columns:
            df_aktif = df_aktif.sort_values('created_at', ascending=False)
        df_terbaru = df_aktif.head(5)

    # ===== CSS =====
    hari_map = {0:'Senin',1:'Selasa',2:'Rabu',3:'Kamis',4:'Jumat',5:'Sabtu',6:'Minggu'}
    bln_map  = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'Mei',6:'Jun',
                7:'Jul',8:'Agu',9:'Sep',10:'Okt',11:'Nov',12:'Des'}
    tgl_str  = f"{hari_map[today.weekday()]}, {today.day} {bln_map[today.month]} {today.year}"

    st.markdown("""
    <style>
    /* ── Global ── */
    [data-testid="stAppViewContainer"] { background: #f4f6f9; }
    .block-container { max-width: 100% !important; }
    h1,h2,h3,h4 { font-family: 'Segoe UI', sans-serif !important; }

    /* ── Header strip ── */
    .dash-header {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 1.2rem;
    }
    .dash-header-left h1 {
        font-size: 28px; font-weight: 700; color: #1a1a2e; margin: 0;
    }
    .dash-header-left p { font-size: 13px; color: #888; margin: 2px 0 0 0; }

    /* ── Alert banner ── */
    .alert-banner {
        background: #fff8e1; border: 1px solid #ffe082; border-radius: 10px;
        padding: 12px 20px; display: flex; align-items: center; gap: 12px;
        margin-bottom: 1.4rem; font-size: 14px; color: #5d4037;
    }
    .alert-banner .alert-icon { font-size: 18px; }
    .alert-banner .alert-text { flex: 1; }
    .alert-banner .alert-link { color: #00a859; font-weight: 600; cursor: pointer; white-space: nowrap; }

    /* ── Metric cards ── */
    .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 1.4rem; }
    .metric-card {
        background: white; border-radius: 12px; padding: 20px 22px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07); border: 1px solid #e8ecf0;
        position: relative; overflow: hidden;
    }
    .metric-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    }
    .metric-card.green::before  { background: #00a859; }
    .metric-card.blue::before   { background: #1565c0; }
    .metric-card.purple::before { background: #6a1b9a; }
    .metric-card.orange::before { background: #e65100; }
    .metric-card .mc-label { font-size: 11px; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }
    .metric-card .mc-value { font-size: 38px; font-weight: 800; line-height: 1; margin-bottom: 6px; }
    .metric-card.green  .mc-value { color: #00a859; }
    .metric-card.blue   .mc-value { color: #1565c0; }
    .metric-card.purple .mc-value { color: #6a1b9a; }
    .metric-card.orange .mc-value { color: #e65100; }
    .metric-card .mc-sub { font-size: 12px; color: #888; }
    .metric-card .mc-sub .warn { color: #f57c00; font-weight: 600; }

    /* ── Two-column panels ── */
    .panel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .panel {
        background: white; border-radius: 12px; padding: 20px 22px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07); border: 1px solid #e8ecf0;
    }
    .panel-header {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 14px;
    }
    .panel-title { font-size: 15px; font-weight: 700; color: #1a1a2e; }
    .panel-link  { font-size: 12px; color: #00a859; font-weight: 600; cursor: pointer; }

    /* ── Doc list ── */
    .doc-item {
        display: flex; align-items: center; gap: 12px;
        padding: 9px 0; border-bottom: 1px solid #f0f0f0;
    }
    .doc-item:last-child { border-bottom: none; }
    .doc-badge {
        font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px;
        white-space: nowrap; min-width: 52px; text-align: center;
    }
    .badge-spo      { background:#e3f2fd; color:#1565c0; }
    .badge-kebijakan{ background:#e8f5e9; color:#2e7d32; }
    .badge-ppk      { background:#f3e5f5; color:#6a1b9a; }
    .badge-pedoman  { background:#fff3e0; color:#e65100; }
    .badge-pak      { background:#fce4ec; color:#c62828; }
    .badge-lain     { background:#f5f5f5; color:#555; }
    .doc-info { flex: 1; min-width: 0; }
    .doc-name { font-size: 13px; font-weight: 600; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .doc-unit { font-size: 11px; color: #999; margin-top: 1px; }

    /* ── Bar chart ── */
    .bar-item { margin-bottom: 12px; }
    .bar-header { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
    .bar-name  { color: #333; font-weight: 500; }
    .bar-count { font-weight: 700; }
    .bar-track { background: #f0f0f0; border-radius: 4px; height: 7px; }
    .bar-fill  { height: 7px; border-radius: 4px; }

    /* ── Upload button ── */
    .upload-btn {
        background: linear-gradient(135deg,#00a859,#008547);
        color: white; padding: 10px 22px; border-radius: 8px;
        font-size: 14px; font-weight: 600; border: none; cursor: pointer;
        display: inline-flex; align-items: center; gap: 6px;
    }

    /* ── Welcome card ── */
    .welcome-strip {
        background: linear-gradient(135deg,#00a859 0%,#006e3a 100%);
        border-radius: 12px; padding: 16px 24px; margin-bottom: 1.4rem;
        display: flex; align-items: center; justify-content: space-between; color: white;
    }
    .welcome-strip .wl { font-size: 18px; font-weight: 700; }
    .welcome-strip .ws { font-size: 12px; opacity: .85; margin-top: 3px; }
    .welcome-strip .wr { text-align: right; font-size: 12px; opacity: .9; }
    </style>
    """, unsafe_allow_html=True)

    # ===== HEADER =====
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"""
        <div class="dash-header-left">
            <h1>📊 Dashboard</h1>
            <p>Selamat datang, <b>{nama}</b> &nbsp;·&nbsp; {tgl_str}</p>
        </div>""", unsafe_allow_html=True)
    with col_h2:
        pass

    # ===== ALERT BANNER (kadaluarsa) =====
    if n_dekat > 0:
        st.markdown(f"""
        <div class="alert-banner">
            <span class="alert-icon">⚠️</span>
            <span class="alert-text">
                <b>{n_dekat} dokumen akan kadaluarsa dalam 30–180 hari</b>
                &nbsp;— segera perbarui atau hubungi pihak terkait
            </span>
        </div>""", unsafe_allow_html=True)

    # ===== METRIC CARDS =====
    sub_aktif  = f'<span class="warn">⚠️ {n_kadaluarsa} kadaluarsa</span>' if n_kadaluarsa else f'✅ Semua dokumen aktif'
    sub_dekat  = f'{n_dekat} akan kadaluarsa' if n_dekat else 'Tidak ada yang mendekati'

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card green">
            <div class="mc-label">Total Regulasi</div>
            <div class="mc-value">{total_dok}</div>
            <div class="mc-sub">{n_aktif} dokumen aktif</div>
        </div>
        <div class="metric-card orange">
            <div class="mc-label">Mendekati Kadaluarsa</div>
            <div class="mc-value">{n_dekat}</div>
            <div class="mc-sub">{sub_dekat}</div>
        </div>
        <div class="metric-card blue">
            <div class="mc-label">Sudah Kadaluarsa</div>
            <div class="mc-value">{n_kadaluarsa}</div>
            <div class="mc-sub">{sub_aktif}</div>
        </div>

    </div>
    """, unsafe_allow_html=True)

    # ===== TWO PANELS =====
    col_kiri, col_kanan = st.columns(2)

    # --- Panel kanan: Dokumen Terbaru ---
    with col_kanan:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("""
        <div class="panel-header">
            <span class="panel-title">📄 Dokumen Terbaru</span>
        </div>""", unsafe_allow_html=True)

        BAR_COLORS = ['#00a859','#1565c0','#6a1b9a','#e65100','#c62828','#00838f']

        def _badge(kat_nama):
            k = kat_nama.lower()
            if 'spo' in k:         return 'badge-spo',      'SPO'
            if 'kebijakan' in k:   return 'badge-kebijakan','KBJK'
            if 'ppk' in k:         return 'badge-ppk',      'PPK'
            if 'pedoman' in k:     return 'badge-pedoman',  'PDM'
            if 'pak' in k:         return 'badge-pak',      'PAK'
            return 'badge-lain', kat_nama[:4].upper()

        if df_terbaru.empty:
            st.markdown('<p style="color:#999;font-size:13px;text-align:center;padding:20px 0">Belum ada dokumen</p>', unsafe_allow_html=True)
        else:
            kat_map2 = {}
            if not df_kat.empty and 'kategori_id' in df_kat.columns and 'nama_kategori' in df_kat.columns:
                for _, r in df_kat.iterrows():
                    kat_map2[str(r['kategori_id'])] = str(r['nama_kategori'])

            items_html = ""
            for _, row in df_terbaru.iterrows():
                nama_dok = str(row.get('nama_regulasi', ''))[:55]
                kid      = str(row.get('kategori_id', ''))
                kat_nama = kat_map2.get(kid, kid)
                bid_nama = str(row.get('bidang_id', ''))
                tgl_t    = str(row.get('tanggal_terbit', ''))
                badge_cls, badge_txt = _badge(kat_nama)
                items_html += f"""
                <div class="doc-item">
                    <span class="doc-badge {badge_cls}">{badge_txt}</span>
                    <div class="doc-info">
                        <div class="doc-name">{nama_dok}</div>
                        <div class="doc-unit">{bid_nama or kat_nama} &nbsp;·&nbsp; {tgl_t}</div>
                    </div>
                </div>"""
            st.markdown(items_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Panel kiri: Distribusi per Kategori ---
    with col_kiri:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("""
        <div class="panel-header">
            <span class="panel-title">📊 Distribusi per Kategori</span>
        </div>""", unsafe_allow_html=True)

        if not kat_dist_sorted:
            st.markdown('<p style="color:#999;font-size:13px;text-align:center;padding:20px 0">Belum ada data</p>', unsafe_allow_html=True)
        else:
            max_val = max(kat_dist_sorted.values()) if kat_dist_sorted else 1
            bars_html = ""
            for i, (kat, cnt) in enumerate(kat_dist_sorted.items()):
                pct   = int(cnt / max_val * 100)
                color = BAR_COLORS[i % len(BAR_COLORS)]
                # Strip prefix nomor dari nama kategori untuk tampilan ringkas
                display_name = kat
                if '. ' in kat:
                    display_name = kat.split('. ', 1)[1]
                bars_html += f"""
                <div class="bar-item">
                    <div class="bar-header">
                        <span class="bar-name">{display_name}</span>
                        <span class="bar-count" style="color:{color}">{cnt}</span>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill" style="width:{pct}%;background:{color}"></div>
                    </div>
                </div>"""
            st.markdown(bars_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)