"""
パンダロイヤル大会マネージャー (app.py)
運営側で設定した大会フェーズ（エントリー ➔ 予選1 ➔ 予選2 ➔ 決勝戦 ➔ 結果発表）に連動して
トップページが自動的に最適化される、スマートフォン完全対応の大会進行Webアプリ
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

# 大会進行フェーズ定義
PHASE_ENTRY = "エントリーフェーズ"
PHASE_PRELIM1 = "予選１"
PHASE_PRELIM2 = "予選２"
PHASE_FINAL = "決勝戦"
PHASE_RESULT = "結果発表"

ALL_PHASES = [
    PHASE_ENTRY,
    PHASE_PRELIM1,
    PHASE_PRELIM2,
    PHASE_FINAL,
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

# モバイルファーストCSSスタイル定義
st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* アプリ共通ヘッダー */
    .app-header {
        text-align: center;
        padding: 0.3rem 0 0.8rem 0;
        margin-bottom: 0.8rem;
    }
    .app-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0F172A;
    }
    
    /* フェーズステータスバナー */
    .phase-badge-container {
        display: inline-block;
        background: linear-gradient(135deg, #10B981, #059669);
        color: white;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-top: 0.3rem;
        box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);
    }
    .phase-badge-entry { background: linear-gradient(135deg, #3B82F6, #1D4ED8); }
    .phase-badge-p1 { background: linear-gradient(135deg, #F59E0B, #D97706); }
    .phase-badge-p2 { background: linear-gradient(135deg, #EC4899, #BE185D); }
    .phase-badge-final { background: linear-gradient(135deg, #8B5CF6, #6D28D9); }
    .phase-badge-result { background: linear-gradient(135deg, #EF4444, #B91C1C); }

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
        margin: 0.8rem 0 1.2rem 0;
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

    /* 表彰台カード（結果発表用） */
    .podium-card {
        background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
        border: 2px solid #FCD34D;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(245, 158, 11, 0.15);
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
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .rank-top1 { background: linear-gradient(90deg, #FEF08A 0%, #FFFBEB 100%); border-color: #FDE047; }
    .rank-top2 { background: linear-gradient(90deg, #F1F5F9 0%, #FFFFFF 100%); border-color: #CBD5E1; }
    .rank-top3 { background: linear-gradient(90deg, #FFEDD5 0%, #FFF7ED 100%); border-color: #FDBA74; }
    
    .rank-badge { font-size: 1.2rem; font-weight: 800; width: 2.2rem; text-align: center; }
    .rank-name-box { flex-grow: 1; margin-left: 0.5rem; }
    .rank-name { font-size: 1rem; font-weight: 700; color: #1E293B; }
    .rank-meta { font-size: 0.75rem; color: #64748B; }
    .rank-score-box { text-align: right; }
    .rank-points-text { font-size: 1.1rem; font-weight: 800; color: #4F46E5; }
    .rank-score-text { font-size: 0.75rem; color: #64748B; }

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
# ヘッダー & ナビゲーション
# ==============================================================================
def render_header_and_nav():
    current_phase = db.get_setting("current_phase", PHASE_ENTRY)

    # フェーズごとのバッジ装飾クラス
    phase_class_map = {
        PHASE_ENTRY: "phase-badge-entry",
        PHASE_PRELIM1: "phase-badge-p1",
        PHASE_PRELIM2: "phase-badge-p2",
        PHASE_FINAL: "phase-badge-final",
        PHASE_RESULT: "phase-badge-result",
    }
    badge_class = phase_class_map.get(current_phase, "phase-badge-entry")

    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-title">🐼 パンダロイヤル 大会マネージャー</div>
            <div class="phase-badge-container {badge_class}">
                現在進行中: {current_phase}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 画面上部メニュー
    menu_options = [
        "🏠 大会ホーム",
        "📊 総合順位",
        "🪑 座席表一覧",
        "⚙️ 管理者ページ",
    ]

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

    # サイドバー情報
    with st.sidebar:
        st.markdown("### 🐼 大会ステータス")
        st.write(f"現在のフェーズ: **{current_phase}**")
        players = db.get_all_players()
        p_count = len(players)
        adm_count = sum(1 for p in players if p["role"] == "admin")
        gn_count = sum(1 for p in players if p["role"] == "general")
        st.progress(min(p_count / 30.0, 1.0))
        st.caption(f"参加登録: {p_count}/30名 (運営: {adm_count}名 / 一般: {gn_count}名)")

    return selected_menu, current_phase


# ==============================================================================
# ホーム画面: 各フェーズごとのコンテンツ
# ==============================================================================

# -------------------------------------------------------------
# 1. エントリーフェーズのトップ表示
# -------------------------------------------------------------
def render_phase_entry():
    st.markdown("### 📝 参加者エントリー受付中")
    st.caption("つなげーとIDとお名前を入力してエントリーしてください。")

    players = db.get_all_players()
    current_count = len(players)

    st.progress(min(current_count / 30.0, 1.0))
    st.caption(f"現在のエントリー状況: {current_count} / 30 名")

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


# -------------------------------------------------------------
# 2. 予選・決勝 ラウンド中のトップ表示 (スコア入力 & 座席確認)
# -------------------------------------------------------------
def render_phase_round(round_name: str):
    st.markdown(f"### 🎲 {round_name} 進行中！")
    st.caption(f"{round_name}の座席を確認し、ゲーム終了後に獲得スコアを送信してください。")

    players = db.get_all_players()
    if not players:
        st.warning("参加者がまだ登録されていません。")
        return

    # プレイヤー選択
    player_options = {p["name"]: p for p in players}
    player_display_list = ["-- お名前を選択してください --"] + list(player_options.keys())
    selected_name = st.selectbox("あなたのお名前", player_display_list)

    if selected_name == "-- お名前を選択してください --":
        st.info("👆 上のプルダウンからご自身のお名前を選択すると、あなたの座席が表示されます。")
    else:
        selected_player = player_options[selected_name]
        player_id = selected_player["id"]

        seat_info = db.get_player_seat(round_name, player_id)
        if not seat_info:
            st.warning(f"⚠️ {round_name} の座席割り当てがまだ完了していません。運営スタッフの抽選をお待ちください。")
        else:
            table_name = seat_info["table_name"]
            seat_number = seat_info["seat_number"]

            # 特大座席バナー
            st.markdown(
                f"""
                <div class="seat-banner">
                    <div class="seat-banner-title">📍 あなたの {round_name} 割り当て座席</div>
                    <div class="seat-banner-main">{table_name} &nbsp; {seat_number} 番席</div>
                    <div class="seat-banner-note">※卓情報はシステムが保持しているため入力不要です</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 既存スコア
            existing_scores = db.get_scores_by_round(round_name)
            current_sc = None
            for s in existing_scores:
                if s["player_id"] == player_id:
                    current_sc = s["score"]
                    break

            with st.form("round_score_form"):
                default_val = current_sc if current_sc is not None else 0
                input_score = st.number_input(
                    f"{round_name} 獲得スコア (素点)",
                    min_value=0,
                    max_value=9999,
                    value=int(default_val),
                    step=1,
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

    # 該当ラウンドの座席表へのクイックリンク
    st.markdown("---")
    with st.expander(f"🪑 {round_name} 全座席表を確認する", expanded=False):
        seats = db.get_seats_by_round(round_name)
        if not seats:
            st.info("座席がまだ割り当てられていません。")
        else:
            tbl_dict: dict = {}
            for s in seats:
                tbl_dict.setdefault(s["table_name"], []).append(s)
            for t_name, s_list in tbl_dict.items():
                st.markdown(f"**🎲 {t_name}** ({len(s_list)}名)")
                s_list.sort(key=lambda x: x["seat_number"])
                for sp in s_list:
                    tag = '<span class="role-badge-admin">運営</span>' if sp["role"] == "admin" else ""
                    st.caption(f"{sp['seat_number']}番: {sp['player_name']} {tag}")


# -------------------------------------------------------------
# 3. 結果発表（最終スコア）フェーズのトップ表示
# -------------------------------------------------------------
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

    # 決勝ラウンドのスコア確認
    final_scores = db.get_scores_by_round("決勝")

    if final_scores:
        st.markdown("### 👑 チャンピオン卓 最終結果")
        champ_scores = [s for s in final_scores if s["table_name"] == "チャンピオン卓"]
        champ_scores.sort(key=lambda x: x["score"], reverse=True)

        if champ_scores:
            # 優勝
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

            # 2位・3位
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

        # シルバー卓覇者 & ブロンズ卓覇者
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

        # 予選集計時の決勝ボーダー表示
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
# 画面4: 管理者ページ (フェーズ設定コントロール搭載)
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
    # ★ 最重要: 大会フェーズ設定コントロール
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🚩 大会進行フェーズ設定")
    st.caption("ここで選択したフェーズに合わせて、参加者のトップ画面が自動的に切り替わります。")

    current_phase = db.get_setting("current_phase", PHASE_ENTRY)

    selected_new_phase = st.radio(
        "現在のフェーズを選択",
        ALL_PHASES,
        index=ALL_PHASES.index(current_phase) if current_phase in ALL_PHASES else 0,
        horizontal=True,
        key="admin_phase_selector",
    )

    if selected_new_phase != current_phase:
        db.set_setting("current_phase", selected_new_phase)
        # ラウンド設定も同期
        if selected_new_phase in ["予選１", "予選２", "決勝戦"]:
            r_name_map = {"予選１": "予選1", "予選２": "予選2", "決勝戦": "決勝"}
            db.set_setting("current_round", r_name_map[selected_new_phase])
        st.success(f"大会フェーズを「{selected_new_phase}」に変更しました！参加者トップ画面が自動更新されます。")
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
                if st.button("🚀 予選1の座席を抽選する", type="primary", use_container_width=True, key="adm_p1_btn"):
                    assignments = logic.assign_preliminary_seats(players, table_names=["A卓", "B卓", "C卓"])
                    db.save_seats("予選1", assignments)
                    st.success("予選1の座席を割り当てました！")
                    st.rerun()

            with st.expander("🎲 予選2 座席抽選", expanded=False):
                if st.button("🚀 予選2の座席を抽選する", type="primary", use_container_width=True, key="adm_p2_btn"):
                    assignments = logic.assign_preliminary_seats(players, table_names=["A卓", "B卓", "C卓"])
                    db.save_seats("予選2", assignments)
                    st.success("予選2の座席を割り当てました！")
                    st.rerun()

            with st.expander("🏆 決勝ラウンド座席抽選 (足切り付き)", expanded=True):
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

    # タブ4: リハーサル/初期化
    with admin_tabs[3]:
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

    if selected_menu == "🏠 大会ホーム":
        # 現在設定されているフェーズに合致したコンテンツを表示
        if current_phase == PHASE_ENTRY:
            render_phase_entry()
        elif current_phase == PHASE_PRELIM1:
            render_phase_round("予選1")
        elif current_phase == PHASE_PRELIM2:
            render_phase_round("予選2")
        elif current_phase == PHASE_FINAL:
            render_phase_round("決勝")
        elif current_phase == PHASE_RESULT:
            render_phase_result()
    elif selected_menu == "📊 総合順位":
        render_ranking_page()
    elif selected_menu == "🪑 座席表一覧":
        render_seats_page()
    elif selected_menu == "⚙️ 管理者ページ":
        render_admin_page()


if __name__ == "__main__":
    main()
