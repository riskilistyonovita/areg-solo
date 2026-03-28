# app.py  — AREG SOLO  |  RS Hermina Solo
"""
Shell utama aplikasi. Menggunakan st.sidebar native agar tampilan
konsisten dan benar-benar terasa seperti webapp.
"""

import streamlit as st
from utils.google_drive_manager import get_drive_manager
from utils.auth_manager import get_auth_manager
import os, base64, importlib, traceback

# ═══════════════════════════════════════════════════════════════════════
# PAGE CONFIG — wajib paling atas
# ═══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AREG SOLO",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Helper ──────────────────────────────────────────────────────────────
def get_b64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


# ── Init managers (cached) ──────────────────────────────────────────────
@st.cache_resource
def init_managers():
    dm   = get_drive_manager()
    auth = get_auth_manager(dm)
    return dm, auth

dm, auth = init_managers()

if not dm.is_initialized():
    st.error("⚠️ Google Drive Manager tidak dapat diinisialisasi!")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════
# ① LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════
if not auth.is_authenticated():

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stMain"] > div:first-child { padding: 0 !important; }
    [data-testid="stHorizontalBlock"]       { gap: 0 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { border:none!important; box-shadow:none!important; }

    /* Right column = form panel */
    div[data-testid="column"]:last-child {
        background: white;
        min-height: 100vh;
        display: flex !important; flex-direction: column;
        align-items: center; justify-content: center;
        padding: 48px 56px !important;
    }
    div[data-testid="column"]:last-child > div { width:100%; max-width:340px; margin:0 auto; }

    /* Inputs */
    .stTextInput > label {
        font-size:11px!important; font-weight:700!important; color:#94a3b8!important;
        text-transform:uppercase!important; letter-spacing:.07em!important;
    }
    .stTextInput input {
        border-radius:10px!important; border:1.5px solid #e2e8f0!important;
        padding:13px 15px!important; font-size:14px!important; background:#f8fafc!important;
    }
    .stTextInput input:focus {
        border-color:#00a859!important; background:white!important;
        box-shadow:0 0 0 3px rgba(0,168,89,.12)!important; outline:none!important;
    }

    /* Login button */
    div[data-testid="column"]:last-child .stButton > button {
        width:100%!important;
        background:linear-gradient(135deg,#00c76b,#00a859)!important;
        color:white!important; border:none!important;
        padding:13px!important; font-size:15px!important; font-weight:700!important;
        border-radius:12px!important;
        box-shadow:0 4px 18px rgba(0,168,89,.35)!important;
        margin-top:4px!important;
    }
    div[data-testid="column"]:last-child .stButton > button:hover {
        transform:translateY(-1px)!important;
        box-shadow:0 6px 24px rgba(0,168,89,.45)!important;
    }
    button[title="View fullscreen"] { display:none!important; }
    .stAlert { border-radius:10px!important; font-size:13px!important; }
    </style>
    """, unsafe_allow_html=True)

    col_hero, col_form = st.columns([3, 2])

    # ── Hero kiri ──────────────────────────────────────────────────────
    with col_hero:
        bg = get_b64("assets/hermina_solo.jpg")
        if bg:
            st.markdown(
                f'<div style="position:relative;height:100vh;overflow:hidden">'
                f'<img src="data:image/jpeg;base64,{bg}" style="position:absolute;inset:0;'
                f'width:100%;height:100%;object-fit:cover;object-position:center">'
                f'<div style="position:absolute;inset:0;background:linear-gradient('
                f'160deg,rgba(5,25,15,.80) 0%,rgba(0,50,25,.55) 100%)"></div>'
                f'<div style="position:relative;z-index:2;height:100%;display:flex;'
                f'flex-direction:column;justify-content:center;padding:60px 52px">'
                # Badge
                f'<div style="display:inline-flex;align-items:center;gap:8px;'
                f'background:rgba(0,232,120,.15);border:1px solid rgba(0,232,120,.3);'
                f'border-radius:999px;padding:5px 14px;font-size:11px;color:#5effa0;'
                f'font-weight:600;letter-spacing:1px;margin-bottom:28px;width:fit-content">'
                f'<span style="width:6px;height:6px;background:#5effa0;border-radius:50%;'
                f'box-shadow:0 0 6px #5effa0;display:inline-block"></span>SISTEM AKTIF</div>'
                # Judul
                f'<h1 style="color:white;font-size:42px;font-weight:800;line-height:1.2;'
                f'margin:0 0 14px;text-shadow:0 2px 20px rgba(0,0,0,.4)">'
                f'Selamat Datang di<br><span style="color:#5effa0">RS Hermina Solo</span></h1>'
                f'<p style="color:rgba(255,255,255,.75);font-size:16px;font-style:italic;'
                f'margin:0 0 36px">"Melayani dengan Hati"</p>'
                # Chips
                f'<div style="display:flex;gap:10px;flex-wrap:wrap">'
                + ''.join([
                    f'<div style="background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);'
                    f'border-radius:999px;padding:7px 16px;font-size:12px;color:rgba(255,255,255,.85)">{t}</div>'
                    for t in ['📋 Manajemen Regulasi','🔄 Ratifikasi Dokumen','📚 e-Library Klinis','🤝 PKS & Perijinan']
                ]) +
                f'</div></div></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="background:linear-gradient(160deg,#0d4a2f,#00a859);height:100vh;'
                'display:flex;align-items:center;justify-content:center;text-align:center;color:white">'
                '<div><div style="font-size:72px">🏥</div>'
                '<h1 style="font-size:36px;font-weight:800">RS Hermina Solo</h1>'
                '<p style="font-style:italic;opacity:.8">"Melayani dengan Hati"</p></div></div>',
                unsafe_allow_html=True
            )

    # ── Form kanan ────────────────────────────────────────────────────
    with col_form:
        _, mid, _ = st.columns([.1, 1, .1])
        with mid:
            logo_b64 = get_b64("assets/logo.png")
            if logo_b64:
                st.markdown(
                    f'<div style="text-align:center;margin-bottom:20px">'
                    f'<img src="data:image/png;base64,{logo_b64}" style="width:70px;height:70px;'
                    f'border-radius:16px;object-fit:cover;box-shadow:0 6px 20px rgba(0,168,89,.2)"></div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div style="text-align:center;margin-bottom:20px">'
                    '<div style="width:70px;height:70px;background:linear-gradient(135deg,#00a859,#007a40);'
                    'border-radius:16px;display:inline-flex;align-items:center;justify-content:center;'
                    'font-size:32px">🏥</div></div>', unsafe_allow_html=True
                )

            st.markdown(
                '<div style="text-align:center;margin-bottom:32px">'
                '<div style="font-size:22px;font-weight:800;color:#1a1a2e">AREG SOLO</div>'
                '<div style="font-size:12px;color:#aaa;margin-top:3px">Aplikasi Regulasi RS Hermina Solo</div>'
                '</div>'
                '<div style="margin-bottom:20px">'
                '<div style="font-size:20px;font-weight:700;color:#1a1a2e;margin-bottom:5px">Masuk ke Akun</div>'
                '<div style="font-size:13px;color:#aaa">Masukkan User ID dan password Anda</div>'
                '</div>',
                unsafe_allow_html=True
            )

            with st.form("login_form", clear_on_submit=False):
                user_id  = st.text_input("User ID", placeholder="Contoh: USR001", key="login_uid")
                password = st.text_input("Password", type="password",
                                         placeholder="Masukkan password", key="login_pwd")
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                submit = st.form_submit_button("🔐  Masuk", use_container_width=True)

            if submit:
                with st.spinner("Memverifikasi..."):
                    user, login_err = auth.authenticate(user_id, password)
                if login_err:
                    st.error(f"❌ {login_err}")
                elif user:
                    auth.create_session(user)
                    st.success("✅ Login berhasil!")
                    import time; time.sleep(0.4); st.rerun()

            st.markdown(
                '<div style="text-align:center;color:#cbd5e0;font-size:11px;margin-top:20px">'
                '© 2026 RS Hermina Solo · Tim Regulasi</div>',
                unsafe_allow_html=True
            )


# ═══════════════════════════════════════════════════════════════════════
# ② MAIN APP
# ═══════════════════════════════════════════════════════════════════════
else:
    current_user = auth.get_current_user()
    if not current_user:
        auth.logout(); st.rerun()

    nama_lengkap = current_user.get('nama_lengkap', 'User')
    role         = current_user.get('role', '')
    user_id_val  = current_user.get('user_id', '')
    inisial      = "".join([w[0].upper() for w in nama_lengkap.split()[:2]]) or "U"

    if 'selected_menu' not in st.session_state:
        st.session_state.selected_menu = 'Dashboard'
    sel = st.session_state.selected_menu

    logo_b64 = get_b64("assets/logo.png") or ""

    NAV = [
        ("Dashboard",       "📊"),
        ("Regulasi",        "📋"),
        ("Perijinan & PKS", "🤝"),
        ("e-Library",       "📚"),
        ("Dokumen Lainnya", "📁"),
        ("Ratifikasi",      "✍️"),
        ("Master Data",     "⚙️"),
    ]

    # Pemetaan menu → (kunci modul di PERMISSIONS, aksi minimum untuk buka halaman)
    MENU_PERMISSIONS = {
        "Dashboard":       ("dashboard",       "view"),
        "Regulasi":        ("regulasi",        "lihat"),
        "Perijinan & PKS": ("perijinan_pks",   "lihat"),
        "e-Library":       ("elibrary",        "lihat"),
        "Dokumen Lainnya": ("dokumen_lainnya", "lihat"),
        "Ratifikasi":      ("ratifikasi",      "lihat"),
        "Master Data":     ("master_data",     "lihat"),
    }

    # Hanya tampilkan menu yang boleh diakses role ini
    NAV_VISIBLE = [
        (lbl, ico) for lbl, ico in NAV
        if auth.has_permission(*MENU_PERMISSIONS.get(lbl, ("dashboard", "view")))
    ]

    # Pastikan sel yang tersimpan masih valid untuk role ini
    visible_labels = [lbl for lbl, _ in NAV_VISIBLE]
    if sel not in visible_labels:
        st.session_state.selected_menu = visible_labels[0] if visible_labels else "Dashboard"
        sel = st.session_state.selected_menu

    # ════════════════════════════════════════════════════════════════
    # GLOBAL CSS  —  sidebar native + main area
    # ════════════════════════════════════════════════════════════════
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu, footer, header { visibility: hidden; }

    /* ── Sidebar shell ──────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: #0f172a !important;
        border-right: none !important;
        box-shadow: 4px 0 24px rgba(0,0,0,.18) !important;
        min-width: 220px !important;
        max-width: 220px !important;
    }
    [data-testid="stSidebarContent"] {
        padding: 0 !important;
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    /* Sembunyikan resize handle */
    [data-testid="stSidebarResizeHandle"] { display: none !important; }
    /* Sembunyikan tombol collapse bawaan — tapi biarkan expand tetap muncul */
    button[aria-label="Close sidebar"],
    button[title="Collapse sidebar"] { display: none !important; }

    /* ── Nav buttons di sidebar ──────────────────────────────────── */
    [data-testid="stSidebarContent"] .stButton > button {
        width: 100% !important;
        background: transparent !important;
        color: #94a3b8 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0 14px !important;
        height: 42px !important;
        min-height: unset !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 10px !important;
        box-shadow: none !important;
        transition: background .15s, color .15s !important;
        letter-spacing: .01em !important;
        margin: 1px 0 !important;
    }
    [data-testid="stSidebarContent"] .stButton > button:hover {
        background: rgba(255,255,255,.06) !important;
        color: #e2e8f0 !important;
    }
    /* Active nav item */
    [data-testid="stSidebarContent"] .stButton > button[kind="primary"] {
        background: rgba(0,199,107,.14) !important;
        color: #34d399 !important;
        font-weight: 700 !important;
        border-left: 3px solid #00c76b !important;
        border-radius: 0 8px 8px 0 !important;
        padding-left: 11px !important;
    }
    [data-testid="stSidebarContent"] .stButton > button[kind="primary"]:hover {
        background: rgba(0,199,107,.2) !important;
    }

    /* ── Main content area ──────────────────────────────────────── */
    [data-testid="stMain"] { background: #f0f4f8 !important; }

    /* ── Topbar ──────────────────────────────────────────────────── */
    .areg-topbar {
        background: #ffffff;
        padding: 0 32px;
        height: 58px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #e8edf5;
        box-shadow: 0 1px 6px rgba(0,0,0,.05);
        position: sticky;
        top: 0;
        z-index: 100;
    }
    .areg-topbar .tb-left { display: flex; align-items: center; gap: 10px; }
    .areg-topbar .tb-crumb {
        font-size: 12px; color: #94a3b8;
        display: flex; align-items: center; gap: 6px;
    }
    .areg-topbar .tb-crumb span { color: #64748b; }
    .areg-topbar .tb-page {
        font-size: 16px; font-weight: 700; color: #1e293b;
        padding-left: 10px;
        border-left: 2px solid #e2e8f0;
    }
    .areg-topbar .tb-right { display: flex; align-items: center; gap: 12px; }
    .areg-topbar .tb-user {
        display: flex; align-items: center; gap: 10px;
        background: #f8fafc;
        border: 1px solid #e8edf5;
        border-radius: 24px;
        padding: 5px 14px 5px 6px;
        cursor: default;
    }
    .areg-topbar .tb-avatar {
        width: 30px; height: 30px;
        background: linear-gradient(135deg, #00c76b, #007a40);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 11px; font-weight: 800; color: white;
        flex-shrink: 0;
    }
    .areg-topbar .tb-name  { font-size: 13px; font-weight: 600; color: #334155; }
    .areg-topbar .tb-role  { font-size: 10px; color: #94a3b8; }

    /* ── Block container: padding utama konten ─────────────────── */
    /* Pakai selector lebih spesifik supaya menang atas default Streamlit */
    [data-testid="stMain"] .block-container,
    [data-testid="stMainBlockContainer"] {
        padding: 0 48px 48px 48px !important;
        max-width: 100% !important;
    }

    /* Topbar harus full-width → kompensasi padding block-container */
    .areg-topbar {
        margin-left: -48px !important;
        margin-right: -48px !important;
        margin-bottom: 28px !important;
    }

    /* ── Tombol di main area ────────────────────────────────────── */
    [data-testid="stMain"] .stButton > button {
        font-size:13px!important; font-weight:600!important;
        border-radius:8px!important; padding:8px 16px!important;
    }
    [data-testid="stMain"] .stButton > button[kind="primary"] {
        background:linear-gradient(135deg,#00c76b,#00a859)!important;
        color:white!important; border:none!important;
        box-shadow:0 2px 10px rgba(0,168,89,.3)!important;
    }
    [data-testid="stMain"] .stButton > button[kind="secondary"] {
        background:white!important; color:#374151!important;
        border:1.5px solid #e5e7eb!important;
    }
    [data-testid="stMain"] .stButton > button[kind="secondary"]:hover {
        border-color:#00a859!important; color:#00a859!important;
        background:#f0faf5!important;
    }

    /* ── Inputs di main area ────────────────────────────────────── */
    [data-testid="stMain"] .stTextInput > label,
    [data-testid="stMain"] .stSelectbox > label,
    [data-testid="stMain"] .stMultiSelect > label,
    [data-testid="stMain"] .stDateInput > label,
    [data-testid="stMain"] .stTextArea  > label {
        font-size:11px!important; font-weight:700!important; color:#64748b!important;
        text-transform:uppercase!important; letter-spacing:.06em!important;
    }
    [data-testid="stMain"] .stTextInput input {
        border-radius:8px!important; border:1.5px solid #e2e8f0!important;
        font-size:14px!important; background:white!important;
    }
    [data-testid="stMain"] .stTextInput input:focus {
        border-color:#00a859!important;
        box-shadow:0 0 0 3px rgba(0,168,89,.12)!important;
    }

    /* ── Tabs ───────────────────────────────────────────────────── */
    [data-baseweb="tab-list"] {
        background:transparent!important;
        border-bottom:2px solid #e2e8f0!important;
        gap:4px!important;
    }
    [data-baseweb="tab"] {
        font-size:13px!important; font-weight:600!important;
        color:#94a3b8!important; padding:8px 16px!important;
        border-radius:8px 8px 0 0!important;
    }
    [aria-selected="true"] {
        color:#00a859!important;
        border-bottom:2px solid #00a859!important;
        background:rgba(0,168,89,.06)!important;
    }

    /* ── Misc ───────────────────────────────────────────────────── */
    .stAlert { border-radius:10px!important; font-size:13px!important; }
    button[title="View fullscreen"] { display:none!important; }
    [data-testid="stVerticalBlockBorderWrapper"] { border:none!important; box-shadow:none!important; }
    </style>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ════════════════════════════════════════════════════════════════
    with st.sidebar:
        # Brand
        logo_img = (
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="width:34px;height:34px;border-radius:9px;object-fit:cover">'
            if logo_b64 else
            '<div style="width:34px;height:34px;background:linear-gradient(135deg,#00c76b,#007a40);'
            'border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:16px">🏥</div>'
        )
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:20px 16px 16px;border-bottom:1px solid rgba(255,255,255,.06);margin-bottom:8px">'
            f'{logo_img}'
            f'<div>'
            f'<div style="color:white;font-size:14px;font-weight:800;letter-spacing:.3px">AREG SOLO</div>'
            f'<div style="color:#00c76b;font-size:9px;letter-spacing:1.2px;font-weight:600;opacity:.8">RS HERMINA SOLO</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        # Section label
        st.markdown(
            '<div style="color:#475569;font-size:8.5px;font-weight:700;letter-spacing:1.5px;'
            'text-transform:uppercase;padding:2px 16px 6px">MENU UTAMA</div>',
            unsafe_allow_html=True
        )

        # Nav items — hanya menu yang boleh diakses role ini
        for lbl, ico in NAV_VISIBLE:
            if st.button(
                f"{ico}  {lbl}",
                key=f"nav_{lbl}",
                type="primary" if sel == lbl else "secondary",
                use_container_width=True
            ):
                st.session_state.selected_menu = lbl
                st.rerun()

        # Divider + util buttons
        st.markdown(
            '<div style="flex:1;min-height:20px"></div>'
            '<div style="height:1px;background:rgba(255,255,255,.07);margin:8px 12px 6px"></div>',
            unsafe_allow_html=True
        )
        if st.button("🚪  Logout", key="nav_logout", type="secondary", use_container_width=True):
            auth.logout(); st.rerun()
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # MAIN AREA
    # ════════════════════════════════════════════════════════════════

    # Topbar
    st.markdown(
        f'<div class="areg-topbar">'
        f'  <div class="tb-left">'
        f'    <div class="tb-crumb">🏠 <span>Home</span> › <span>{sel}</span></div>'
        f'    <div class="tb-page">{sel}</div>'
        f'  </div>'
        f'  <div class="tb-right">'
        f'    <div class="tb-user">'
        f'      <div class="tb-avatar">{inisial}</div>'
        f'      <div>'
        f'        <div class="tb-name">{nama_lengkap}</div>'
        f'        <div class="tb-role">{role}</div>'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Spacer kecil setelah topbar
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    MODULE_MAP = {
        "Dashboard":       "modules.dashboard",
        "Regulasi":        "modules.regulasi",
        "Perijinan & PKS": "modules.pks",
        "e-Library":       "modules.elibrary",
        "Dokumen Lainnya": "modules.dokumen_lainnya",
        "Ratifikasi":      "modules.ratifikasi",
        "Master Data":     "modules.master_data",
    }

    if sel in MODULE_MAP:
        # ── Permission guard ────────────────────────────────────────────
        mod_key, mod_action = MENU_PERMISSIONS.get(sel, (None, None))
        if mod_key and not auth.has_permission(mod_key, mod_action):
            st.error(f"⛔ Anda tidak memiliki akses ke menu **{sel}**.")
            st.info(
                f"Role **{role}** tidak memiliki hak akses untuk membuka halaman ini. "
                f"Hubungi Administrator jika merasa ini keliru."
            )
            st.stop()

        try:
            mod = importlib.import_module(MODULE_MAP[sel])
            if sel == "Regulasi":
                mod.show(default_tab='daftar')
            else:
                mod.show()
        except Exception as e:
            st.error(f"⚠️ Error memuat halaman **{sel}**: {e}")
            with st.expander("Detail Error"):
                st.code(traceback.format_exc())

    # (end of main app)