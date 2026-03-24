@echo off
echo ============================================
echo   SETUP A-REG SOLO
echo   RS Hermina Solo
echo ============================================
echo.

:: Cek Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python belum terinstall!
    echo.
    echo Silakan download Python di:
    echo https://www.python.org/downloads/
    echo.
    echo PENTING: Centang "Add Python to PATH" saat install!
    pause
    exit /b 1
)

echo [OK] Python ditemukan
echo.

:: Upgrade pip
echo [1/3] Upgrade pip...
python -m pip install --upgrade pip --quiet

:: Install dependencies
echo [2/3] Install dependencies (harap tunggu)...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Gagal install dependencies!
    echo Coba jalankan manual: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo [OK] Semua dependencies berhasil diinstall!
echo.

:: Cek service_account.json
if not exist "service_account.json" (
    echo [WARNING] File service_account.json tidak ditemukan!
    echo Pastikan file tersebut ada di folder ini sebelum menjalankan app.
    echo.
)

:: Cek assets
if not exist "assets\logo.png" (
    echo [WARNING] assets\logo.png tidak ditemukan!
)
if not exist "assets\hermina_solo.jpg" (
    echo [WARNING] assets\hermina_solo.jpg tidak ditemukan!
)

echo [3/3] Menjalankan aplikasi...
echo.
echo ============================================
echo   App berjalan di: http://localhost:8501
echo   Tekan Ctrl+C untuk stop
echo ============================================
echo.
streamlit run app.py
pause