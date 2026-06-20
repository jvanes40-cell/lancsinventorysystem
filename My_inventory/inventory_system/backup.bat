@echo off
setlocal

:: ─── CONFIG ───────────────────────────────────────────────
set PROJECT_DIR=C:\Users\LENOVO\Desktop\LANCS STORAGE SYSTEM (Fix)\My_inventory\inventory_system
set DB_FILE=%PROJECT_DIR%\db.sqlite3
set BACKUP_DIR=%PROJECT_DIR%\backups
set KEEP_DAYS=7
:: ──────────────────────────────────────────────────────────

:: Create backup folder if it doesn't exist
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Use wmic to get date reliably regardless of Windows locale/format
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set DATETIME=%%a

set YYYY=%DATETIME:~0,4%
set MM=%DATETIME:~4,2%
set DD=%DATETIME:~6,2%
set HH=%DATETIME:~8,2%
set MIN=%DATETIME:~10,2%

set TIMESTAMP=%YYYY%-%MM%-%DD%_%HH%%MIN%
set BACKUP_FILE=%BACKUP_DIR%\lancs_backup_%TIMESTAMP%.sqlite3

:: Copy the database
copy "%DB_FILE%" "%BACKUP_FILE%" >nul

if exist "%BACKUP_FILE%" (
    echo [%TIMESTAMP%] Backup SUCCESS: %BACKUP_FILE%
) else (
    echo [%TIMESTAMP%] Backup FAILED!
    exit /b 1
)

:: Delete backups older than KEEP_DAYS days
forfiles /p "%BACKUP_DIR%" /s /m *.sqlite3 /d -%KEEP_DAYS% /c "cmd /c del @path" 2>nul

echo [%TIMESTAMP%] Old backups cleaned up. Keeping last %KEEP_DAYS% days.
endlocal