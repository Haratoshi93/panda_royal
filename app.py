"""
パンダロイヤル大会マネージャー (app.py)
運営側で設定した大会進行フロー（8フェーズ）に完全連動し、
トップページが現在のフェーズに応じた最適な表示に自動切り替えされる、
スマートフォン利用前提のボードゲーム大会進行Webアプリケーション。

【8つの大会フェーズ】
1. エントリーフェーズ
2. 予選１　準備（席替え表示）
3. 予選１　結果入力
4. 予選２　準備（席替え表示）
5. 予選２　結果入力
6. 決勝戦　準備（席替え表示）
7. 決勝戦　結果入力
8. 結果発表（最終スコア表示）
"""

import base64
import io
import os
import random
import socket
import pandas as pd
import qrcode
import streamlit as st
from dotenv import load_dotenv

import database as db
import tournament_logic as logic

# 環境変数の読み込み
load_dotenv()
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "panda2026")


# ==============================================================================
# ネットワーク & QRコード ユーティリティ
# ==============================================================================
def get_local_ip() -> str:
    """マシンのローカルIPアドレスを取得します。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def get_current_access_url() -> str:
    """参加者がアクセスする有効なURLを取得します。カスタムURLが設定されていればそれを優先します。"""
    custom_url = db.get_setting("custom_access_url", "").strip()
    if custom_url:
        return custom_url
    local_ip = get_local_ip()
    return f"http://{local_ip}:8501"


def generate_qr_code_image(url: str) -> bytes:
    """指定されたURLのQRコードPNG画像を生成します。"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# 大会進行フェーズ定義（8ステップ）
PHASE_ENTRY = "エントリーフェーズ"
PHASE_PRELIM1_SEAT = "予選１　準備（席替え表示）"
PHASE_PRELIM1_SCORE = "予選１　結果入力"
PHASE_PRELIM2_SEAT = "予選２　準備（席替え表示）"
PHASE_PRELIM2_SCORE = "予選２　結果入力"
PHASE_FINAL_SEAT = "決勝戦　準備（席替え表示）"
PHASE_FINAL_SCORE = "決勝戦　結果入力"
PHASE_RESULT = "結果発表（最終スコア表示）"

ALL_PHASES = [
    PHASE_ENTRY,
    PHASE_PRELIM1_SEAT,
    PHASE_PRELIM1_SCORE,
    PHASE_PRELIM2_SEAT,
    PHASE_PRELIM2_SCORE,
    PHASE_FINAL_SEAT,
    PHASE_FINAL_SCORE,
    PHASE_RESULT,
]

# 卓ごとのカラーテーマ定義
TABLE_THEMES = {
    "A卓": {"bg": "#EFF6FF", "border": "#93C5FD", "accent": "#2563EB", "badge": "🟦 A卓"},
    "B卓": {"bg": "#ECFDF5", "border": "#6EE7B7", "accent": "#059669", "badge": "🟩 B卓"},
    "C卓": {"bg": "#F5F3FF", "border": "#C4B5FD", "accent": "#7C3AED", "badge": "🟪 C卓"},
    "チャンピオン卓": {"bg": "#FFFBEB", "border": "#FCD34D", "accent": "#D97706", "badge": "👑 チャンピオン卓"},
    "シルバー卓": {"bg": "#F8FAFC", "border": "#CBD5E1", "accent": "#475569", "badge": "🥈 シルバー卓"},
    "ブロンズ卓": {"bg": "#FFF7ED", "border": "#FDBA74", "accent": "#EA580C", "badge": "🥉 ブロンズ卓"},
}


def get_table_theme(table_name: str) -> dict:
    return TABLE_THEMES.get(
        table_name,
        {"bg": "#EFF6FF", "border": "#93C5FD", "accent": "#4F46E5", "badge": f"🎲 {table_name}"},
    )


