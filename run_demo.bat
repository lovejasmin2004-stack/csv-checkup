@echo off
rem Starts a small local web server in this folder and opens the demo page.
rem Close this window to stop it.
cd /d "%~dp0"
start "" http://localhost:8000/index.html
python -m http.server 8000
