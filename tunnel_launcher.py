"""
Cloudflare Tunnel 自動連携ランチャー (tunnel_launcher.py)
cloudflared を起動し、発行された公開URLをデータベースの custom_access_url に自動登録します。
"""

import os
import re
import subprocess
import sys
import time

import database as db

def main():
    print("Starting Cloudflare Tunnel for Panda Royal Tournament Manager...")
    
    # cloudflared のパス探索
    cloudflared_cmd = "cloudflared"
    
    # プロセス起動
    try:
        proc = subprocess.Popen(
            [cloudflared_cmd, "tunnel", "--url", "http://localhost:8501"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        print("Error: cloudflared was not found on PATH.")
        return

    print("Waiting for public tunnel URL from Cloudflare...")
    url_found = None
    url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # stderr をリアルタイムで監視（cloudflared は stderr にログを出す）
    for line in iter(proc.stderr.readline, ""):
        if not line:
            break
        print(f"[Cloudflare] {line.strip()}")
        match = url_regex.search(line)
        if match:
            url_found = match.group(0)
            print("=" * 60)
            print(f"SUCCESS! Public Tunnel URL: {url_found}")
            print("=" * 60)
            # DBに保存
            db.init_db()
            db.set_setting("custom_access_url", url_found)
            print("Successfully updated custom_access_url in database!")
            print("The in-app QR code is now automatically pointing to this public URL.")
            break

    if not url_found:
        print("Failed to capture tunnel URL.")
        return

    # トンネルを維持
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("Stopping Cloudflare Tunnel...")
        proc.terminate()
        # 終了時にローカルURLに戻す
        db.set_setting("custom_access_url", "")
        print("Reset custom_access_url to local IP.")

if __name__ == "__main__":
    main()
