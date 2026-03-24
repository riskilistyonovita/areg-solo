# utils/email_sender.py
"""
Modul pengiriman email notifikasi regulasi baru — BATCH MODE
Kirim 1 email berisi semua regulasi yang diupload hari ini.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date
import pandas as pd
import streamlit as st


# ============================================================
# ► KONFIGURASI EMAIL
# Local  : isi di .streamlit/secrets.toml   [email] section
# Cloud  : isi di Streamlit Cloud > Settings > Secrets
# ============================================================
def _load_email_config():
    """Load konfigurasi email dari st.secrets atau fallback ke os.environ."""
    import os
    try:
        sec = st.secrets.get("email", {})
        sender   = sec.get("sender",   os.getenv("EMAIL_SENDER",   ""))
        password = sec.get("password", os.getenv("EMAIL_PASSWORD", ""))
        app_url  = sec.get("app_url",  os.getenv("APP_URL",        "http://localhost:8501"))
    except Exception:
        sender   = os.getenv("EMAIL_SENDER",   "")
        password = os.getenv("EMAIL_PASSWORD", "")
        app_url  = os.getenv("APP_URL",        "http://localhost:8501")
    return sender, password, app_url

EMAIL_SENDER, EMAIL_PASSWORD, APP_URL = _load_email_config()
# ============================================================

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

_KAT_BUKAN_REGULASI = [
    "library", "pks", "perjanjian", "program kerja",
    "spk", "rkk", "notulen", "surat keputusan",
]


def get_regulasi_hari_ini(dm) -> list:
    """Ambil semua dokumen regulasi yang diupload HARI INI dari rekap_database."""
    try:
        docs = dm.get_all_documents() or []
        if not docs:
            return []

        df = pd.DataFrame(docs).fillna('')
        if df.empty or 'created_at' not in df.columns:
            return []

        today_str = date.today().strftime('%Y-%m-%d')
        df_today  = df[df['created_at'].astype(str).str.startswith(today_str)].copy()
        if df_today.empty:
            return []

        # Map kategori
        df_kat  = dm.get_master_data('kategori_id')
        kat_map = {}
        if not df_kat.empty and 'kategori_id' in df_kat.columns and 'nama_kategori' in df_kat.columns:
            kat_map = dict(zip(df_kat['kategori_id'].astype(str),
                               df_kat['nama_kategori'].astype(str)))

        result = []
        for _, row in df_today.iterrows():
            kat_id   = str(row.get('kategori_id', ''))
            kat_nama = kat_map.get(kat_id, kat_id)
            # Skip non-regulasi
            if any(kw in kat_nama.lower() for kw in _KAT_BUKAN_REGULASI):
                continue
            result.append({
                'nama':     str(row.get('nama_regulasi', '')),
                'kategori': kat_nama,
            })

        return result

    except Exception as e:
        st.warning(f"⚠️ Gagal membaca data: {str(e)}")
        return []


def _get_email_list(dm) -> list:
    """Ambil semua email aktif dari sheet email_unit."""
    try:
        df = dm.get_master_data('email_unit')
        if df.empty or 'email' not in df.columns:
            return []
        if 'status' in df.columns:
            df = df[df['status'].str.lower() == 'aktif']
        emails = df['email'].dropna().astype(str).str.strip().tolist()
        return [e for e in emails if '@' in e and len(e) > 5]
    except Exception as e:
        st.warning(f"⚠️ Gagal membaca daftar email unit: {str(e)}")
        return []


def _build_html(docs: list) -> str:
    tanggal = datetime.now().strftime('%d %B %Y')

    rows_html = ""
    for i, doc in enumerate(docs, 1):
        bg = "#fafafa" if i % 2 == 0 else "#ffffff"
        rows_html += f"""
        <tr style="background:{bg}">
          <td style="padding:8px 14px;color:#888;font-size:13px;
                     border-bottom:1px solid #f0f0f0;">{i}.</td>
          <td style="padding:8px 14px;color:#1a1a1a;font-size:13px;
                     border-bottom:1px solid #f0f0f0;">{doc['nama']}</td>
          <td style="padding:8px 14px;color:#00a859;font-size:12px;
                     border-bottom:1px solid #f0f0f0;white-space:nowrap;">{doc['kategori']}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 0;background:#f4f6f8;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:14px;box-shadow:0 2px 12px rgba(0,0,0,0.08);overflow:hidden;">

  <tr>
    <td style="background:linear-gradient(135deg,#00a859,#007a40);padding:30px 36px;text-align:center;">
      <div style="font-size:32px;margin-bottom:8px;">🏥</div>
      <h1 style="margin:0;color:#fff;font-size:20px;font-weight:700;">AREG SOLO</h1>
      <p style="margin:6px 0 0;color:rgba(255,255,255,0.82);font-size:12px;">
        Aplikasi Regulasi RS Hermina Solo</p>
    </td>
  </tr>

  <tr>
    <td style="padding:32px 36px;">
      <p style="margin:0 0 6px;color:#333;font-size:15px;">Kepada Yth,</p>
      <p style="margin:0 0 22px;color:#333;font-size:15px;font-weight:700;">
        Seluruh Unit di RS Hermina Solo</p>

      <p style="margin:0 0 18px;color:#444;font-size:14px;line-height:1.7;">
        Bersama email ini kami informasikan bahwa terdapat
        <span style="background:#e8f5ee;color:#00a859;font-weight:700;
                     padding:2px 8px;border-radius:4px;">{len(docs)} regulasi baru</span>
        yang telah diterbitkan pada tanggal <strong>{tanggal}</strong>:
      </p>

      <table width="100%" cellpadding="0" cellspacing="0"
             style="border:1px solid #e8e8e8;border-radius:10px;overflow:hidden;margin-bottom:26px;">
        <tr style="background:#f0f7f3;">
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#555;
                     text-transform:uppercase;letter-spacing:0.6px;
                     border-bottom:2px solid #d4e9de;">#</th>
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#555;
                     text-transform:uppercase;letter-spacing:0.6px;
                     border-bottom:2px solid #d4e9de;">Nama Regulasi</th>
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#555;
                     text-transform:uppercase;letter-spacing:0.6px;
                     border-bottom:2px solid #d4e9de;">Kategori</th>
        </tr>
        {rows_html}
      </table>

      <p style="margin:0 0 18px;color:#444;font-size:14px;line-height:1.7;">
        Mohon seluruh unit untuk memahami dan melaksanakan regulasi tersebut
        sesuai ketentuan yang berlaku di RS Hermina Solo.</p>

      <div style="text-align:center;margin:28px 0 20px;">
        <a href="{APP_URL}"
           style="display:inline-block;background:linear-gradient(135deg,#00a859,#007a40);
                  color:#fff;text-decoration:none;padding:14px 36px;
                  border-radius:10px;font-size:14px;font-weight:700;">
          🔍 Lihat Detail di AREG SOLO
        </a>
      </div>

      <p style="margin:0;color:#aaa;font-size:12px;text-align:center;">
        Untuk informasi lebih lanjut, hubungi Tim Mutu &amp; Akreditasi</p>
    </td>
  </tr>

  <tr>
    <td style="background:#f8f9fa;padding:18px 36px;text-align:center;
               border-top:1px solid #ececec;">
      <p style="margin:0;color:#bbb;font-size:11px;line-height:1.6;">
        Email ini dikirim otomatis oleh sistem AREG SOLO<br>
        © {datetime.now().year} RS Hermina Solo · IT Department
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body></html>"""


def _build_plain(docs: list) -> str:
    tanggal = datetime.now().strftime('%d %B %Y')
    lines   = "\n".join([f"  {i}. {d['nama']} [{d['kategori']}]"
                         for i, d in enumerate(docs, 1)])
    return (f"Kepada Yth. Seluruh Unit di RS Hermina Solo,\n\n"
            f"Terdapat {len(docs)} regulasi baru diterbitkan pada {tanggal}:\n\n"
            f"{lines}\n\n"
            f"Silakan buka AREG SOLO:\n{APP_URL}\n\n"
            f"---\nEmail otomatis · AREG SOLO · RS Hermina Solo")


def kirim_notifikasi_batch(dm, docs: list = None) -> dict:
    """
    Kirim email notifikasi batch ke semua email unit aktif.
    Jika docs=None, otomatis ambil regulasi hari ini dari database.
    """
    if docs is None:
        docs = get_regulasi_hari_ini(dm)

    if not docs:
        return {'success': False, 'sent': 0, 'total_dok': 0,
                'message': 'Tidak ada regulasi baru hari ini.'}

    if 'xxxx' in EMAIL_PASSWORD or '@' not in EMAIL_SENDER:
        return {'success': False, 'sent': 0, 'total_dok': len(docs),
                'message': 'Konfigurasi email belum diisi di utils/email_sender.py'}

    recipients = _get_email_list(dm)
    if not recipients:
        return {'success': False, 'sent': 0, 'total_dok': len(docs),
                'message': 'Tidak ada email unit aktif di sheet email_unit.'}

    tanggal = datetime.now().strftime('%d %B %Y')
    subject = f"📋 Regulasi Baru RS Hermina Solo · {tanggal} ({len(docs)} dokumen)"

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = f"AREG SOLO <{EMAIL_SENDER}>"
            msg['To']      = EMAIL_SENDER
            msg['Bcc']     = ", ".join(recipients)

            msg.attach(MIMEText(_build_plain(docs), 'plain', 'utf-8'))
            msg.attach(MIMEText(_build_html(docs),  'html',  'utf-8'))

            server.sendmail(EMAIL_SENDER, [EMAIL_SENDER] + recipients, msg.as_string())

    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'sent': 0, 'total_dok': len(docs),
                'message': ('Autentikasi Gmail gagal. '
                            'Pastikan App Password benar & 2-Step Verification aktif.')}
    except smtplib.SMTPException as e:
        return {'success': False, 'sent': 0, 'total_dok': len(docs),
                'message': f'SMTP Error: {str(e)}'}
    except Exception as e:
        return {'success': False, 'sent': 0, 'total_dok': len(docs),
                'message': f'Error: {str(e)}'}

    return {'success': True, 'sent': len(recipients), 'total_dok': len(docs),
            'message': f'✅ Email berhasil dikirim ke {len(recipients)} unit '
                       f'({len(docs)} regulasi).'}