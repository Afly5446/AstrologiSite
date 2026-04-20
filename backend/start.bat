@echo off
cd /d %~dp0
gunicorn -w 2 -b 0.0.0.0:8000 app:app