# ページ基本設定（スマホ画面に最適化）
st.set_page_config(
    page_title="パンダロイヤル 大会マネージャー",
    page_icon="🐼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# データベース初期化
db.init_db()

# ==============================================================================
# モバイルファースト＆ダークモード完全対応 カスタムCSS
# ==============================================================================
st.markdown(
    """
    <style>
    /* 1. Streamlit標準ヘッダー・フッター・バッジの非表示化 */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header[data-testid="stHeader"] {display: none !important;}
    .stApp > header {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}

    /* 2. コンテナ余白と最大幅（スマホ片手操作に最適化、下部バッジ被り防止） */
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 5.5rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        max-width: 540px !important;
        margin: 0 auto !important;
    }

    /* 3. OSのダークモード設定に関わらず明るく見やすい配色を強制維持 */
    :root {
        color-scheme: light !important;
    }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
    }
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Segoe UI", sans-serif !important;
        color: #0F172A !important;
    }

    /* 全ての標準テキスト・見出し・ラベル・キャプションの文字色を明示固定（白飛び防止） */
    h1, h2, h3, h4, h5, h6,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stWidgetLabel"] p,
    label p {
        color: #0F172A !important;
    }
    [data-testid="stCaptionContainer"] p,
    .stCaption {
        color: #64748B !important;
        font-size: 0.82rem !important;
    }

    /* 4. ヒーローヘッダー＆ステップバー */
    .hero-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #FFFFFF !important;
        border-radius: 20px;
        padding: 1.1rem 1rem 1rem 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .hero-brand {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        margin-bottom: 0.2rem;
    }
    .hero-title {
        font-size: 1.4rem;
        font-weight: 900;
        color: #FFFFFF !important;
        letter-spacing: 0.5px;
        margin: 0;
    }
    .hero-sub {
        font-size: 0.75rem;
        color: #94A3B8 !important;
        font-weight: 600;
        letter-spacing: 1px;
        margin-bottom: 0.65rem;
    }
    .phase-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 0.38rem 1rem;
        border-radius: 9999px;
        font-size: 0.84rem;
        font-weight: 800;
        color: #FFFFFF !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
        margin-bottom: 0.75rem;
    }
    .pill-entry { background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); }
    .pill-seat  { background: linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%); }
    .pill-score { background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); }
    .pill-result{ background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); }

    /* 5段階ステップインジケーター */
    .stepper-row {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 4px;
        padding-top: 0.55rem;
        border-top: 1px solid rgba(255, 255, 255, 0.12);
    }
    .step-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 3px;
    }
    .step-bar {
        width: 100%;
        height: 4px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.18);
    }
    .step-done .step-bar { background: #34D399; }
    .step-active .step-bar { background: #60A5FA; box-shadow: 0 0 8px #60A5FA; }
    .step-label {
        font-size: 0.68rem;
        font-weight: 700;
        color: #64748B !important;
    }
    .step-done .step-label { color: #A7F3D0 !important; }
    .step-active .step-label { color: #FFFFFF !important; font-weight: 800; }

    /* 5. ナビゲーションバー（100%横幅・5等分グリッドタブ） */
    [data-testid="stElementContainer"]:has([data-testid="stRadio"]),
    div[data-testid="stRadio"],
    div[data-testid="stRadio"] > div {
        width: 100% !important;
    }
    div[role="radiogroup"] {
        display: grid !important;
        grid-template-columns: repeat(5, 1fr) !important;
        width: 100% !important;
        background: #FFFFFF !important;
        padding: 5px !important;
        border-radius: 16px !important;
        gap: 4px !important;
        margin-bottom: 1rem !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05) !important;
        box-sizing: border-box !important;
    }
    div[role="radiogroup"] > div {
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        display: flex !important;
    }
    div[role="radiogroup"] label {
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 8px 2px !important;
        background: transparent !important;
        border-radius: 11px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        box-sizing: border-box !important;
    }
    div[role="radiogroup"] label:hover {
        background: #F1F5F9 !important;
    }
    div[role="radiogroup"] label > div {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
    }
    /* ラジオボタンの丸ポチのみを消去 */
    div[role="radiogroup"] label > div > div:first-child:not([data-testid="stMarkdownContainer"]) {
        display: none !important;
    }
    div[role="radiogroup"] label [data-testid="stMarkdownContainer"] {
        width: 100% !important;
        text-align: center !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    div[role="radiogroup"] label [data-testid="stMarkdownContainer"] p {
        margin: 0 !important;
        font-size: 0.78rem !important;
        font-weight: 800 !important;
        color: #475569 !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
    }
    /* アクティブタブのスタイル */
    div[role="radiogroup"] label:has(input:checked),
    div[role="radiogroup"] label[data-selected="true"] {
        background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%) !important;
        box-shadow: 0 3px 8px rgba(79, 70, 229, 0.3) !important;
    }
    div[role="radiogroup"] label:has(input:checked) [data-testid="stMarkdownContainer"] p,
    div[role="radiogroup"] label[data-selected="true"] [data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
    }

    /* 6. コンテンツカード & セクションヘッダー */
    .surface-card {
        background: #FFFFFF;
        border-radius: 18px;
        padding: 1.1rem 1.15rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
        margin-bottom: 0.9rem;
    }
    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.45rem;
    }
    .section-title {
        font-size: 1.08rem !important;
        font-weight: 800 !important;
        color: #0F172A !important;
        margin: 0 !important;
        line-height: 1.35 !important;
    }
    .section-desc {
        font-size: 0.83rem !important;
        color: #64748B !important;
        margin-top: 0.25rem !important;
        margin-bottom: 0.85rem !important;
        line-height: 1.45 !important;
    }

    /* カスタムプログレスバー */
    .custom-progress-bg {
        width: 100%;
        height: 10px;
        background-color: #E2E8F0;
        border-radius: 999px;
        overflow: hidden;
        margin: 0.45rem 0;
    }
    .custom-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #4F46E5 0%, #3B82F6 100%);
        border-radius: 999px;
        transition: width 0.3s ease;
    }

    /* 7. 座席チケットバナー */
    .seat-ticket {
        border-radius: 20px;
        padding: 1.35rem 1.1rem;
        text-align: center;
        margin: 0.75rem 0 1rem 0;
        position: relative;
        box-shadow: 0 10px 20px -5px rgba(15, 23, 42, 0.12);
    }
    .seat-ticket-label {
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .seat-ticket-main {
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: 0.5px;
        margin: 0.2rem 0 0.4rem 0;
        line-height: 1.15;
    }
    .seat-ticket-sub {
        display: inline-block;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.75);
    }

    /* 8. ランキングカード */
    .rank-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.8rem 1rem;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        background-color: #FFFFFF;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 5px rgba(15, 23, 42, 0.03);
    }
    .rank-top1 {
        background: linear-gradient(135deg, #FEF9C3 0%, #FFFBEB 100%);
        border: 1.5px solid #FACC15;
        box-shadow: 0 4px 10px rgba(250, 204, 21, 0.18);
    }
    .rank-top2 {
        background: linear-gradient(135deg, #F1F5F9 0%, #FFFFFF 100%);
        border: 1.5px solid #94A3B8;
    }
    .rank-top3 {
        background: linear-gradient(135deg, #FFEDD5 0%, #FFF7ED 100%);
        border: 1.5px solid #FB923C;
    }
    .rank-badge {
        font-size: 1.1rem;
        font-weight: 900;
        min-width: 2.4rem;
        text-align: center;
        color: #0F172A !important;
    }
    .rank-name-box { flex-grow: 1; margin-left: 0.55rem; min-width: 0; }
    .rank-name {
        font-size: 0.98rem;
        font-weight: 800;
        color: #0F172A !important;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 4px;
    }
    .rank-meta {
        font-size: 0.75rem;
        color: #64748B !important;
        margin-top: 2px;
    }
    .rank-score-box { text-align: right; margin-left: 0.5rem; white-space: nowrap; }
    .rank-points-text { font-size: 1.15rem; font-weight: 900; color: #4F46E5 !important; }
    .rank-score-text { font-size: 0.75rem; color: #64748B !important; font-weight: 600; }

    /* タグバッジ */
    .role-badge-admin {
        background-color: #FEF3C7;
        color: #B45309 !important;
        font-size: 0.68rem;
        padding: 2px 7px;
        border-radius: 6px;
        font-weight: 800;
        border: 1px solid #FDE68A;
        vertical-align: middle;
    }
    .role-badge-gen {
        background-color: #F1F5F9;
        color: #475569 !important;
        font-size: 0.68rem;
        padding: 2px 7px;
        border-radius: 6px;
        font-weight: 700;
        border: 1px solid #E2E8F0;
        vertical-align: middle;
    }

    /* 9. フォーム・入力欄・セレクトボックス・ボタン（ダークモード時の黒背景化・白文字化を完全防止） */
    [data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 18px !important;
        padding: 1.15rem !important;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04) !important;
    }
    .stTextInput > div > div,
    .stNumberInput > div > div,
    .stSelectbox > div > div {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        border-radius: 12px !important;
        border: 1.5px solid #CBD5E1 !important;
    }
    .stTextInput input,
    .stNumberInput input,
    .stSelectbox div[data-baseweb="select"] * {
        color: #0F172A !important;
        -webkit-text-fill-color: #0F172A !important;
        background-color: transparent !important;
        font-weight: 600 !important;
    }
    .stTextInput input::placeholder {
        color: #94A3B8 !important;
        -webkit-text-fill-color: #94A3B8 !important;
        opacity: 1 !important;
    }
    .stNumberInput input {
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        text-align: center !important;
    }
    /* 数値入力の＋/ーボタン */
    .stNumberInput button {
        background-color: #E2E8F0 !important;
        color: #0F172A !important;
    }

    /* 通常ボタン & フォーム送信ボタン共通スタイル */
    .stButton > button,
    .stFormSubmitButton > button,
    .stDownloadButton > button {
        border-radius: 12px !important;
        min-height: 3rem !important;
        padding: 0.65rem 1.1rem !important;
        font-weight: 800 !important;
        font-size: 0.98rem !important;
        transition: all 0.15s ease !important;
        border: 1px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }
    .stButton > button p,
    .stFormSubmitButton > button p,
    .stDownloadButton > button p {
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 0.98rem !important;
    }
    /* Primaryボタン（送信・メインアクション） */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primaryFormSubmit"] {
        background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
    }
    .stButton > button[kind="primary"] p,
    .stFormSubmitButton > button[kind="primary"] p,
    .stDownloadButton > button[kind="primary"] p,
    button[data-testid="stBaseButton-primary"] p,
    button[data-testid="stBaseButton-primaryFormSubmit"] p {
        color: #FFFFFF !important;
    }

    /* Expander と Tabs のスタイル調整 */
    [data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 14px !important;
        overflow: hidden !important;
    }
    [data-testid="stExpander"] summary {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-weight: 700 !important;
    }
    [data-testid="stExpander"] summary p {
        color: #0F172A !important;
        font-weight: 700 !important;
    }
    button[data-baseweb="tab"] {
        font-weight: 700 !important;
        color: #475569 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #4F46E5 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# ヘッダー & ナビゲーション
# ==============================================================================
def get_phase_step_index(current_phase: str) -> int:
    """5段階ステップ（0:エントリー, 1:予選1, 2:予選2, 3:決勝, 4:結果発表）のインデックスを返します。"""
    if current_phase == PHASE_ENTRY:
        return 0
    elif "予選１" in current_phase:
        return 1
    elif "予選２" in current_phase:
        return 2
    elif "決勝" in current_phase:
        return 3
    else:
        return 4


def render_header_and_nav():
    current_phase = db.get_setting("current_phase", PHASE_ENTRY)

    if "準備" in current_phase:
        pill_class = "pill-seat"
        phase_icon = "🪑"
    elif "結果入力" in current_phase:
        pill_class = "pill-score"
        phase_icon = "🎲"
    elif "結果発表" in current_phase:
        pill_class = "pill-result"
        phase_icon = "🏆"
    else:
        pill_class = "pill-entry"
        phase_icon = "📝"

    active_step = get_phase_step_index(current_phase)
    step_names = ["エントリー", "予選1", "予選2", "決勝", "結果発表"]
    steps_html = ""
    for idx, s_name in enumerate(step_names):
        if idx < active_step:
            st_cls = "step-item step-done"
        elif idx == active_step:
            st_cls = "step-item step-active"
        else:
            st_cls = "step-item"
        steps_html += f'<div class="{st_cls}"><div class="step-bar"></div><div class="step-label">{s_name}</div></div>'

    st.markdown(
        f'<div class="hero-card">'
        f'<div class="hero-brand">'
        f'<span style="font-size: 1.5rem;">🐼</span>'
        f'<div class="hero-title">パンダロイヤル</div>'
        f'</div>'
        f'<div class="hero-sub">DICE GAME TOURNAMENT MANAGER</div>'
        f'<div class="phase-pill {pill_class}">'
        f'<span>{phase_icon}</span><span>{current_phase}</span>'
        f'</div>'
        f'<div class="stepper-row">{steps_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    menu_options = [
        "🏠 ホーム",
        "📊 順位",
        "🪑 座席",
        "📱 QR",
        "⚙️ 管理",
    ]

    if "current_page" not in st.session_state or st.session_state["current_page"] not in menu_options:
        st.session_state["current_page"] = menu_options[0]

    selected_menu = st.radio(
        "ナビゲーション",
        menu_options,
        index=menu_options.index(st.session_state["current_page"]),
        horizontal=True,
        label_visibility="collapsed",
        key="main_nav_radio",
    )
    st.session_state["current_page"] = selected_menu

    return selected_menu, current_phase


# ==============================================================================
# 共通UIパーツ: 卓別座席リスト描画
# ==============================================================================
def render_table_seats_cards(seats: list, highlight_player_id: int = -1):
    """卓ごとの座席表をカラーテーマ付きカード＆タブで描画します。"""
    if not seats:
        st.info("まだ座席割り当てデータがありません。")
        return

    tables: dict = {}
    for s in seats:
        tables.setdefault(s["table_name"], []).append(s)

    table_names = list(tables.keys())
    tab_labels = [get_table_theme(t)["badge"] for t in table_names] + ["📋 全卓一覧"]
    tabs = st.tabs(tab_labels)

    def _build_table_html(t_name: str, t_players: list) -> str:
        theme = get_table_theme(t_name)
        t_players_sorted = sorted(t_players, key=lambda x: x["seat_number"])
        rows_html = ""
        for p in t_players_sorted:
            is_me = p["player_id"] == highlight_player_id
            role_badge = (
                '<span class="role-badge-admin">運営</span>'
                if p["role"] == "admin"
                else '<span class="role-badge-gen">一般</span>'
            )
            me_badge = (
                '<span style="background:#4F46E5;color:#FFF;font-size:0.68rem;padding:2px 6px;border-radius:99px;margin-left:6px;font-weight:800;">あなた</span>'
                if is_me
                else ""
            )
            row_bg = "#EEF2FF" if is_me else "#FFFFFF"
            row_border = f"2px solid {theme['accent']}" if is_me else "1px solid #F1F5F9"
            rows_html += (
                f'<div style="background:{row_bg}; border:{row_border}; border-radius:10px; padding:0.55rem 0.85rem; margin-bottom:0.35rem; display:flex; justify-content:space-between; align-items:center;">'
                f'<div style="display:flex; align-items:center; gap:10px;">'
                f'<span style="background:{theme["bg"]}; color:{theme["accent"]}; border:1px solid {theme["border"]}; font-weight:900; font-size:0.85rem; width:2rem; height:2rem; border-radius:8px; display:inline-flex; align-items:center; justify-content:center;">{p["seat_number"]}</span>'
                f'<span style="font-size:0.96rem; font-weight:700; color:#0F172A;">{p["player_name"]}</span>'
                f'{me_badge}'
                f'</div>'
                f'<div>{role_badge}</div>'
                f'</div>'
            )
        return (
            f'<div style="background:{theme["bg"]}; border:1.5px solid {theme["border"]}; border-radius:16px; padding:0.9rem; margin-bottom:0.85rem;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; padding:0 0.2rem;">'
            f'<span style="font-size:1.05rem; font-weight:900; color:{theme["accent"]};">{theme["badge"]}</span>'
            f'<span style="font-size:0.78rem; font-weight:700; color:#475569; background:#FFFFFF; padding:2px 10px; border-radius:99px; border:1px solid {theme["border"]};">{len(t_players_sorted)} 名</span>'
            f'</div>'
            f'{rows_html}'
            f'</div>'
        )

    for idx, t_name in enumerate(table_names):
        with tabs[idx]:
            st.markdown(_build_table_html(t_name, tables[t_name]), unsafe_allow_html=True)

    with tabs[-1]:
        for t_name in table_names:
            st.markdown(_build_table_html(t_name, tables[t_name]), unsafe_allow_html=True)


# ==============================================================================
# 1. エントリーフェーズ画面
# ==============================================================================
def render_phase_entry():
    players = db.get_all_players()
    current_count = len(players)
    pct = min(int((current_count / 30.0) * 100), 100)

    st.markdown(
        f'<div class="surface-card">'
        f'<div class="section-header">'
        f'<div class="section-title">📝 参加者エントリー受付</div>'
        f'<span style="font-size: 1.05rem; font-weight: 900; color: #4F46E5;">'
        f'{current_count} <span style="font-size: 0.8rem; color: #64748B; font-weight: 600;">/ 30名</span>'
        f'</span>'
        f'</div>'
        f'<div class="custom-progress-bg"><div class="custom-progress-fill" style="width: {pct}%;"></div></div>'
        f'<div style="font-size: 0.8rem; color: #64748B; margin-top: 0.3rem;">'
        f'つなげーとIDと大会で表示するニックネームを入力して登録してください。'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if current_count >= 30:
        st.warning("⚠️ 定員（30名）に達しています。")

    with st.form("phase_entry_form", clear_on_submit=True):
        tsunagate_id = st.text_input("つなげーとID (必須)", placeholder="例: panda_1234")
        player_name = st.text_input("ニックネーム / 表示名 (必須)", placeholder="例: たろう")

        submitted = st.form_submit_button("✅ 大会にエントリーする", use_container_width=True, type="primary")

        if submitted:
            if not tsunagate_id.strip():
                st.error("つなげーとIDを入力してください。")
                return
            if not player_name.strip():
                st.error("ニックネームを入力してください。")
                return

            ok, msg = db.add_player(tsunagate_id, player_name, "general")
            if ok:
                st.balloons()
                st.success(f"🎉 {player_name} さんのエントリーが完了しました！")
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    # エントリー済みメンバー一覧カード
    if players:
        items_html = '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;">'
        for idx, p in enumerate(players, 1):
            role_label = (
                '<span class="role-badge-admin">運営</span>'
                if p["role"] == "admin"
                else '<span class="role-badge-gen">一般</span>'
            )
            items_html += (
                f'<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:0.5rem 0.65rem; display:flex; align-items:center; justify-content:space-between;">'
                f'<div style="min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">'
                f'<span style="font-size:0.75rem; font-weight:800; color:#64748B; margin-right:3px;">{idx}.</span>'
                f'<span style="font-size:0.88rem; font-weight:700; color:#0F172A;">{p["name"]}</span>'
                f'</div>'
                f'{role_label}'
                f'</div>'
            )
        items_html += "</div>"
    else:
        items_html = '<div style="text-align:center; padding:0.8rem 0; color:#64748B; font-size:0.86rem;">まだエントリーしている参加者はいません。一番乗りで登録しましょう！</div>'

    st.markdown(
        f'<div class="surface-card" style="margin-top: 0.85rem;">'
        f'<div class="section-header" style="margin-bottom: 0.65rem;">'
        f'<div class="section-title" style="font-size: 0.98rem;">👥 エントリー済み参加者 ({current_count}名)</div>'
        f'</div>'
        f'{items_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ==============================================================================
# 2. 準備フェーズ画面（席替え表示・座席案内）
# ==============================================================================
def render_phase_seating(round_name: str, phase_title: str):
    st.markdown(
        f'<div class="surface-card">'
        f'<div class="section-title">🪑 {phase_title}</div>'
        f'<div class="section-desc" style="margin-bottom:0;">'
        f'座席抽選が完了しました！ご自身のお名前を選択して座席番号を確認し、テーブルへ移動してください。'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    players = db.get_all_players()
    if not players:
        st.warning("参加者が登録されていません。")
        return

    player_options = {p["name"]: p for p in players}
    player_display_list = ["-- あなたのお名前を選択してください --"] + list(player_options.keys())
    selected_name = st.selectbox("👤 あなたのお名前", player_display_list, key=f"seat_sel_{round_name}")

    selected_player_id = -1
    if selected_name != "-- あなたのお名前を選択してください --":
        selected_player = player_options[selected_name]
        selected_player_id = selected_player["id"]

        seat_info = db.get_player_seat(round_name, selected_player_id)
        if not seat_info:
            st.error(f"⚠️ {round_name} の座席データがまだ作成されていません。運営の抽選完了をお待ちください。")
        else:
            table_name = seat_info["table_name"]
            seat_number = seat_info["seat_number"]
            theme = get_table_theme(table_name)

            st.markdown(
                f'<div class="seat-ticket" style="background:{theme["bg"]}; border:2.5px solid {theme["accent"]};">'
                f'<div class="seat-ticket-label" style="color:{theme["accent"]};">📍 {selected_name} さんの {round_name} 座席チケット</div>'
                f'<div class="seat-ticket-main" style="color:#0F172A;">{theme["badge"]} &nbsp; <span style="color:{theme["accent"]};">{seat_number}番席</span></div>'
                f'<div class="seat-ticket-sub" style="color:{theme["accent"]}; border:1px solid {theme["border"]};">👉 {table_name} の {seat_number}番席 へご着席ください</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(f'<div style="font-size:1rem; font-weight:800; color:#0F172A; margin:0.6rem 0 0.4rem 0;">🗺️ {round_name} テーブル別座席表</div>', unsafe_allow_html=True)
    seats = db.get_seats_by_round(round_name)
    render_table_seats_cards(seats, highlight_player_id=selected_player_id)

    if round_name in ["予選2", "決勝"]:
        with st.expander("📊 これまでの暫定総合順位を見る", expanded=False):
            rounds_to_calc = ["予選1"] if round_name == "予選2" else ["予選1", "予選2"]
            all_scs = db.get_all_scores_summary()
            rankings = logic.calculate_overall_ranking(players, all_scs, target_rounds=rounds_to_calc)
            for p in rankings:
                st.markdown(
                    f'<div style="display:flex; justify-content:space-between; padding:0.45rem 0.2rem; border-bottom:1px solid #F1F5F9; font-size:0.9rem;">'
                    f'<div><strong>{p["overall_rank"]}位</strong> &nbsp; {p["player_name"]}</div>'
                    f'<div><strong style="color:#4F46E5;">{p["total_rank_points"]} pt</strong> <span style="color:#64748B;font-size:0.8rem;">(計{p["total_score"]}点)</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ==============================================================================
# 3. 結果入力フェーズ画面 (スコア報告)
# ==============================================================================
def render_phase_score_input(round_name: str, phase_title: str):
    st.markdown(
        f'<div class="surface-card">'
        f'<div class="section-title">🎲 {phase_title}</div>'
        f'<div class="section-desc" style="margin-bottom:0;">'
        f'ゲーム終了後、ご自身のお名前を選択して獲得した素点スコアを送信してください。'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    players = db.get_all_players()
    if not players:
        st.warning("参加者が登録されていません。")
        return

    player_options = {p["name"]: p for p in players}
    player_display_list = ["-- あなたのお名前を選択してください --"] + list(player_options.keys())
    selected_name = st.selectbox("👤 あなたのお名前", player_display_list, key=f"score_sel_{round_name}")

    if selected_name == "-- あなたのお名前を選択してください --":
        return

    selected_player = player_options[selected_name]
    player_id = selected_player["id"]

    seat_info = db.get_player_seat(round_name, player_id)
    if not seat_info:
        st.error(f"⚠️ {round_name} の座席情報がありません。運営スタッフにお声がけください。")
        return

    table_name = seat_info["table_name"]
    seat_number = seat_info["seat_number"]
    theme = get_table_theme(table_name)

    st.markdown(
        f'<div style="background:{theme["bg"]}; border:1.5px solid {theme["border"]}; border-radius:14px; padding:0.75rem 1rem; margin:0.4rem 0 0.85rem 0; display:flex; justify-content:space-between; align-items:center;">'
        f'<div>'
        f'<div style="font-size:0.75rem; color:#475569; font-weight:700;">あなたの対戦テーブル</div>'
        f'<div style="font-size:1.15rem; font-weight:900; color:{theme["accent"]};">{theme["badge"]} {seat_number}番席</div>'
        f'</div>'
        f'<span style="font-size:0.75rem; background:#FFFFFF; color:#475569; padding:4px 10px; border-radius:99px; border:1px solid {theme["border"]}; font-weight:700;">自動判定済</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    existing_scores = db.get_scores_by_round(round_name)
    current_sc = None
    for s in existing_scores:
        if s["player_id"] == player_id:
            current_sc = s["score"]
            break

    with st.form("score_input_form"):
        default_val = current_sc if current_sc is not None else 0
        input_score = st.number_input(
            f"🎯 {round_name} の獲得スコア（素点）",
            min_value=0,
            max_value=9999,
            value=int(default_val),
            step=1,
        )

        if current_sc is not None:
            st.caption(f"✅ 現在登録されているスコア: {current_sc} 点（再送信で修正できます）")

        submit_btn = st.form_submit_button("📤 スコアを確定して送信する", use_container_width=True, type="primary")

        if submit_btn:
            db.save_score(round_name, player_id, int(input_score), table_name)
            scs = db.get_scores_by_round(round_name)
            calc = logic.calculate_table_ranks_and_points(scs)
            db.update_rank_points_in_db(round_name, calc)

            st.balloons()
            st.success(f"✅ {round_name} のスコア ({input_score}点) を記録しました！")
            st.rerun()

    # 同卓メンバーの入力状況カード
    table_scores = {s["player_id"]: s for s in existing_scores if s["table_name"] == table_name}
    seats_in_round = db.get_seats_by_round(round_name)
    table_seats = [s for s in seats_in_round if s["table_name"] == table_name]
    table_seats.sort(key=lambda x: x["seat_number"])

    done_cnt = len(table_scores)
    total_cnt = len(table_seats)
    pct = int((done_cnt / total_cnt) * 100) if total_cnt > 0 else 0

    st.markdown(
        f'<div class="surface-card" style="margin-top:0.9rem;">'
        f'<div class="section-header">'
        f'<div class="section-title" style="font-size:0.98rem;">👥 {table_name} のスコア入力状況</div>'
        f'<span style="font-size:0.88rem; font-weight:800; color:{theme["accent"]};">{done_cnt} / {total_cnt} 名完了</span>'
        f'</div>'
        f'<div class="custom-progress-bg"><div class="custom-progress-fill" style="width:{pct}%;"></div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for s_info in table_seats:
        pid = s_info["player_id"]
        p_sc_obj = table_scores.get(pid)
        is_me = pid == player_id
        border_style = f"2px solid {theme['accent']}" if is_me else "1px solid #E2E8F0"
        bg_style = "#EEF2FF" if is_me else "#FFFFFF"

        if p_sc_obj:
            st_str = f"<span style='font-weight:900;color:#4F46E5;font-size:0.98rem;'>{p_sc_obj['score']}点</span> <span style='font-size:0.78rem;color:#475569;background:#F1F5F9;padding:2px 7px;border-radius:6px;font-weight:700;'>卓{p_sc_obj['rank_in_table']}位 / {p_sc_obj['rank_points']}pt</span>"
        else:
            st_str = "<span style='color:#94A3B8; font-size:0.82rem; font-weight:600;'>⏳ 未入力</span>"

        me_tag = '<span style="font-size:0.7rem; background:#4F46E5; color:#FFF; padding:1px 6px; border-radius:99px; margin-left:5px; font-weight:700;">あなた</span>' if is_me else ""
        st.markdown(
            f'<div style="padding:0.6rem 0.85rem; border-radius:10px; border:{border_style}; background:{bg_style}; margin-bottom:0.38rem; display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<span style="font-size:0.8rem; font-weight:800; color:#64748B; margin-right:6px;">{s_info["seat_number"]}番</span>'
            f'<span style="font-weight:700; color:#0F172A;">{s_info["player_name"]}</span>'
            f'{me_tag}'
            f'</div>'
            f'<div>{st_str}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ==============================================================================
# 4. 結果発表（最終スコア表示）フェーズ画面
# ==============================================================================
def render_phase_result():
    st.markdown(
        '<div class="surface-card" style="background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%); border: 2px solid #FCD34D; text-align: center;">'
        '<div style="font-size: 1.45rem; font-weight: 900; color: #78350F;">🏆 最終結果発表・表彰式 🏆</div>'
        '<div style="font-size: 0.84rem; color: #92400E; margin-top: 0.25rem; font-weight: 700;">パンダロイヤル全ラウンド終了！お疲れ様でした！</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    players = db.get_all_players()
    all_scores = db.get_all_scores_summary()

    if not players:
        st.info("まだ参加者データがありません。")
        return

    final_scores = db.get_scores_by_round("決勝")

    if final_scores:
        champ_scores = [s for s in final_scores if s["table_name"] == "チャンピオン卓"]
        champ_scores.sort(key=lambda x: x["score"], reverse=True)

        if champ_scores:
            p1 = champ_scores[0]
            st.markdown(
                f'<div style="background: linear-gradient(135deg, #FEF08A 0%, #FDE047 100%); border-radius: 18px; padding: 1.3rem; text-align: center; margin-bottom: 0.75rem; box-shadow: 0 8px 16px -3px rgba(234, 179, 8, 0.25); border: 2px solid #EAB308;">'
                f'<div style="font-size: 0.9rem; font-weight: 900; color: #854D0E; letter-spacing: 1px;">👑 CHAMPION 総合優勝 👑</div>'
                f'<div style="font-size: 1.85rem; font-weight: 900; color: #713F12; margin: 0.25rem 0;">{p1["player_name"]} 選手</div>'
                f'<div style="display:inline-block; background:#FFFFFF; color:#854D0E; padding:3px 14px; border-radius:99px; font-size:0.95rem; font-weight:800;">決勝スコア: {p1["score"]} 点</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if len(champ_scores) > 1:
                p2 = champ_scores[1]
                p3_html = ""
                if len(champ_scores) > 2:
                    p3 = champ_scores[2]
                    p3_html = (
                        f'<div style="background:#FFF7ED; border-radius:14px; padding:0.85rem; text-align:center; border:1.5px solid #FDBA74;">'
                        f'<div style="font-size:0.8rem; font-weight:800; color:#9A3412;">🥉 第3位</div>'
                        f'<div style="font-size:1.1rem; font-weight:900; color:#0F172A; margin:2px 0;">{p3["player_name"]}</div>'
                        f'<div style="font-size:0.82rem; font-weight:700; color:#64748B;">{p3["score"]} 点</div>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:8px; margin-bottom:1rem;">'
                    f'<div style="background:#F8FAFC; border-radius:14px; padding:0.85rem; text-align:center; border:1.5px solid #CBD5E1;">'
                    f'<div style="font-size:0.8rem; font-weight:800; color:#475569;">🥈 準優勝</div>'
                    f'<div style="font-size:1.1rem; font-weight:900; color:#0F172A; margin:2px 0;">{p2["player_name"]}</div>'
                    f'<div style="font-size:0.82rem; font-weight:700; color:#64748B;">{p2["score"]} 点</div>'
                    f'</div>'
                    f'{p3_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown('<div style="font-size:1rem; font-weight:800; color:#0F172A; margin:0.6rem 0 0.4rem 0;">🏅 全ラウンド総合ランキング</div>', unsafe_allow_html=True)
    rankings_all = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選1", "予選2", "決勝"])
    render_ranking_cards_list(rankings_all, ["予選1", "予選2", "決勝"], show_cutoff=False)


# ==============================================================================
# サブ画面: 総合順位 (閲覧用)
# ==============================================================================
def render_ranking_cards_list(rankings: list, target_rounds: list, show_cutoff: bool = False):
    for p in rankings:
        rank = p["overall_rank"]
        card_class = "rank-card"
        badge_icon = f"{rank}"
        if rank == 1:
            card_class += " rank-top1"
            badge_icon = "👑 1"
        elif rank == 2:
            card_class += " rank-top2"
            badge_icon = "🥈 2"
        elif rank == 3:
            card_class += " rank-top3"
            badge_icon = "🥉 3"

        role_tag = '<span class="role-badge-admin">運営</span>' if p["role"] == "admin" else ""

        detail_texts = []
        for r_name in target_rounds:
            r_obj = p["round_details"].get(r_name)
            short_r = "予1" if r_name == "予選1" else ("予2" if r_name == "予選2" else "決")
            if r_obj:
                detail_texts.append(f"{short_r}: {r_obj['score']}点({r_obj['rank_points']}pt)")
            else:
                detail_texts.append(f"{short_r}: -")
        detail_str = " / ".join(detail_texts)

        if show_cutoff and rank == 11:
            st.markdown(
                '<div style="text-align: center; margin: 0.65rem 0; padding: 0.35rem; background: linear-gradient(90deg, #FEF3C7, #FDE68A, #FEF3C7); color: #92400E; border-radius: 8px; font-size: 0.78rem; font-weight: 900; border: 1px solid #FCD34D;">'
                '▲ 上位10名 チャンピオン卓進出ライン ▲'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            f'<div class="{card_class}">'
            f'<div class="rank-badge">{badge_icon}</div>'
            f'<div class="rank-name-box">'
            f'<div class="rank-name">{p["player_name"]} {role_tag}</div>'
            f'<div class="rank-meta">{detail_str}</div>'
            f'</div>'
            f'<div class="rank-score-box">'
            f'<div class="rank-points-text">{p["total_rank_points"]} pt</div>'
            f'<div class="rank-score-text">計 {p["total_score"]} 点</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_ranking_page():
    st.markdown(
        '<div class="surface-card">'
        '<div class="section-title">📊 総合順位ランキング</div>'
        '<div class="section-desc" style="margin-bottom:0;">'
        '順位決定ルール: 順位点（1位10pt〜）の合計優先 ＞ 同点の場合は獲得スコア（素点）合計優先'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    players = db.get_all_players()
    if not players:
        st.info("まだ参加者が登録されていません。")
        return

    all_scores = db.get_all_scores_summary()
    r_tabs = st.tabs(["🔥 予選総合 (予1+予2)", "1️⃣ 予選1のみ", "2️⃣ 予選2のみ", "🏆 全ラウンド総合"])

    with r_tabs[0]:
        rk = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選1", "予選2"])
        render_ranking_cards_list(rk, ["予選1", "予選2"], show_cutoff=True)
    with r_tabs[1]:
        rk = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選1"])
        render_ranking_cards_list(rk, ["予選1"], show_cutoff=False)
    with r_tabs[2]:
        rk = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選2"])
        render_ranking_cards_list(rk, ["予選2"], show_cutoff=False)
    with r_tabs[3]:
        rk = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選1", "予選2", "決勝"])
        render_ranking_cards_list(rk, ["予選1", "予選2", "決勝"], show_cutoff=False)


# ==============================================================================
# サブ画面: 座席表一覧 (閲覧用)
# ==============================================================================
def render_seats_page():
    st.markdown(
        '<div class="surface-card">'
        '<div class="section-title">🪑 ラウンド別 座席表一覧</div>'
        '<div class="section-desc" style="margin-bottom:0;">'
        '各ラウンドのテーブル割り当てと着席番号を確認できます。'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    round_tabs = st.tabs(["1️⃣ 予選1", "2️⃣ 予選2", "🏆 決勝"])
    for idx, r_name in enumerate(["予選1", "予選2", "決勝"]):
        with round_tabs[idx]:
            seats = db.get_seats_by_round(r_name)
            render_table_seats_cards(seats)


# ==============================================================================
# サブ画面: 参加用QRコード
# ==============================================================================
def render_qr_page():
    access_url = get_current_access_url()
    qr_bytes = generate_qr_code_image(access_url)
    qr_b64 = base64.b64encode(qr_bytes).decode()

    st.markdown(
        f'<div class="surface-card" style="text-align: center; padding: 1.5rem 1rem;">'
        f'<div style="font-size: 1.15rem; font-weight: 900; color: #0F172A; margin-bottom: 0.25rem;">📱 スマホで簡単エントリー＆スコア入力</div>'
        f'<div style="font-size: 0.82rem; color: #64748B; margin-bottom: 1rem;">カメラアプリで下のQRコードを読み取ってください</div>'
        f'<div style="display: flex; justify-content: center; margin: 0.5rem 0 1rem 0;">'
        f'<img src="data:image/png;base64,{qr_b64}" style="width: 240px; height: 240px; border-radius: 16px; border: 2px solid #E2E8F0; padding: 8px; background: #FFFFFF;" />'
        f'</div>'
        f'<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.55rem; font-family: monospace; font-size: 0.88rem; font-weight: 700; color: #2563EB; word-break: break-all; margin-bottom: 0.4rem;">{access_url}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.download_button(
        "📥 QRコード画像を保存する (印刷・配布用)",
        data=qr_bytes,
        file_name="panda_royal_qr.png",
        mime="image/png",
        use_container_width=True,
        type="primary",
    )


# ==============================================================================
# 画面4: 管理者ページ (8フェーズ設定コントロール搭載)
# ==============================================================================
def render_admin_page():
    st.markdown(
        '<div class="surface-card">'
        '<div class="section-title">⚙️ 運営管理コンソール</div>'
        '<div class="section-desc" style="margin-bottom:0;">'
        'フェーズ進行の切り替え、運営スタッフのタグ付け、座席抽選を行います。'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        with st.form("admin_auth_form"):
            pw_input = st.text_input("🔑 管理者パスワード", type="password", placeholder="パスワードを入力")
            if st.form_submit_button("🔓 管理画面にログイン", use_container_width=True, type="primary"):
                if pw_input == DEFAULT_ADMIN_PASSWORD:
                    st.session_state["admin_logged_in"] = True
                    st.rerun()
                else:
                    st.error("パスワードが正しくありません。")
        return

    # 進行フェーズ設定カード
    current_phase = db.get_setting("current_phase", PHASE_ENTRY)
    curr_idx = ALL_PHASES.index(current_phase) if current_phase in ALL_PHASES else 0

    st.markdown("##### 🚩 大会フェーズ進行コントロール")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if curr_idx > 0:
            prev_phase = ALL_PHASES[curr_idx - 1]
            if st.button(f"⬅️ 戻す: {prev_phase}", use_container_width=True):
                db.set_setting("current_phase", prev_phase)
                st.rerun()
    with col_next:
        if curr_idx < len(ALL_PHASES) - 1:
            next_phase = ALL_PHASES[curr_idx + 1]
            if st.button(f"次へ進める ➔ {next_phase}", use_container_width=True, type="primary"):
                db.set_setting("current_phase", next_phase)
                st.rerun()

    selected_new_phase = st.selectbox(
        "フェーズを直接指定して切り替え",
        ALL_PHASES,
        index=curr_idx,
        key="admin_phase_selector_box",
    )

    if selected_new_phase != current_phase:
        db.set_setting("current_phase", selected_new_phase)
        st.success(f"フェーズを「{selected_new_phase}」に切り替えました！")
        st.rerun()

    players = db.get_all_players()
    total_count = len(players)
    admin_count = sum(1 for p in players if p["role"] == "admin")
    gen_count = sum(1 for p in players if p["role"] == "general")

    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; margin:0.75rem 0;">
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:0.6rem; text-align:center;">
                <div style="font-size:0.72rem; color:#64748B; font-weight:700;">総エントリー</div>
                <div style="font-size:1.25rem; font-weight:900; color:#0F172A;">{total_count}名</div>
            </div>
            <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:12px; padding:0.6rem; text-align:center;">
                <div style="font-size:0.72rem; color:#B45309; font-weight:700;">運営スタッフ</div>
                <div style="font-size:1.25rem; font-weight:900; color:#B45309;">{admin_count}名</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:0.6rem; text-align:center;">
                <div style="font-size:0.72rem; color:#475569; font-weight:700;">一般参加</div>
                <div style="font-size:1.25rem; font-weight:900; color:#334155;">{gen_count}名</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    admin_tabs = st.tabs([
        "👥 タグ付け",
        "🎯 座席抽選",
        "📊 入力進捗",
        "📱 URL設定",
        "🛠️ 管理/DB",
    ])

    # タブ1: 属性タグ付け
    with admin_tabs[0]:
        if not players:
            st.info("参加者がまだいません。")
        else:
            for p in players:
                is_admin = p["role"] == "admin"
                col_p_info, col_p_btn = st.columns([3, 2])
                with col_p_info:
                    tag_html = '<span class="role-badge-admin">運営</span>' if is_admin else '<span class="role-badge-gen">一般</span>'
                    st.markdown(
                        f"**{p['name']}** {tag_html}<div style='font-size:0.75rem;color:#64748B;'>ID: {p['tsunagate_id']}</div>",
                        unsafe_allow_html=True,
                    )
                with col_p_btn:
                    btn_label = "一般に戻す" if is_admin else "運営にする"
                    next_role = "general" if is_admin else "admin"
                    if st.button(btn_label, key=f"role_btn_{p['id']}", use_container_width=True):
                        db.update_player_role(p["id"], next_role)
                        st.rerun()

        with st.expander("➕ 手動エントリー (代理登録)"):
            with st.form("manual_add_form", clear_on_submit=True):
                m_tid = st.text_input("つなげーとID")
                m_name = st.text_input("お名前")
                m_role = st.selectbox("属性", ["一般", "運営"])
                if st.form_submit_button("登録する", use_container_width=True, type="primary"):
                    if m_tid.strip() and m_name.strip():
                        ok, msg = db.add_player(m_tid, m_name, "admin" if m_role == "運営" else "general")
                        if ok:
                            st.success(f"{m_name} さんを追加しました！")
                            st.rerun()
                        else:
                            st.error(msg)

        with st.expander("🗑️ 参加者削除"):
            if players:
                del_id = st.selectbox(
                    "削除するプレイヤー",
                    [p["id"] for p in players],
                    format_func=lambda pid: next(f"{p['name']} ({p['role']})" for p in players if p["id"] == pid),
                )
                if st.button("選択したプレイヤーを削除", use_container_width=True):
                    db.delete_player(del_id)
                    st.warning("削除しました。")
                    st.rerun()

    # タブ2: 座席抽選
    with admin_tabs[1]:
        if len(players) < 3:
            st.warning("座席抽選には3名以上の参加者が必要です。")
        else:
            with st.expander("🎲 予選1 座席抽選", expanded=True):
                st.caption("運営を各卓に均等配分し、一般参加者をシャッフル配分します。")
                if st.button("🚀 予選1の座席を抽選する", type="primary", use_container_width=True, key="adm_p1_btn"):
                    assignments = logic.assign_preliminary_seats(players, table_names=["A卓", "B卓", "C卓"])
                    db.save_seats("予選1", assignments)
                    st.success("予選1の座席を割り当てました！")
                    st.rerun()

            with st.expander("🎲 予選2 座席抽選", expanded=False):
                st.caption("予選2の座席をシャッフル配分します。")
                if st.button("🚀 予選2の座席を抽選する", type="primary", use_container_width=True, key="adm_p2_btn"):
                    assignments = logic.assign_preliminary_seats(players, table_names=["A卓", "B卓", "C卓"])
                    db.save_seats("予選2", assignments)
                    st.success("予選2の座席を割り当てました！")
                    st.rerun()

            with st.expander("🏆 決勝ラウンド座席抽選 (運営足切り付き)", expanded=True):
                curr_limit = int(db.get_setting("admin_limit_champion", "3"))
                admin_limit = st.slider(
                    "👑 チャンピオン卓の運営上限人数",
                    min_value=0,
                    max_value=10,
                    value=curr_limit,
                )
                if admin_limit != curr_limit:
                    db.set_setting("admin_limit_champion", str(admin_limit))

                if st.button("🏆 決勝座席抽選を実行", type="primary", use_container_width=True, key="adm_final_btn"):
                    all_scores = db.get_all_scores_summary()
                    overall_rankings = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選1", "予選2"])
                    final_assignments, swap_history = logic.assign_final_seats_with_admin_cutoff(
                        overall_rankings,
                        admin_limit_champion=admin_limit,
                    )
                    db.save_seats("決勝", final_assignments)
                    st.success("決勝ラウンドの座席割り当てが完了しました！")
                    if swap_history:
                        for sw in swap_history:
                            st.write(
                                f"🔻 運営 {sw['demoted_admin']} (予選{sw['demoted_rank']}位) ➔ シルバー卓へ\n"
                                f"🔺 一般 {sw['promoted_general']} (予選{sw['promoted_rank']}位) ➔ チャンピオン卓へ繰上昇格！"
                            )
                    st.rerun()

    # タブ3: 入力進捗
    with admin_tabs[2]:
        for r_name in ["予選1", "予選2", "決勝"]:
            r_seats = db.get_seats_by_round(r_name)
            r_scores = db.get_scores_by_round(r_name)
            sc_count = len(r_scores)
            st_count = len(r_seats)
            pct = int((sc_count / st_count) * 100) if st_count > 0 else 0

            st.markdown(
                f"""
                <div class="surface-card" style="padding:0.85rem 1rem; margin-bottom:0.6rem;">
                    <div style="display:flex; justify-content:space-between; font-weight:800; font-size:0.92rem;">
                        <span>{r_name}</span>
                        <span style="color:#4F46E5;">{sc_count} / {st_count} 名完了 ({pct}%)</span>
                    </div>
                    <div class="custom-progress-bg">
                        <div class="custom-progress-fill" style="width:{pct}%;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st_count > 0 and sc_count < st_count:
                entered_pids = {s["player_id"] for s in r_scores}
                unentered = [s["player_name"] for s in r_seats if s["player_id"] not in entered_pids]
                st.caption(f"未入力 ({r_name}): {', '.join(unentered)}")

    # タブ4: URL設定
    with admin_tabs[3]:
        current_url = get_current_access_url()
        custom_saved_url = db.get_setting("custom_access_url", "")
        st.markdown(f"現在のアクセスURL: `{current_url}`")

        with st.form("custom_url_form"):
            input_custom_url = st.text_input("公開URL", value=custom_saved_url, placeholder="https://panda-royal.streamlit.app/")
            if st.form_submit_button("💾 URLを保存する", use_container_width=True, type="primary"):
                db.set_setting("custom_access_url", input_custom_url.strip())
                st.success("アクセスURLを更新しました！")
                st.rerun()

    # タブ5: バックアップ/初期化
    with admin_tabs[4]:
        st.markdown("##### 💾 データベースのバックアップ & 復元")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            db_bytes = db.get_db_bytes()
            st.download_button(
                label="📥 DBバックアップ保存 (.db)",
                data=db_bytes,
                file_name="panda_royal_backup.db",
                mime="application/octet-stream",
                use_container_width=True,
            )
        with col_b2:
            uploaded_db = st.file_uploader("📤 バックアップから復元", type=["db"], label_visibility="collapsed")
            if uploaded_db is not None:
                if st.button("🔄 このバックアップで復元", type="primary", use_container_width=True):
                    if db.restore_db_from_bytes(uploaded_db.read()):
                        st.success("✅ データベースを復元しました！")
                        st.rerun()

        st.markdown("---")
        st.markdown("##### 🧪 リハーサル用ダミーデータ")
        if st.button("👥 30名のダミープレイヤーを一括作成", use_container_width=True):
            for i, name in enumerate(["運営A", "運営B", "運営C", "運営D", "運営E"], 1):
                db.add_player(f"admin_{i:02d}", name, "admin")
            for i in range(1, 26):
                db.add_player(f"user_{i:02d}", f"一般{i:02d}", "general")
            st.success("ダミー30名を登録しました！")
            st.rerun()

        if st.button("🎲 予選1・2・決勝のスコアを一括生成", use_container_width=True):
            for r_name in ["予選1", "予選2", "決勝"]:
                seats = db.get_seats_by_round(r_name)
                if not seats:
                    continue
                for s in seats:
                    db.save_score(r_name, s["player_id"], random.randint(30, 120), s["table_name"])
                scs = db.get_scores_by_round(r_name)
                calc = logic.calculate_table_ranks_and_points(scs)
                db.update_rank_points_in_db(r_name, calc)
            st.success("スコアを自動生成しました！")
            st.rerun()

        st.markdown("---")
        with st.expander("🚨 全データ削除（初期化）"):
            confirm_text = st.text_input("確認のため「RESET」と入力")
            if st.button("💥 全データをリセットする", type="primary", use_container_width=True):
                if confirm_text == "RESET":
                    db.reset_all_data()
                    st.success("リセット完了しました。")
                    st.rerun()
                else:
                    st.error("確認テキストが一致しません。")

        if st.button("🔒 管理者からログアウト", use_container_width=True):
            st.session_state["admin_logged_in"] = False
            st.rerun()


# ==============================================================================
# メインエントリーポイント
# ==============================================================================
def main():
    selected_menu, current_phase = render_header_and_nav()

    if selected_menu == "🏠 ホーム":
        if current_phase == PHASE_ENTRY:
            render_phase_entry()
        elif current_phase == PHASE_PRELIM1_SEAT:
            render_phase_seating("予選1", "予選1 席替え・座席発表")
        elif current_phase == PHASE_PRELIM1_SCORE:
            render_phase_score_input("予選1", "予選1 スコア結果入力")
        elif current_phase == PHASE_PRELIM2_SEAT:
            render_phase_seating("予選2", "予選2 席替え・座席発表")
        elif current_phase == PHASE_PRELIM2_SCORE:
            render_phase_score_input("予選2", "予選2 スコア結果入力")
        elif current_phase == PHASE_FINAL_SEAT:
            render_phase_seating("決勝", "決勝戦 進出卓発表・席替え")
        elif current_phase == PHASE_FINAL_SCORE:
            render_phase_score_input("決勝", "決勝戦 スコア結果入力")
        elif current_phase == PHASE_RESULT:
            render_phase_result()
        else:
            render_phase_entry()
    elif selected_menu == "📊 順位":
        render_ranking_page()
    elif selected_menu == "🪑 座席":
        render_seats_page()
    elif selected_menu == "📱 QR":
        render_qr_page()
    elif selected_menu == "⚙️ 管理":
        render_admin_page()


if __name__ == "__main__":
    main()
