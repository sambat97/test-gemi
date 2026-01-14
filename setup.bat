@echo off
echo ========================================
echo SheerID Bot - Quick Setup Script
echo ========================================
echo.

REM Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Silakan install Python terlebih dahulu dari https://python.org
    pause
    exit /b 1
)

echo [1/4] Python terdeteksi: 
python --version
echo.

REM Install dependencies
echo [2/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal install dependencies!
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully!
echo.

REM Check if .env exists
if not exist .env (
    echo [3/4] Creating .env file...
    copy .env.example .env
    echo [WARNING] File .env telah dibuat!
    echo.
    echo IMPORTANT: Edit file .env dan masukkan bot token Anda!
    echo Buka .env dengan notepad dan ganti:
    echo    TELEGRAM_BOT_TOKEN=your_bot_token_here
    echo dengan token bot Anda dari @BotFather
    echo.
) else (
    echo [3/4] File .env sudah ada, skip...
    echo.
)

REM Check if bot token is configured
findstr /C:"your_bot_token_here" .env > nul
if not errorlevel 1 (
    echo [WARNING] Bot token belum dikonfigurasi!
    echo Silakan edit .env dan masukkan token Anda dari @BotFather
    echo.
    set TOKEN_CONFIGURED=0
) else (
    set TOKEN_CONFIGURED=1
)

echo [4/4] Setup selesai!
echo.
echo ========================================
echo Next Steps:
echo ========================================

if %TOKEN_CONFIGURED%==0 (
    echo 1. Edit file .env
    echo 2. Ganti TELEGRAM_BOT_TOKEN dengan token Anda
    echo 3. Jalankan: python bot.py
) else (
    echo Setup lengkap! Bot siap dijalankan.
    echo Jalankan: python bot.py
)

echo.
echo ========================================
pause
