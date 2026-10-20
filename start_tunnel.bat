@echo off
chcp 65001 > nul

echo Starting Cloudflare Tunnel for smartphone access...
echo This will generate a public HTTPS URL (e.g. https://xxx.trycloudflare.com).
echo Copy that URL and paste it into Admin Page - QR Settings to update the QR code.
echo.

cloudflared tunnel --url http://localhost:8501

pause
