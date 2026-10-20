"""
パンダロイヤル大会マネージャー (app.py)
スマートフォン利用を前提にUI/UXを完全再設計したボードゲーム大会進行Webアプリ
"""

import os
import random
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import database as db
import tournament_logic as logic

# 環境変数の読み込み
load_dotenv()
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "panda2026")

# ページ基本設定（スマホ画面に最適化）
st.set_page_config(
    page_title="パンダロイヤル",
    page_icon="🐼",
    layout="centered",  # スマホの縦長画面に自然にフィット
    initial_sidebar_state="collapsed",  # スマホ閲覧時に画面を広く使えるよう初期は閉じる
)

# データベース初期化
db.init_db()

# モバイルファーストCSSスタイル定義
st.markdown(
    """
    <style>
    /* 全体フォント・サイズ調整 */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* モバイル向けヘッダー */
    .app-header {
        text-align: center;
        padding: 0.5rem 0 1rem 0;
        border-bottom: 2px solid #F1F5F9;
        margin-bottom: 1rem;
    }
    .app-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.5px;
    }
    .app-subtitle {
        font-size: 0.85rem;
        color: #64748B;
        margin-top: 0.2rem;
    }

    /* スマホで見やすいカードUI */
    .mobile-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        margin-bottom: 0.9rem;
    }
    
    /* 座席お知らせビッグバナー */
    .seat-banner {
        background: linear-gradient(135deg, #4338CA 0%, #3B82F6 100%);
        color: #FFFFFF;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        margin: 1rem 0 1.5rem 0;
        box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
    }
    .seat-banner-title {
        font-size: 0.85rem;
        opacity: 0.9;
        font-weight: 500;
    }
    .seat-banner-main {
        font-size: 2rem;
        font-weight: 800;
        margin: 0.3rem 0;
        letter-spacing: 0.5px;
    }
    .seat-banner-note {
        font-size: 0.8rem;
        opacity: 0.85;
    }

    /* ランキングカード */
    .rank-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1rem;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        background-color: #FFFFFF;
        margin-bottom: 0.6rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .rank-top1 {
        background: linear-gradient(90deg, #FEF08A 0%, #FFFBEB 100%);
        border-color: #FDE047;
    }
    .rank-top2 {
        background: linear-gradient(90deg, #F1F5F9 0%, #FFFFFF 100%);
        border-color: #CBD5E1;
    }
    .rank-top3 {
        background: linear-gradient(90deg, #FFEDD5 0%, #FFF7ED 100%);
        border-color: #FDBA74;
    }
    .rank-badge {
        font-size: 1.2rem;
        font-weight: 800;
        width: 2.2rem;
        text-align: center;
    }
    .rank-name-box {
        flex-grow: 1;
        margin-left: 0.5rem;
    }
    .rank-name {
        font-size: 1rem;
        font-weight: 700;
        color: #1E293B;
    }
    .rank-meta {
        font-size: 0.75rem;
        color: #64748B;
    }
    .rank-score-box {
        text-align: right;
    }
    .rank-points-text {
        font-size: 1.1rem;
        font-weight: 800;
        color: #4F46E5;
    }
    .rank-score-text {
        font-size: 0.75rem;
        color: #64748B;
    }

    /* タグバッジ */
    .role-badge-admin {
        background-color: #FEF3C7;
        color: #B45309;
        font-size: 0.7rem;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
        margin-left: 4px;
    }
    .role-badge-gen {
        background-color: #F1F5F9;
        color: #475569;
        font-size: 0.7rem;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: 4px;
    }

    /* ボタン・入力要素のタップ領域拡大 */
    .stButton>button {
        border-radius: 12px;
        padding: 0.65rem 1rem;
        font-weight: 700;
        font-size: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# ナビゲーションバー（スマホの最上部でワンタップ切り替え）
# ==============================================================================
def render_mobile_navigation() -> str:
    # ヘッダー表示
    st.markdown(
        """
        <div class="app-header">
            <div class="app-title">🐼 パンダロイヤル 大会マネージャー</div>
            <div class="app-subtitle">ダイスゲーム大会 進行・スコア集計システム</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 画面上部のワンタップ・セレクター
    menu_options = [
        "📝 エントリー",
        "🎲 スコア入力",
        "📊 順位・座席表",
        "⚙️ 管理者ページ",
    ]

    # セッションステートで画面を保持
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = menu_options[0]

    selected_menu = st.radio(
        "画面メニュー",
        menu_options,
        index=menu_options.index(st.session_state["current_page"])
        if st.session_state["current_page"] in menu_options
        else 0,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.session_state["current_page"] = selected_menu

    # サイドバー（PC閲覧用・補足情報）
    with st.sidebar:
        st.markdown("### 🐼 大会ステータス")
        players = db.get_all_players()
        p_count = len(players)
        adm_count = sum(1 for p in players if p["role"] == "admin")
        gn_count = sum(1 for p in players if p["role"] == "general")
        st.progress(min(p_count / 30.0, 1.0))
        st.caption(f"参加登録: {p_count}/30名 (運営: {adm_count}名 / 一般: {gn_count}名)")
        st.markdown("---")
        st.caption("※スマートフォンでのご利用を想定し、縦スクロールに最適化しています。")

    return selected_menu


# ==============================================================================
# 画面1: エントリー画面 (スマホ最適化)
# ==============================================================================
def render_entry_page():
    st.markdown("### 📝 参加者エントリー")
    st.caption("つなげーとIDとお名前を入力してエントリーしてください。")

    players = db.get_all_players()
    current_count = len(players)

    # 進行状況バー
    st.progress(min(current_count / 30.0, 1.0))
    st.caption(f"現在のエントリー状況: {current_count} / 30 名")

    if current_count >= 30:
        st.warning("⚠️ 定員（30名）に達しています。")

    # 入力フォーム（スマホで押しやすい大きなカード）
    with st.form("mobile_entry_form", clear_on_submit=True):
        tsunagate_id = st.text_input(
            "つなげーとID (必須)",
            placeholder="例: panda_1234",
            help="つなげーと上でのIDまたは登録名",
        )

        player_name = st.text_input(
            "ニックネーム / 表示名 (必須)",
            placeholder="例: たろう",
            help="大会座席表や順位表に表示されるお名前です",
        )

        st.caption("※エントリー時は自動的に「一般参加者」として登録されます。運営メンバーのタグ付けは管理者ページで行います。")

        submitted = st.form_submit_button("✅ 大会にエントリーする", use_container_width=True, type="primary")

        if submitted:
            if not tsunagate_id.strip():
                st.error("つなげーとIDを入力してください。")
                return
            if not player_name.strip():
                st.error("ニックネームを入力してください。")
                return

            success, message = db.add_player(tsunagate_id, player_name, "general")
            if success:
                st.balloons()
                st.success(f"🎉 {player_name} さんのエントリーが完了しました！")
                st.rerun()
            else:
                st.error(f"❌ {message}")

    # 現在の登録者一覧（アコーディオンでスッキリ）
    with st.expander(f"📋 現在のエントリー一覧を見る ({current_count}名)", expanded=False):
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
# 画面2: スコア入力画面 (スマホ最適化)
# ==============================================================================
def render_score_page():
    st.markdown("### 🎲 スコア入力")
    st.caption("ラウンド終了後、獲得した素点スコアを送信してください。")

    players = db.get_all_players()
    if not players:
        st.warning("参加者がまだ登録されていません。先にエントリーを行ってください。")
        return

    # ラウンド選択（スマホで押しやすいラジオボタン）
    round_options = ["予選1", "予選2", "決勝"]
    default_round = db.get_setting("current_round", "予選1")
    selected_round = st.radio(
        "対象ラウンド",
        round_options,
        index=round_options.index(default_round) if default_round in round_options else 0,
        horizontal=True,
    )

    # プレイヤー選択（スマホでタップしやすいプルダウン）
    player_options = {p["name"]: p for p in players}
    player_display_list = ["-- お名前を選択してください --"] + list(player_options.keys())
    
    selected_name = st.selectbox("あなたのお名前", player_display_list)

    if selected_name == "-- お名前を選択してください --":
        st.info("👆 上のプルダウンからご自身のお名前を選択してください。")
        return

    selected_player = player_options[selected_name]
    player_id = selected_player["id"]

    # 座席情報の取得
    seat_info = db.get_player_seat(selected_round, player_id)

    if not seat_info:
        st.error(
            f"⚠️ {selected_round} の座席割り当てがまだ完了していません。\n\n"
            f"運営スタッフが座席抽選を行うまで少々お待ちください。"
        )
        return

    table_name = seat_info["table_name"]
    seat_number = seat_info["seat_number"]

    # スマホ画面にドカンと大きく表示される「座席バナー」
    st.markdown(
        f"""
        <div class="seat-banner">
            <div class="seat-banner-title">📍 あなたの {selected_round} 割り当て座席</div>
            <div class="seat-banner-main">{table_name} &nbsp; {seat_number} 番席</div>
            <div class="seat-banner-note">※卓情報はシステムが保持しているため入力不要です</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 既存のスコア確認
    existing_scores = db.get_scores_by_round(selected_round)
    current_registered_score = None
    for s in existing_scores:
        if s["player_id"] == player_id:
            current_registered_score = s["score"]
            break

    # スコア送信フォーム
    with st.form("mobile_score_form"):
        default_val = current_registered_score if current_registered_score is not None else 0
        input_score = st.number_input(
            "獲得スコア (ゲーム終了時の素点)",
            min_value=0,
            max_value=9999,
            value=int(default_val),
            step=1,
            help="ダイスゲーム終了時に獲得した素点を入力してください",
        )

        if current_registered_score is not None:
            st.caption(f"ℹ️ 現在の登録済みスコア: {current_registered_score} 点 (再送信で更新されます)")

        submit_btn = st.form_submit_button(
            "📤 スコアを送信する",
            use_container_width=True,
            type="primary",
        )

        if submit_btn:
            db.save_score(selected_round, player_id, int(input_score), table_name)
            round_all_scores = db.get_scores_by_round(selected_round)
            calculated_scores = logic.calculate_table_ranks_and_points(round_all_scores)
            db.update_rank_points_in_db(selected_round, calculated_scores)

            st.balloons()
            st.success(f"✅ {selected_round} のスコア ({input_score}点) を記録しました！")
            st.rerun()

    # 同卓メンバーの入力状況（カードリスト形式でスマホに最適化）
    st.markdown("---")
    st.markdown(f"#### 👥 {table_name} の入力状況")
    
    table_scores = {s["player_id"]: s for s in existing_scores if s["table_name"] == table_name}
    seats_in_round = db.get_seats_by_round(selected_round)
    table_seats = [s for s in seats_in_round if s["table_name"] == table_name]
    table_seats.sort(key=lambda x: x["seat_number"])

    st.caption(f"入力進捗: {len(table_scores)} / {len(table_seats)} 名 完了")

    for s_info in table_seats:
        pid = s_info["player_id"]
        p_score_obj = table_scores.get(pid)
        is_me = (pid == player_id)
        highlight_style = "border-left: 4px solid #4F46E5; background-color: #EEF2FF;" if is_me else "background-color: #FFFFFF;"

        if p_score_obj:
            score_status = f"<strong style='color:#4F46E5;'>{p_score_obj['score']}点</strong> ({p_score_obj['rank_in_table']}位 / {p_score_obj['rank_points']}pt)"
        else:
            score_status = "<span style='color:#94A3B8; font-size: 0.85rem;'>未入力</span>"

        st.markdown(
            f"""
            <div style="padding: 0.6rem 0.8rem; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 0.4rem; display: flex; justify-content: space-between; align-items: center; {highlight_style}">
                <div>
                    <span style="font-size: 0.85rem; color: #64748B;">{s_info['seat_number']}番席</span>
                    <strong style="margin-left: 0.4rem; font-size: 0.95rem;">{s_info['player_name']}</strong>
                    {'<span style="font-size: 0.75rem; color: #4F46E5; margin-left: 4px;">(あなた)</span>' if is_me else ''}
                </div>
                <div>{score_status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==============================================================================
# 画面3: 順位・座席表ダッシュボード (スマホ最適化)
# ==============================================================================
def render_dashboard_page():
    tab_rank, tab_seat = st.tabs(["🏆 総合ランキング", "🪑 座席表"])

    # ---------------------------------------------------------
    # タブ1: 総合ランキング (スマホで見やすいカードリスト)
    # ---------------------------------------------------------
    with tab_rank:
        players = db.get_all_players()
        if not players:
            st.info("参加者がまだ登録されていません。")
            return

        all_scores = db.get_all_scores_summary()

        col_r1, col_r2 = st.columns([3, 1])
        with col_r1:
            target_rounds = st.multiselect(
                "集計ラウンド",
                ["予選1", "予選2", "決勝"],
                default=["予選1", "予選2"],
                label_visibility="collapsed",
            )
        with col_r2:
            if st.button("🔄 更新", use_container_width=True):
                st.rerun()

        if not target_rounds:
            st.warning("集計対象のラウンドを選択してください。")
            return

        rankings = logic.calculate_overall_ranking(players, all_scores, target_rounds=target_rounds)

        st.caption("※ 順位ルール: 「順位点合計」優先 ＞ 同点なら「素点合計」優先")

        for p in rankings:
            rank = p["overall_rank"]
            
            # 上位スタイリング
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

            # ラウンド別内訳のテキスト
            detail_texts = []
            for r_name in target_rounds:
                r_obj = p["round_details"].get(r_name)
                if r_obj:
                    detail_texts.append(f"{r_name}: {r_obj['score']}点({r_obj['rank_points']}pt)")
                else:
                    detail_texts.append(f"{r_name}: -")
            detail_str = " | ".join(detail_texts)

            # 決勝進出ボーダー表示（10位と11位の間）
            if rank == 11 and "予選2" in target_rounds:
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

    # ---------------------------------------------------------
    # タブ2: 座席表 (スマホ用カード表示)
    # ---------------------------------------------------------
    with tab_seat:
        selected_round_seat = st.radio(
            "ラウンド選択",
            ["予選1", "予選2", "決勝"],
            horizontal=True,
            key="dash_seat_round_radio",
        )

        seats = db.get_seats_by_round(selected_round_seat)
        if not seats:
            st.info(f"💡 {selected_round_seat} の座席割り当てはまだ行われていません。")
            return

        # 卓ごとに分割
        tables: dict = {}
        for s in seats:
            tables.setdefault(s["table_name"], []).append(s)

        # 卓の切り替えタブ
        table_names = list(tables.keys())
        selected_table_tab = st.radio(
            "表示卓",
            table_names,
            horizontal=True,
            key="dash_table_tab_radio",
        )

        current_table_players = tables.get(selected_table_tab, [])
        current_table_players.sort(key=lambda x: x["seat_number"])

        admin_in_tbl = sum(1 for p in current_table_players if p["role"] == "admin")
        gen_in_tbl = sum(1 for p in current_table_players if p["role"] == "general")

        st.markdown(
            f"""
            <div style="background-color: #F8FAFC; border-radius: 10px; padding: 0.8rem; margin: 0.5rem 0 1rem 0; border: 1px solid #E2E8F0; text-align: center;">
                <div style="font-size: 1.1rem; font-weight: 700; color: #1E293B;">🎲 {selected_table_tab} 座席一覧</div>
                <div style="font-size: 0.8rem; color: #64748B;">定員: {len(current_table_players)}名 (運営: {admin_in_tbl}名 / 一般: {gen_in_tbl}名)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for p in current_table_players:
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
# 画面4: 管理者ページ (スマホ最適化)
# ==============================================================================
def render_admin_page():
    st.markdown("### ⚙️ 管理者ページ")
    st.caption("運営スタッフ専用の大会進行・座席抽選・設定管理コンソールです。")

    # セッション認証
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        with st.form("mobile_admin_login"):
            pw_input = st.text_input("管理者パスワード", type="password", placeholder="パスワードを入力")
            login_btn = st.form_submit_button("🔓 ログイン", use_container_width=True, type="primary")

            if login_btn:
                if pw_input == DEFAULT_ADMIN_PASSWORD:
                    st.session_state["admin_logged_in"] = True
                    st.success("ログインしました！")
                    st.rerun()
                else:
                    st.error("パスワードが正しくありません。")
        return

    # ログアウトボタン
    col_auth, col_logout = st.columns([3, 1])
    with col_auth:
        st.success("🔓 管理者認証中")
    with col_logout:
        if st.button("ログアウト", use_container_width=True):
            st.session_state["admin_logged_in"] = False
            st.rerun()

    players = db.get_all_players()
    total_count = len(players)
    admin_count = sum(1 for p in players if p["role"] == "admin")
    gen_count = sum(1 for p in players if p["role"] == "general")

    # サマリー指標
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("総数", f"{total_count}名")
    col_m2.metric("運営", f"{admin_count}名")
    col_m3.metric("一般", f"{gen_count}名")

    admin_tabs = st.tabs([
        "👥 属性タグ付け",
        "🎯 座席抽選",
        "📊 入力進捗",
        "🛠️ テスト/初期化",
    ])

    # ---------------------------------------------------------
    # タブ1: 属性タグ付け（スマホで片手操作できるボタンスタイル）
    # ---------------------------------------------------------
    with admin_tabs[0]:
        st.markdown("#### 👥 参加者タグ付け (運営 / 一般)")
        st.caption("各参加者の属性をタップで切り替えます。予選の卓均等配分や決勝足切りに反映されます。")

        if not players:
            st.info("参加者がまだいません。")
        else:
            for p in players:
                is_admin = (p["role"] == "admin")
                col_p_info, col_p_btn = st.columns([3, 2])
                with col_p_info:
                    tag_html = '<span class="role-badge-admin">運営</span>' if is_admin else '<span class="role-badge-gen">一般</span>'
                    st.markdown(
                        f"""
                        <div style="padding: 0.3rem 0;">
                            <strong>{p['name']}</strong> {tag_html}
                            <div style="font-size: 0.75rem; color: #94A3B8;">ID: {p['tsunagate_id']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_p_btn:
                    btn_label = "一般に戻す" if is_admin else "運営にする"
                    next_role = "general" if is_admin else "admin"
                    if st.button(btn_label, key=f"role_btn_{p['id']}", use_container_width=True):
                        db.update_player_role(p["id"], next_role)
                        st.rerun()

        # 参加者の手動追加・削除
        st.markdown("---")
        with st.expander("➕ 参加者の手動追加 (代理登録)"):
            with st.form("manual_add_player_form", clear_on_submit=True):
                m_tsunagate = st.text_input("つなげーとID", placeholder="tsunagate_001")
                m_name = st.text_input("お名前 / ニックネーム", placeholder="参加者名")
                m_role = st.selectbox("初期属性", ["一般", "運営"])
                m_sub = st.form_submit_button("追加する", use_container_width=True)
                if m_sub:
                    if not m_tsunagate.strip() or not m_name.strip():
                        st.error("IDとお名前は必須です。")
                    else:
                        ok, msg = db.add_player(m_tsunagate, m_name, "admin" if m_role == "運営" else "general")
                        if ok:
                            st.success(f"{m_name} さんを追加しました！")
                            st.rerun()
                        else:
                            st.error(msg)

        with st.expander("🗑️ 参加者の削除"):
            if players:
                del_id = st.selectbox(
                    "削除する参加者",
                    [p["id"] for p in players],
                    format_func=lambda pid: next(f"{p['name']} ({p['role']})" for p in players if p["id"] == pid),
                )
                if st.button("選択した参加者を削除", use_container_width=True, type="secondary"):
                    db.delete_player(del_id)
                    st.warning("参加者を削除しました。")
                    st.rerun()

    # ---------------------------------------------------------
    # タブ2: 座席抽選・大会進行
    # ---------------------------------------------------------
    with admin_tabs[1]:
        st.markdown("#### 🎯 座席自動抽選")

        if len(players) < 3:
            st.warning("⚠️ 参加者が3名未満のため抽選できません。")
        else:
            # 予選1
            with st.expander("🎲 予選1 座席抽選", expanded=True):
                st.caption("運営をA/B/C卓に均等配分し、一般をシャッフル配分します。")
                if st.button("🚀 予選1の座席を抽選する", type="primary", use_container_width=True, key="admin_p1_btn"):
                    assignments = logic.assign_preliminary_seats(players, table_names=["A卓", "B卓", "C卓"])
                    db.save_seats("予選1", assignments)
                    db.set_setting("current_round", "予選1")
                    st.success("🎉 予選1の座席を抽選・保存しました！")
                    st.rerun()

            # 予選2
            with st.expander("🎲 予選2 座席抽選", expanded=False):
                st.caption("同様に運営均等＋一般シャッフル配分します。")
                if st.button("🚀 予選2の座席を抽選する", type="primary", use_container_width=True, key="admin_p2_btn"):
                    assignments = logic.assign_preliminary_seats(players, table_names=["A卓", "B卓", "C卓"])
                    db.save_seats("予選2", assignments)
                    db.set_setting("current_round", "予選2")
                    st.success("🎉 予選2の座席を抽選・保存しました！")
                    st.rerun()

            # 決勝ラウンド
            with st.expander("🏆 決勝ラウンド座席抽選 (足切り付き)", expanded=True):
                st.caption("予選1・2の総合順位からチャンピオン卓、シルバー卓、ブロンズ卓に仮配置し、運営足切り・繰り上げを実行します。")
                
                curr_limit = int(db.get_setting("admin_limit_champion", "3"))
                admin_limit = st.slider(
                    "👑 チャンピオン卓の運営上限人数",
                    min_value=0,
                    max_value=10,
                    value=curr_limit,
                    help="この人数を超える運営はシルバー卓へ降格し、一般参加者が繰り上げ昇格します",
                )
                if admin_limit != curr_limit:
                    db.set_setting("admin_limit_champion", str(admin_limit))

                if st.button("🏆 決勝の座席抽選（足切り実行）", type="primary", use_container_width=True, key="admin_final_btn"):
                    all_scores = db.get_all_scores_summary()
                    overall_rankings = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選1", "予選2"])
                    final_assignments, swap_history = logic.assign_final_seats_with_admin_cutoff(
                        overall_rankings,
                        admin_limit_champion=admin_limit,
                    )
                    db.save_seats("決勝", final_assignments)
                    db.set_setting("current_round", "決勝")
                    st.success("🎉 決勝ラウンドの座席割り当てが完了しました！")

                    if swap_history:
                        st.markdown("##### 🔄 運営足切り・繰り上げ履歴")
                        for sw in swap_history:
                            st.write(
                                f"🔻 運営 {sw['demoted_admin']} (予選{sw['demoted_rank']}位) ➔ 降格\n"
                                f"🔺 一般 {sw['promoted_general']} (予選{sw['promoted_rank']}位) ➔ チャンピオン卓へ繰り上げ！"
                            )
                    else:
                        st.info("※ 運営人数は上限内だったため、足切りは発生しませんでした。")
                    st.rerun()

    # ---------------------------------------------------------
    # タブ3: 入力進捗
    # ---------------------------------------------------------
    with admin_tabs[2]:
        st.markdown("#### 📊 ラウンド別スコア入力進捗")
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

    # ---------------------------------------------------------
    # タブ4: リハーサル / 初期化
    # ---------------------------------------------------------
    with admin_tabs[3]:
        st.markdown("#### 🧪 リハーサル用ダミーデータ")
        if st.button("👥 30名のダミープレイヤーを一括作成", use_container_width=True):
            admin_names = ["運営A", "運営B", "運営C", "運営D", "運営E"]
            for i, name in enumerate(admin_names, 1):
                db.add_player(f"admin_{i:02d}", name, "admin")
            for i in range(1, 26):
                db.add_player(f"user_{i:02d}", f"一般{i:02d}", "general")
            st.success("ダミー30名を登録しました！")
            st.rerun()

        if st.button("🎲 予選1・2のランダムスコアを一括生成", use_container_width=True):
            for r_name in ["予選1", "予選2"]:
                seats = db.get_seats_by_round(r_name)
                if not seats:
                    st.error(f"{r_name} の座席が未抽選です。")
                    continue
                for s in seats:
                    db.save_score(r_name, s["player_id"], random.randint(30, 120), s["table_name"])
                scs = db.get_scores_by_round(r_name)
                calc = logic.calculate_table_ranks_and_points(scs)
                db.update_rank_points_in_db(r_name, calc)
            st.success("予選1・2のスコアを自動生成しました！")
            st.rerun()

        st.markdown("---")
        st.markdown("#### ⚠️ 大会データリセット")
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
    selected_menu = render_mobile_navigation()

    if selected_menu == "📝 エントリー":
        render_entry_page()
    elif selected_menu == "🎲 スコア入力":
        render_score_page()
    elif selected_menu == "📊 順位・座席表":
        render_dashboard_page()
    elif selected_menu == "⚙️ 管理者ページ":
        render_admin_page()


if __name__ == "__main__":
    main()
