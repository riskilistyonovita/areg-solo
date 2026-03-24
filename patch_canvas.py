"""
patch_canvas.py
Jalankan SEKALI untuk fix streamlit-drawable-canvas agar kompatibel dengan Streamlit 1.35+
Cara: python patch_canvas.py
"""
import site, os, shutil, sys

def patch():
    patched = False
    for sp in site.getsitepackages():
        canvas_dir = os.path.join(sp, 'streamlit_drawable_canvas')
        if not os.path.exists(canvas_dir):
            continue
        
        fpath = os.path.join(canvas_dir, '__init__.py')
        if not os.path.exists(fpath):
            continue

        # Backup
        backup = fpath + '.bak'
        if not os.path.exists(backup):
            shutil.copy2(fpath, backup)
            print(f"[BACKUP] {backup}")

        with open(fpath, encoding='utf-8') as f:
            content = f.read()

        if 'PATCHED_FOR_ST135' in content:
            print("[OK] Sudah di-patch sebelumnya.")
            return True

        # Target yang perlu diganti
        old1 = 'background_image_url = st_image.image_to_url('
        old2 = 'background_image_url = st._config.get_option("server.baseUrlPath") + background_image_url'

        if old1 not in content:
            print("[WARN] Target tidak ditemukan. Mungkin versi berbeda.")
            return False

        # Cari baris lengkap
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if old1 in line:
                # Ganti blok ini (bisa 2-3 baris)
                new_lines.append('        # PATCHED_FOR_ST135: image_to_url removed in Streamlit 1.35+')
                new_lines.append('        import io as _io, base64 as _b64')
                new_lines.append('        _buf = _io.BytesIO()')
                new_lines.append('        background_image.save(_buf, format="PNG")')
                new_lines.append('        _b64data = _b64.b64encode(_buf.getvalue()).decode()')
                new_lines.append('        background_image_url = f"data:image/png;base64,{_b64data}"')
                # Skip sampai baris baseUrlPath selesai
                while i < len(lines) and 'baseUrlPath' not in lines[i] and 'background_color' not in lines[i]:
                    i += 1
                if i < len(lines) and 'baseUrlPath' in lines[i]:
                    i += 1  # skip baseUrlPath line
            else:
                new_lines.append(line)
                i += 1

        new_content = '\n'.join(new_lines)

        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"[OK] Patch berhasil diterapkan ke: {fpath}")
        patched = True
        break

    if not patched:
        print("[ERROR] streamlit_drawable_canvas tidak ditemukan di site-packages.")
        print("Pastikan sudah install: pip install streamlit-drawable-canvas")
    return patched

if __name__ == '__main__':
    print("=" * 60)
    print("Patch streamlit-drawable-canvas untuk Streamlit 1.35+")
    print("=" * 60)
    ok = patch()
    if ok:
        print("\n✅ Selesai! Restart Streamlit app setelah ini.")
    else:
        print("\n❌ Patch gagal. Lihat pesan error di atas.")
    input("\nTekan Enter untuk keluar...")