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
    img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# 大会進行フェーズ定義（ご指定の8ステップ）
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

# ページ基本設定（スマホ画面に最適化）
st.set_page_config(
    page_title="パンダロイヤル",
    page_icon="🐼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# データベース初期化
db.init_db()

# モバイルファースト＆モダンWebアプリCSS定義
st.markdown(
    """
    <style>
    /* Streamlit標準のヘッダー・フッター・ツールバーを非表示にし、ネイティブアプリ化 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        display: none !important;
    }
    [data-testid="stToolbar"] {
        display: none !important;
    }
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
        max-width: 600px !important;
        margin: 0 auto !important;
    }

    /* アプリ全体の背景とベースフォント */
    .stApp {
        background-color: #F8FAFC !important;
    }
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif;
        color: #1E293B;
    }

    /* アプリ共通ヘッダー */
    .app-header {
        text-align: center;
        padding: 0.2rem 0 0.8rem 0;
        margin-bottom: 0.4rem;
    }
    .app-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.5px;
        margin: 0;
    }
    .app-subtitle {
        font-size: 0.82rem;
        color: #64748B;
        margin-top: 2px;
        font-weight: 500;
    }
    
    /* フェーズステータスバナー */
    .phase-badge-container {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: white;
        padding: 0.4rem 1.2rem;
        border-radius: 9999px;
        font-size: 0.88rem;
        font-weight: 700;
        margin-top: 0.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12);
    }
    .phase-badge-entry { background: linear-gradient(135deg, #2563EB, #1D4ED8); }
    .phase-badge-seat { background: linear-gradient(135deg, #7C3AED, #6D28D9); }
    .phase-badge-score { background: linear-gradient(135deg, #EA580C, #C2410C); }
    .phase-badge-result { background: linear-gradient(135deg, #DC2626, #991B1B); }

    /* ラジオボタンをタップしやすいモダンなタブバーへ変形 */
    div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        background: #E2E8F0 !important;
        padding: 5px !important;
        border-radius: 14px !important;
        gap: 4px !important;
        margin-bottom: 1.2rem !important;
        border: 1px solid #CBD5E1 !important;
    }
    div[role="radiogroup"] > label {
        flex: 1 1 0 !important;
        background: transparent !important;
        border-radius: 10px !important;
        padding: 8px 4px !important;
        font-weight: 700 !important;
        font-size: 0.82rem !important;
        cursor: pointer !important;
        transition: all 0.15s ease-in-out !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        color: #475569 !important;
        margin: 0 !important;
    }
    div[role="radiogroup"] > label:hover {
        background: rgba(255, 255, 255, 0.6) !important;
        color: #0F172A !important;
    }
    /* ラジオボタンの丸印を完全に非表示 */
    div[role="radiogroup"] label > div > div:first-child:not([data-testid="stMarkdownContainer"]) {
        display: none !important;
    }
    div[role="radiogroup"] label > div {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }
    div[role="radiogroup"] label p {
        margin: 0 !important;
        font-size: 0.84rem !important;
        font-weight: 700 !important;
        color: #475569 !important;
    }
    /* 選択中のタブの背景ハイライト */
    div[role="radiogroup"] label:has(input[type="radio"]:checked) {
        background: #4F46E5 !important;
        box-shadow: 0 2px 6px rgba(79, 70, 229, 0.35) !important;
    }
    div[role="radiogroup"] label:has(input[type="radio"]:checked) p {
        color: #FFFFFF !important;
        font-weight: 800 !important;
    }

    /* スマホで見やすいカードUI */
    .mobile-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        margin-bottom: 1rem;
    }
    
    /* 座席お知らせビッグバナー */
    .seat-banner {
        background: linear-gradient(135deg, #4F46E5 0%, #3B82F6 100%);
        color: #FFFFFF;
        border-radius: 20px;
        padding: 1.5rem 1.2rem;
        text-align: center;
        margin: 0.8rem 0 1.2rem 0;
        box-shadow: 0 10px 20px -3px rgba(79, 70, 229, 0.35);
    }
    .seat-banner-title {
        font-size: 0.95rem;
        opacity: 0.92;
        font-weight: 600;
    }
    .seat-banner-main {
        font-size: 2.3rem;
        font-weight: 900;
        margin: 0.4rem 0;
        letter-spacing: 1px;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
    }
    .seat-banner-note {
        font-size: 0.88rem;
        opacity: 0.9;
    }

    /* 表彰台カード（結果発表用） */
    .podium-card {
        background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
        border: 2px solid #FCD34D;
        border-radius: 20px;
        padding: 1.4rem;
        text-align: center;
        margin-bottom: 1.2rem;
        box-shadow: 0 6px 12px -2px rgba(245, 158, 11, 0.2);
    }

    /* ランキングカード */
    .rank-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1.1rem;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        background-color: #FFFFFF;
        margin-bottom: 0.55rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .rank-top1 {
        background: linear-gradient(90deg, #FEF08A 0%, #FFFBEB 100%);
        border-color: #FACC15;
        box-shadow: 0 4px 8px rgba(250, 204, 21, 0.2);
    }
    .rank-top2 {
        background: linear-gradient(90deg, #E2E8F0 0%, #F8FAFC 100%);
        border-color: #94A3B8;
    }
    .rank-top3 {
        background: linear-gradient(90deg, #FED7AA 0%, #FFF7ED 100%);
        border-color: #FB923C;
    }
    
    .rank-badge { font-size: 1.25rem; font-weight: 800; width: 2.2rem; text-align: center; }
    .rank-name-box { flex-grow: 1; margin-left: 0.6rem; }
    .rank-name { font-size: 1.05rem; font-weight: 700; color: #0F172A; }
    .rank-meta { font-size: 0.78rem; color: #64748B; margin-top: 2px; }
    .rank-score-box { text-align: right; }
    .rank-points-text { font-size: 1.2rem; font-weight: 800; color: #4F46E5; }
    .rank-score-text { font-size: 0.78rem; color: #64748B; }

    /* タグバッジ */
    .role-badge-admin {
        background-color: #FEF3C7;
        color: #B45309;
        font-size: 0.72rem;
        padding: 2px 7px;
        border-radius: 6px;
        font-weight: 800;
        margin-left: 5px;
        border: 1px solid #FDE68A;
    }
    .role-badge-gen {
        background-color: #F1F5F9;
        color: #475569;
        font-size: 0.72rem;
        padding: 2px 7px;
        border-radius: 6px;
        font-weight: 600;
        margin-left: 5px;
        border: 1px solid #E2E8F0;
    }

    /* フォームコントロールのスタイル */
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border: 1.5px solid #CBD5E1 !important;
        padding: 0.65rem 0.85rem !important;
        font-size: 1rem !important;
        background-color: #FFFFFF !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4F46E5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.18) !important;
    }
    .stSelectbox > div > div {
        border-radius: 12px !important;
        border: 1.5px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
    }
    .stNumberInput > div > div > input {
        border-radius: 12px !important;
        border: 1.5px solid #CBD5E1 !important;
        font-size: 1.3rem !important;
        font-weight: 800 !important;
        text-align: center !important;
        background-color: #FFFFFF !important;
    }

    /* ボタンのスタイル */
    .stButton > button {
        border-radius: 12px !important;
        padding: 0.75rem 1.2rem !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%) !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# ヘッダー & ナビゲーション
# ==============================================================================
def render_header_and_nav():
    current_phase = db.get_setting("current_phase", PHASE_ENTRY)

    # フェーズごとのバッジ装飾クラス
    if "準備" in current_phase:
        badge_class = "phase-badge-seat"
        phase_icon = "🪑"
    elif "結果入力" in current_phase:
        badge_class = "phase-badge-score"
        phase_icon = "🎲"
    elif "結果発表" in current_phase:
        badge_class = "phase-badge-result"
        phase_icon = "🏆"
    else:
        badge_class = "phase-badge-entry"
        phase_icon = "📝"

    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-title">🐼 パンダロイヤル</div>
            <div class="app-subtitle">ダイスゲーム大会マネージャー</div>
            <div class="phase-badge-container {badge_class}">
                <span>{phase_icon}</span>
                <span>進行状況: {current_phase}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 画面上部メニュー（スマホで1行にすっきり収まる短いラベル）
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
        "画面メニュー",
        menu_options,
        index=menu_options.index(st.session_state["current_page"]),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state["current_page"] = selected_menu

    # サイドバー情報
    with st.sidebar:
        st.markdown("### 🐼 大会ステータス")
        st.write(f"現在のフェーズ:\n**{current_phase}**")
        players = db.get_all_players()
        p_count = len(players)
        adm_count = sum(1 for p in players if p["role"] == "admin")
        gn_count = sum(1 for p in players if p["role"] == "general")
        st.progress(min(p_count / 30.0, 1.0))
        st.caption(f"参加登録: {p_count}/30名 (運営: {adm_count}名 / 一般: {gn_count}名)")

    return selected_menu, current_phase


# ==============================================================================
# 1. エントリーフェーズ画面
# ==============================================================================
def render_phase_entry():
    players = db.get_all_players()
    current_count = len(players)

    st.markdown(
        f"""
        <div class="mobile-card" style="text-align: center; background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border-color: #BFDBFE;">
            <div style="font-size: 1.15rem; font-weight: 800; color: #1E40AF;">📝 参加者エントリー受付中</div>
            <div style="font-size: 0.82rem; color: #3B82F6; margin: 0.2rem 0 0.6rem 0;">つなげーとIDとお名前を入力してエントリーしてください</div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.2rem;">
                <span style="font-size: 0.85rem; font-weight: 700; color: #1E3A8A;">現在の参加枠</span>
                <span style="font-size: 1.15rem; font-weight: 900; color: #1D4ED8;">{current_count} <span style="font-size: 0.85rem; font-weight: 600; color: #64748B;">/ 30 名</span></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(current_count / 30.0, 1.0))

    if current_count >= 30:
        st.warning("⚠️ 定員（30名）に達しています。")

    with st.form("phase_entry_form", clear_on_submit=True):
        tsunagate_id = st.text_input("つなげーとID (必須)", placeholder="例: panda_1234")
        player_name = st.text_input("ニックネーム / 表示名 (必須)", placeholder="例: たろう")
        st.caption("※エントリー時は「一般参加者」として登録されます。運営スタッフのタグ付けは管理者ページで行います。")

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

    with st.expander(f"📋 現在のエントリー者一覧 ({current_count}名)", expanded=True):
        if players:
            for idx, p in enumerate(players, 1):
                role_label = '<span class="role-badge-admin">運営</span>' if p["role"] == "admin" else '<span class="role-badge-gen">一般</span>'
                st.markdown(
                    f"""
                    <div style="padding: 0.4rem 0; border-bottom: 1px solid #F1F5F9; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>{idx}. {p['name']}</strong> {role_label}
                            <div style="font-size: 0.75rem; color: #94A3B8;">ID: {p['tsunagate_id']}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("まだエントリーしているプレイヤーはいません。")


# ==============================================================================
# 2. 準備フェーズ画面（席替え表示・座席案内）
# ==============================================================================
def render_phase_seating(round_name: str, phase_title: str):
    st.markdown(f"### 🪑 {phase_title}")
    st.caption("座席の抽選が完了しました！自分のお名前を選択して座席を確認し、移動してください。")

    players = db.get_all_players()
    if not players:
        st.warning("参加者が登録されていません。")
        return

    player_options = {p["name"]: p for p in players}
    player_display_list = ["-- お名前を選択して座席を確認 --"] + list(player_options.keys())
    selected_name = st.selectbox("あなたのお名前", player_display_list)

    if selected_name == "-- お名前を選択して座席を確認 --":
        st.info("👆 上のプルダウンからご自身のお名前を選択してください。")
    else:
        selected_player = player_options[selected_name]
        player_id = selected_player["id"]

        seat_info = db.get_player_seat(round_name, player_id)
        if not seat_info:
            st.error(
                f"⚠️ {round_name} の座席割り当てデータが見つかりません。\n\n"
                f"運営スタッフが座席抽選を行うまで少々お待ちください。"
            )
        else:
            table_name = seat_info["table_name"]
            seat_number = seat_info["seat_number"]

            # 特大座席バナー
            st.markdown(
                f"""
                <div class="seat-banner">
                    <div class="seat-banner-title">📍 {selected_name} さんの割り当て座席</div>
                    <div class="seat-banner-main">{table_name} &nbsp; {seat_number} 番席</div>
                    <div class="seat-banner-note">👉 {table_name}の{seat_number}番の席へご移動ください</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.info("💡 全員の着席と運営の合図をお待ちください。対戦終了後に「結果入力」画面へ切り替わります。")

    # 全座席表の表示
    st.markdown("---")
    st.markdown(f"#### 📋 {round_name} 全座席表")
    seats = db.get_seats_by_round(round_name)
    if not seats:
        st.caption("座席表データはまだありません。")
    else:
        tables: dict = {}
        for s in seats:
            tables.setdefault(s["table_name"], []).append(s)

        selected_tbl_tab = st.radio("卓切り替え", list(tables.keys()), horizontal=True, key=f"seat_tab_{round_name}")
        tbl_players = tables.get(selected_tbl_tab, [])
        tbl_players.sort(key=lambda x: x["seat_number"])

        for p in tbl_players:
            role_badge = '<span class="role-badge-admin">運営</span>' if p["role"] == "admin" else '<span class="role-badge-gen">一般</span>'
            st.markdown(
                f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.6rem 0.9rem; margin-bottom: 0.35rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #4F46E5; font-size: 1.1rem; min-width: 2rem; display: inline-block;">{p['seat_number']}</strong>
                        <span style="font-size: 0.95rem; font-weight: 600; margin-left: 0.3rem;">{p['player_name']}</span>
                    </div>
                    <div>{role_badge}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 予選2や決勝の準備フェーズでは、直前までの総合ランキングも確認できるアコーディオンを表示
    if round_name in ["予選2", "決勝"]:
        st.markdown("---")
        with st.expander("📊 これまでの暫定総合順位を確認する", expanded=False):
            rounds_to_calc = ["予選1"] if round_name == "予選2" else ["予選1", "予選2"]
            all_scs = db.get_all_scores_summary()
            rankings = logic.calculate_overall_ranking(players, all_scs, target_rounds=rounds_to_calc)
            for p in rankings:
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; padding:0.4rem 0; border-bottom:1px solid #F1F5F9;">
                        <div><strong>{p['overall_rank']}位</strong> {p['player_name']}</div>
                        <div><strong style="color:#4F46E5;">{p['total_rank_points']}pt</strong> (計{p['total_score']}点)</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ==============================================================================
# 3. 結果入力フェーズ画面 (スコア報告)
# ==============================================================================
def render_phase_score_input(round_name: str, phase_title: str):
    st.markdown(f"### 🎲 {phase_title}")
    st.caption("ゲーム終了！ご自身のお名前を選択し、ダイスゲームで獲得した素点スコアを送信してください。")

    players = db.get_all_players()
    if not players:
        st.warning("参加者が登録されていません。")
        return

    player_options = {p["name"]: p for p in players}
    player_display_list = ["-- お名前を選択してスコア入力 --"] + list(player_options.keys())
    selected_name = st.selectbox("あなたのお名前", player_display_list)

    if selected_name == "-- お名前を選択してスコア入力 --":
        st.info("👆 上のプルダウンからご自身のお名前を選択してください。")
        return

    selected_player = player_options[selected_name]
    player_id = selected_player["id"]

    seat_info = db.get_player_seat(round_name, player_id)
    if not seat_info:
        st.error(f"⚠️ {round_name} の座席情報がありません。運営にお問い合わせください。")
        return

    table_name = seat_info["table_name"]
    seat_number = seat_info["seat_number"]

    # 座席案内バナー
    st.markdown(
        f"""
        <div class="seat-banner">
            <div class="seat-banner-title">📍 あなたの {round_name} 座席</div>
            <div class="seat-banner-main">{table_name} &nbsp; {seat_number} 番席</div>
            <div class="seat-banner-note">※卓情報は自動確定済みです</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 既存スコア取得
    existing_scores = db.get_scores_by_round(round_name)
    current_sc = None
    for s in existing_scores:
        if s["player_id"] == player_id:
            current_sc = s["score"]
            break

    # スコア送信フォーム
    with st.form("score_input_form"):
        default_val = current_sc if current_sc is not None else 0
        input_score = st.number_input(
            "ゲーム獲得スコア (素点)",
            min_value=0,
            max_value=9999,
            value=int(default_val),
            step=1,
            help="ダイスゲーム終了時に獲得した素点を入力してください",
        )

        if current_sc is not None:
            st.caption(f"ℹ️ 現在の登録済みスコア: {current_sc} 点 (再送信で更新されます)")

        submit_btn = st.form_submit_button("📤 スコアを送信する", use_container_width=True, type="primary")

        if submit_btn:
            db.save_score(round_name, player_id, int(input_score), table_name)
            scs = db.get_scores_by_round(round_name)
            calc = logic.calculate_table_ranks_and_points(scs)
            db.update_rank_points_in_db(round_name, calc)

            st.balloons()
            st.success(f"✅ {round_name} のスコア ({input_score}点) を正常に記録しました！")
            st.rerun()

    # 同卓メンバーの入力状況
    st.markdown("---")
    st.markdown(f"#### 👥 {table_name} の入力状況")
    table_scores = {s["player_id"]: s for s in existing_scores if s["table_name"] == table_name}
    seats_in_round = db.get_seats_by_round(round_name)
    table_seats = [s for s in seats_in_round if s["table_name"] == table_name]
    table_seats.sort(key=lambda x: x["seat_number"])

    st.caption(f"入力進捗: {len(table_scores)} / {len(table_seats)} 名 完了")

    for s_info in table_seats:
        pid = s_info["player_id"]
        p_sc_obj = table_scores.get(pid)
        is_me = (pid == player_id)
        highlight = "border-left: 4px solid #4F46E5; background-color: #EEF2FF;" if is_me else "background-color: #FFFFFF;"

        if p_sc_obj:
            st_str = f"<strong style='color:#4F46E5;'>{p_sc_obj['score']}点</strong> ({p_sc_obj['rank_in_table']}位 / {p_sc_obj['rank_points']}pt)"
        else:
            st_str = "<span style='color:#94A3B8; font-size: 0.85rem;'>未入力</span>"

        st.markdown(
            f"""
            <div style="padding: 0.55rem 0.8rem; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 0.4rem; display: flex; justify-content: space-between; align-items: center; {highlight}">
                <div>
                    <span style="font-size: 0.85rem; color: #64748B;">{s_info['seat_number']}番</span>
                    <strong style="margin-left: 0.3rem;">{s_info['player_name']}</strong>
                    {'<span style="font-size: 0.75rem; color: #4F46E5; margin-left: 4px;">(あなた)</span>' if is_me else ''}
                </div>
                <div>{st_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==============================================================================
# 4. 結果発表（最終スコア表示）フェーズ画面
# ==============================================================================
def render_phase_result():
    st.markdown(
        """
        <div class="podium-card">
            <div style="font-size: 1.8rem;">🎉 大会結果発表・表彰式 🎉</div>
            <div style="font-size: 0.95rem; color: #92400E; margin-top: 0.4rem; font-weight: 600;">
                パンダロイヤル ダイスゲーム大会 全ラウンド終了！
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    players = db.get_all_players()
    all_scores = db.get_all_scores_summary()

    if not players:
        st.info("データがありません。")
        return

    final_scores = db.get_scores_by_round("決勝")

    if final_scores:
        st.markdown("### 👑 チャンピオン卓 最終結果")
        champ_scores = [s for s in final_scores if s["table_name"] == "チャンピオン卓"]
        champ_scores.sort(key=lambda x: x["score"], reverse=True)

        if champ_scores:
            p1 = champ_scores[0]
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #FEF08A, #FDE047); border-radius: 14px; padding: 1.2rem; text-align: center; margin-bottom: 0.8rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 2px solid #FACC15;">
                    <div style="font-size: 1rem; font-weight: bold; color: #854D0E;">🏆 大会 総合優勝 🏆</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #713F12; margin: 0.3rem 0;">{p1['player_name']} 選手</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #854D0E;">決勝スコア: {p1['score']} 点</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if len(champ_scores) > 1:
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    p2 = champ_scores[1]
                    st.markdown(
                        f"""
                        <div style="background: #F1F5F9; border-radius: 12px; padding: 0.8rem; text-align: center; border: 1px solid #CBD5E1;">
                            <div style="font-size: 0.85rem; font-weight: bold; color: #475569;">🥈 準優勝</div>
                            <div style="font-size: 1.2rem; font-weight: 700; color: #1E293B;">{p2['player_name']}</div>
                            <div style="font-size: 0.9rem; color: #64748B;">決勝: {p2['score']}点</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_sub2:
                    if len(champ_scores) > 2:
                        p3 = champ_scores[2]
                        st.markdown(
                            f"""
                            <div style="background: #FFEDD5; border-radius: 12px; padding: 0.8rem; text-align: center; border: 1px solid #FDBA74;">
                                <div style="font-size: 0.85rem; font-weight: bold; color: #9A3412;">🥉 第3位</div>
                                <div style="font-size: 1.2rem; font-weight: 700; color: #1E293B;">{p3['player_name']}</div>
                                <div style="font-size: 0.9rem; color: #64748B;">決勝: {p3['score']}点</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        silver_scores = [s for s in final_scores if s["table_name"] == "シルバー卓"]
        bronze_scores = [s for s in final_scores if s["table_name"] == "ブロンズ卓"]
        silver_scores.sort(key=lambda x: x["score"], reverse=True)
        bronze_scores.sort(key=lambda x: x["score"], reverse=True)

        if silver_scores or bronze_scores:
            st.markdown("#### 🎖️ 各卓の覇者")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                if silver_scores:
                    s_win = silver_scores[0]
                    st.markdown(
                        f"""
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.6rem; text-align: center;">
                            <div style="font-size: 0.8rem; color: #64748B;">🥈 シルバー卓 1位</div>
                            <strong>{s_win['player_name']}</strong> ({s_win['score']}点)
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            with col_t2:
                if bronze_scores:
                    b_win = bronze_scores[0]
                    st.markdown(
                        f"""
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.6rem; text-align: center;">
                            <div style="font-size: 0.8rem; color: #64748B;">🥉 ブロンズ卓 1位</div>
                            <strong>{b_win['player_name']}</strong> ({b_win['score']}点)
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # 総合ランキング（予選1・2・決勝の合計）
    st.markdown("---")
    st.markdown("### 🏅 全ラウンド総合スコア一覧")
    rankings_all = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選1", "予選2", "決勝"])

    for p in rankings_all:
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

        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="rank-badge">{badge_icon}</div>
                <div class="rank-name-box">
                    <div class="rank-name">{p['player_name']} {role_tag}</div>
                    <div class="rank-meta">予1:{p['round_details'].get('予選1',{}).get('score','-')}点 | 予2:{p['round_details'].get('予選2',{}).get('score','-')}点 | 決:{p['round_details'].get('決勝',{}).get('score','-')}点</div>
                </div>
                <div class="rank-score-box">
                    <div class="rank-points-text">{p['total_rank_points']} pt</div>
                    <div class="rank-score-text">計 {p['total_score']} 点</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==============================================================================
# サブ画面: 総合順位 (閲覧用)
# ==============================================================================
def render_ranking_page():
    st.markdown("### 📊 総合順位ランキング")
    players = db.get_all_players()
    if not players:
        st.info("参加者がまだ登録されていません。")
        return

    all_scores = db.get_all_scores_summary()
    target_rounds = st.multiselect(
        "集計対象ラウンド",
        ["予選1", "予選2", "決勝"],
        default=["予選1", "予選2"],
    )

    if not target_rounds:
        st.warning("集計対象のラウンドを選択してください。")
        return

    rankings = logic.calculate_overall_ranking(players, all_scores, target_rounds=target_rounds)

    st.caption("※ 順位ルール: 「順位点合計」優先 ＞ 同点なら「素点合計」優先")

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
            if r_obj:
                detail_texts.append(f"{r_name}: {r_obj['score']}点({r_obj['rank_points']}pt)")
            else:
                detail_texts.append(f"{r_name}: -")
        detail_str = " | ".join(detail_texts)

        if rank == 11 and "予選2" in target_rounds and "決勝" not in target_rounds:
            st.markdown(
                """
                <div style="text-align: center; margin: 0.6rem 0; padding: 0.2rem; background-color: #FEF3C7; color: #92400E; border-radius: 6px; font-size: 0.75rem; font-weight: bold;">
                    ▲ 上位10名: チャンピオン卓進出ライン ▲
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="rank-badge">{badge_icon}</div>
                <div class="rank-name-box">
                    <div class="rank-name">{p['player_name']} {role_tag}</div>
                    <div class="rank-meta">{detail_str}</div>
                </div>
                <div class="rank-score-box">
                    <div class="rank-points-text">{p['total_rank_points']} pt</div>
                    <div class="rank-score-text">計 {p['total_score']} 点</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==============================================================================
# サブ画面: 座席表一覧 (閲覧用)
# ==============================================================================
def render_seats_page():
    st.markdown("### 🪑 座席表一覧")
    round_selected = st.radio("表示ラウンド", ["予選1", "予選2", "決勝"], horizontal=True)

    seats = db.get_seats_by_round(round_selected)
    if not seats:
        st.info(f"{round_selected} の座席割り当てはまだ完了していません。")
        return

    tables: dict = {}
    for s in seats:
        tables.setdefault(s["table_name"], []).append(s)

    table_names = list(tables.keys())
    selected_tbl = st.radio("表示卓", table_names, horizontal=True)

    p_list = tables.get(selected_tbl, [])
    p_list.sort(key=lambda x: x["seat_number"])

    st.markdown(
        f"""
        <div style="background-color: #F8FAFC; border-radius: 10px; padding: 0.8rem; margin: 0.5rem 0 1rem 0; border: 1px solid #E2E8F0; text-align: center;">
            <div style="font-size: 1.1rem; font-weight: 700; color: #1E293B;">🎲 {selected_tbl} 座席一覧</div>
            <div style="font-size: 0.8rem; color: #64748B;">定員: {len(p_list)}名</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for p in p_list:
        role_badge = '<span class="role-badge-admin">運営</span>' if p["role"] == "admin" else '<span class="role-badge-gen">一般</span>'
        st.markdown(
            f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.65rem 0.9rem; margin-bottom: 0.4rem; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #4F46E5; font-size: 1.1rem; min-width: 2rem; display: inline-block;">{p['seat_number']}</strong>
                    <span style="font-size: 0.95rem; font-weight: 600; margin-left: 0.3rem;">{p['player_name']}</span>
                </div>
                <div>{role_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==============================================================================
# サブ画面: 参加用QRコード (プロジェクター投影・スマホ読み取り用)
# ==============================================================================
def render_qr_page():
    st.markdown("### 📱 参加用QRコード")
    st.caption("スマホのカメラでこのQRコードを読み取って大会にご参加ください！")

    access_url = get_current_access_url()
    qr_bytes = generate_qr_code_image(access_url)

    # プロジェクター投影向け大型カード
    st.markdown(
        f"""
        <div style="background-color: #FFFFFF; border-radius: 20px; border: 2px solid #E2E8F0; padding: 1.5rem 1rem; text-align: center; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); margin-bottom: 1.2rem;">
            <div style="font-size: 1.3rem; font-weight: 800; color: #1E293B; margin-bottom: 0.5rem;">
                🐼 パンダロイヤル 大会アクセス
            </div>
            <div style="display: flex; justify-content: center; margin: 1rem 0;">
                <img src="data:image/png;base64,{pd.Series(qr_bytes).apply(lambda x: __import__('base64').b64encode(x).decode()).iloc[0]}" style="width: 260px; height: 260px; border-radius: 12px; border: 1px solid #E2E8F0;" />
            </div>
            <div style="background-color: #F8FAFC; border-radius: 8px; padding: 0.6rem; font-family: monospace; font-size: 0.9rem; color: #3B82F6; word-break: break-all; margin: 0.8rem 0;">
                {access_url}
            </div>
            <div style="font-size: 0.85rem; color: #64748B;">
                📷 スマートフォンの標準カメラアプリで読み取れます
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ダウンロードボタン
    st.download_button(
        "📥 QRコード画像をダウンロード (印刷・LINE配布用)",
        data=qr_bytes,
        file_name="panda_royal_qr.png",
        mime="image/png",
        use_container_width=True,
        type="primary",
    )

    st.markdown("---")
    with st.expander("ℹ️ 接続に関するヒント"):
        st.markdown(
            """
            - **同じWi-Fi（またはテザリング）に接続している場合**:
              パソコンとスマホが同じWi-Fiに繋がっていれば、上記QRコードからそのままアクセスできます。
            - **参加者が自分のモバイル通信（4G/5G）で繋ぐ場合**:
              Cloudflare Tunnel などの無料トンネリングツールを利用して発行された公開URL（https://...）を「管理者ページ」で設定すると、どの回線からでもQRコードでアクセスできます。
            """
        )


# ==============================================================================
# 画面4: 管理者ページ (8フェーズ設定コントロール搭載)
# ==============================================================================
def render_admin_page():
    st.markdown("### ⚙️ 管理者ページ")

    # パスワード認証
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        with st.form("admin_auth_form"):
            pw_input = st.text_input("管理者パスワード", type="password", placeholder="パスワードを入力")
            if st.form_submit_button("🔓 ログイン", use_container_width=True, type="primary"):
                if pw_input == DEFAULT_ADMIN_PASSWORD:
                    st.session_state["admin_logged_in"] = True
                    st.success("ログイン成功！")
                    st.rerun()
                else:
                    st.error("パスワードが正しくありません。")
        return

    # 認証後ヘッダー
    c_auth, c_out = st.columns([3, 1])
    c_auth.success("🔓 管理者認証中")
    if c_out.button("ログアウト", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()

    # ==========================================
    # ★ 最重要: 大会進行フェーズ設定（8ステップ）
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🚩 大会進行フェーズ設定")
    st.caption("選択したフェーズに合わせて、参加者のトップ画面（大会ホーム）の表示が自動的に連動します。")

    current_phase = db.get_setting("current_phase", PHASE_ENTRY)
    curr_idx = ALL_PHASES.index(current_phase) if current_phase in ALL_PHASES else 0

    # フェーズのワンクリック進める/戻すボタン
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
            if st.button(f"進める ➔: {next_phase}", use_container_width=True, type="primary"):
                db.set_setting("current_phase", next_phase)
                st.rerun()

    selected_new_phase = st.selectbox(
        "フェーズを直接選択して変更",
        ALL_PHASES,
        index=curr_idx,
        key="admin_phase_selector_box",
    )

    if selected_new_phase != current_phase:
        db.set_setting("current_phase", selected_new_phase)
        st.success(f"フェーズを「{selected_new_phase}」に変更しました！参加者トップ画面が自動更新されます。")
        st.rerun()

    st.markdown("---")

    players = db.get_all_players()
    total_count = len(players)
    admin_count = sum(1 for p in players if p["role"] == "admin")
    gen_count = sum(1 for p in players if p["role"] == "general")

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("総数", f"{total_count}名")
    col_m2.metric("運営", f"{admin_count}名")
    col_m3.metric("一般", f"{gen_count}名")

    admin_tabs = st.tabs([
        "👥 タグ付け",
        "🎯 座席抽選",
        "📊 入力進捗",
        "📱 QR・URL設定",
        "🛠️ テスト/初期化",
    ])

    # タブ1: 属性タグ付け
    with admin_tabs[0]:
        st.markdown("##### 👥 参加者タグ付け (運営 / 一般)")
        if not players:
            st.info("参加者がまだいません。")
        else:
            for p in players:
                is_admin = (p["role"] == "admin")
                col_p_info, col_p_btn = st.columns([3, 2])
                with col_p_info:
                    tag_html = '<span class="role-badge-admin">運営</span>' if is_admin else '<span class="role-badge-gen">一般</span>'
                    st.markdown(
                        f"**{p['name']}** {tag_html}<div style='font-size:0.75rem;color:#94A3B8;'>ID: {p['tsunagate_id']}</div>",
                        unsafe_allow_html=True,
                    )
                with col_p_btn:
                    btn_label = "一般に戻す" if is_admin else "運営にする"
                    next_role = "general" if is_admin else "admin"
                    if st.button(btn_label, key=f"role_btn_{p['id']}", use_container_width=True):
                        db.update_player_role(p["id"], next_role)
                        st.rerun()

        st.markdown("---")
        with st.expander("➕ 手動エントリー (代理登録)"):
            with st.form("manual_add_form", clear_on_submit=True):
                m_tid = st.text_input("つなげーとID")
                m_name = st.text_input("お名前")
                m_role = st.selectbox("属性", ["一般", "運営"])
                if st.form_submit_button("登録する", use_container_width=True):
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
        st.markdown("##### 🎯 座席自動抽選")
        if len(players) < 3:
            st.warning("参加者が3名未満です。")
        else:
            with st.expander("🎲 予選1 座席抽選", expanded=True):
                st.caption("運営を均等に配分し、一般をシャッフル配分します。")
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

            with st.expander("🏆 決勝ラウンド座席抽選 (足切り付き)", expanded=True):
                st.caption("予選1・2の総合結果からチャンピオン卓・シルバー卓・ブロンズ卓を決定し、運営足切りを実行します。")
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
                        st.markdown("##### 🔄 運営足切り・繰り上げ履歴")
                        for sw in swap_history:
                            st.write(
                                f"🔻 運営 {sw['demoted_admin']} (予選{sw['demoted_rank']}位) ➔ 降格\n"
                                f"🔺 一般 {sw['promoted_general']} (予選{sw['promoted_rank']}位) ➔ チャンピオン卓へ昇格！"
                            )
                    st.rerun()

    # タブ3: 入力進捗
    with admin_tabs[2]:
        st.markdown("##### 📊 ラウンド別スコア入力進捗")
        for r_name in ["予選1", "予選2", "決勝"]:
            r_seats = db.get_seats_by_round(r_name)
            r_scores = db.get_scores_by_round(r_name)
            sc_count = len(r_scores)
            st_count = len(r_seats)
            pct = (sc_count / st_count) if st_count > 0 else 0

            st.markdown(f"**{r_name}**: {sc_count} / {st_count} 名 完了 ({int(pct*100)}%)")
            st.progress(pct)

            if st_count > 0 and sc_count < st_count:
                entered_pids = {s["player_id"] for s in r_scores}
                unentered = [s["player_name"] for s in r_seats if s["player_id"] not in entered_pids]
                st.caption(f"未入力: {', '.join(unentered)}")

    # タブ4: 参加用QR・URL設定
    with admin_tabs[3]:
        st.markdown("##### 📱 参加用アクセスURL & QRコード設定")
        st.caption("参加者がスマートフォンからアクセスするためのURLを設定・確認できます。")

        current_url = get_current_access_url()
        custom_saved_url = db.get_setting("custom_access_url", "")

        st.markdown(f"**現在のアクセスURL:** `{current_url}`")
        if custom_saved_url:
            st.success("🌐 外部公開カスタムURLが適用されています。")
        else:
            st.info("📶 ローカルWi-Fi用の内部IPアドレスが適用されています。")

        # QRコードのミニプレビュー
        qr_preview = generate_qr_code_image(current_url)
        st.image(qr_preview, width=180, caption="現在の参加用QRコード")

        st.markdown("---")
        st.markdown("###### 🌐 外部公開URL（Cloudflare Tunnel 等）の手動設定")
        st.caption(
            "会場Wi-Fiに繋がず参加者自身のスマホ回線（4G/5G）からアクセスさせたい場合は、"
            "Cloudflare Tunnel 等で発行された公開URL（例: `https://xxxx.trycloudflare.com`）をここに入力して保存してください。"
        )

        with st.form("custom_url_form"):
            input_custom_url = st.text_input("外部公開URL", value=custom_saved_url, placeholder="https://xxxx.trycloudflare.com")
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                save_url_btn = st.form_submit_button("💾 URLを保存する", use_container_width=True, type="primary")
            with col_u2:
                reset_url_btn = st.form_submit_button("🔄 ローカルIPに戻す", use_container_width=True)

            if save_url_btn:
                db.set_setting("custom_access_url", input_custom_url.strip())
                st.success("アクセスURLを更新しました！QRコードが即時再生成されます。")
                st.rerun()

            if reset_url_btn:
                db.set_setting("custom_access_url", "")
                st.success("ローカルIPアドレスのURLに戻しました。")
                st.rerun()

    # タブ5: バックアップ/初期化
    with admin_tabs[4]:
        st.markdown("##### 💾 データベースのバックアップ & 復元")
        st.caption(
            "Streamlit Community Cloud などのクラウド環境で運用する場合、"
            "定期的にバックアップをダウンロードしておくことで、万が一の再起動時にも即座にデータを完全復元できます。"
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            db_bytes = db.get_db_bytes()
            st.download_button(
                label="📥 DBバックアップを保存 (.db)",
                data=db_bytes,
                file_name="panda_royal_backup.db",
                mime="application/octet-stream",
                use_container_width=True,
            )
        with col_b2:
            uploaded_db = st.file_uploader("📤 バックアップから復元", type=["db"], label_visibility="collapsed")
            if uploaded_db is not None:
                if st.button("🔄 このバックアップで復元する", type="primary", use_container_width=True):
                    file_bytes = uploaded_db.read()
                    if db.restore_db_from_bytes(file_bytes):
                        st.success("✅ データベースを復元しました！")
                        st.rerun()
                    else:
                        st.error("❌ データベースの復元に失敗しました。")

        st.markdown("---")
        st.markdown("##### 🧪 リハーサル用ダミーデータ")
        if st.button("👥 30名のダミープレイヤーを一括作成", use_container_width=True):
            admin_names = ["運営A", "運営B", "運営C", "運営D", "運営E"]
            for i, name in enumerate(admin_names, 1):
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
        st.markdown("##### ⚠️ 大会データリセット")
        with st.expander("🚨 全データ削除"):
            confirm_text = st.text_input("確認のため「RESET」と入力")
            if st.button("💥 全データをリセットする", type="primary", use_container_width=True):
                if confirm_text == "RESET":
                    db.reset_all_data()
                    st.success("リセット完了しました。")
                    st.rerun()
                else:
                    st.error("確認テキストが一致しません。")


# ==============================================================================
# メインエントリーポイント
# ==============================================================================
def main():
    selected_menu, current_phase = render_header_and_nav()

    if selected_menu == "🏠 ホーム":
        # 8つのフェーズに合致したコンテンツを表示
        if current_phase == PHASE_ENTRY:
            render_phase_entry()
        elif current_phase == PHASE_PRELIM1_SEAT:
            render_phase_seating("予選1", "予選１　準備（席替え・座席発表）")
        elif current_phase == PHASE_PRELIM1_SCORE:
            render_phase_score_input("予選1", "予選１　結果入力")
        elif current_phase == PHASE_PRELIM2_SEAT:
            render_phase_seating("予選2", "予選２　準備（席替え・座席発表）")
        elif current_phase == PHASE_PRELIM2_SCORE:
            render_phase_score_input("予選2", "予選２　結果入力")
        elif current_phase == PHASE_FINAL_SEAT:
            render_phase_seating("決勝", "決勝戦　準備（進出卓発表・席替え）")
        elif current_phase == PHASE_FINAL_SCORE:
            render_phase_score_input("決勝", "決勝戦　結果入力")
        elif current_phase == PHASE_RESULT:
            render_phase_result()
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

