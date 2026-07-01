@echo off
rem Double-click launcher for the AnimeUnity Downloader GUI.
rem Uses pythonw so no console window appears. Falls back to python if needed.
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0app.py"
) else (
    start "" python "%~dp0app.py"
)
