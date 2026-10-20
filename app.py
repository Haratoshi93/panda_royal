"""
パンダロイヤル大会マネージャー (app.py)
ボードゲーム大会（最大30人）の進行・スコア集計・自動座席割り当てWebアプリケーション
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

# ページ基本設定
st.set_page_config(
    page_title="パンダロイヤル大会マネージャー",
    page_icon="🐼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# データベース初期化
db.init_db()

# カスタムスタイル
st.markdown(
    """
    <style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .sub-text {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }
    .table-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #E2E8F0;
        margin-bottom: 1.2rem;
    }
    .admin-badge {
        background-color: #FEF3C7;
        color: #92400E;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
    }
    .general-badge {
        background-color: #E0E7FF;
        color: #3730A3;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
    }
    .champion-badge {
        background-color: #FEF08A;
        color: #854D0E;
        font-weight: bold;
    }
    .silver-badge {
        background-color: #E2E8F0;
        color: #334155;
        font-weight: bold;
    }
    .bronze-badge {
        background-color: #FFEDD5;
        color: #9A3412;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# サイドバー & ナビゲーション
# ==============================================================================
def render_sidebar() -> str:
    st.sidebar.markdown("## 🐼 パンダロイヤル")
    st.sidebar.caption("ダイスゲーム大会進行システム (最大30名)")
    
    # 登録状況のミニインジケーター
    players = db.get_all_players()
    player_count = len(players)
    admin_count = sum(1 for p in players if p["role"] == "admin")
    gen_count = sum(1 for p in players if p["role"] == "general")
    
    st.sidebar.progress(min(player_count / 30.0, 1.0))
    st.sidebar.caption(f"現在の参加登録: {player_count}/30名 (運営: {admin_count}名 / 一般: {gen_count}名)")
    
    st.sidebar.markdown("---")
    
    menu = st.sidebar.radio(
        "メニューを選択してください",
        ["📝 エントリー画面", "🎲 スコア入力画面", "📊 ダッシュボード (閲覧専用)", "⚙️ 運営用管理画面"],
        index=0,
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption("💡 参加者はスマホからエントリーとスコア入力を行えます。")
    
    return menu


# ==============================================================================
# 画面1: エントリー画面
# ==============================================================================
def render_entry_page():
    st.markdown('<div class="main-header">📝 参加者エントリー</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-text">大会に参加するプレイヤー情報を登録してください。</div>', unsafe_allow_html=True)

    players = db.get_all_players()
    current_count = len(players)

    if current_count >= 30:
        st.warning("⚠️ 定員（30名）に達しています。追加登録は運営管理画面で空き枠を確認してください。")

    with st.form("entry_form", clear_on_submit=True):
        st.markdown("### プレイヤー情報入力")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            tsunagate_id = st.text_input(
                "つなげーとID (必須)",
                placeholder="例: panda_1234",
                help="つなげーと上でのお名前やIDを入力してください",
            )
        with col2:
            player_name = st.text_input(
                "ニックネーム / 表示名 (必須)",
                placeholder="例: たろう",
                help="大会座席表や順位表に表示される名前です",
            )

        role_option = st.radio(
            "属性",
            ["一般参加者", "運営スタッフ"],
            horizontal=True,
            help="運営スタッフとして登録する場合は認証パスワードが必要です",
        )

        admin_pw_input = ""
        if role_option == "運営スタッフ":
            admin_pw_input = st.text_input(
                "運営認証パスワード",
                type="password",
                placeholder="運営用パスワードを入力",
                help="運営登録専用のパスワードです",
            )

        submitted = st.form_submit_button("✅ 大会にエントリーする", use_container_width=True)

        if submitted:
            # 入力チェック
            if not tsunagate_id.strip():
                st.error("つなげーとIDを入力してください。")
                return
            if not player_name.strip():
                st.error("ニックネームを入力してください。")
                return

            # 属性とパスワード検証
            actual_role = "general"
            if role_option == "運営スタッフ":
                if admin_pw_input != DEFAULT_ADMIN_PASSWORD:
                    st.error("運営認証パスワードが正しくありません。")
                    return
                actual_role = "admin"

            # DB保存
            success, message = db.add_player(tsunagate_id, player_name, actual_role)
            if success:
                st.success(f"🎉 {player_name} さんのエントリーが完了しました！")
                st.rerun()
            else:
                st.error(f"❌ {message}")

    # 登録済みリスト（確認用）
    st.markdown("---")
    st.markdown(f"### 現在のエントリー一覧 ({current_count}名)")
    if players:
        df_players = pd.DataFrame(players)
        df_players["属性"] = df_players["role"].apply(lambda r: "運営" if r == "admin" else "一般")
        df_players = df_players.rename(columns={
            "id": "番号",
            "tsunagate_id": "つなげーとID",
            "name": "名前",
            "created_at": "登録日時"
        })
        st.dataframe(
            df_players[["番号", "つなげーとID", "名前", "属性"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("まだエントリーしているプレイヤーはいません。一番乗りで登録しましょう！")


# ==============================================================================
# 画面2: スコア入力画面
# ==============================================================================
def render_score_page():
    st.markdown('<div class="main-header">🎲 スコア入力</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-text">ラウンド終了後、自分が獲得したゲームスコアを送信してください。卓情報は自動設定されます。</div>',
        unsafe_allow_html=True,
    )

    players = db.get_all_players()
    if not players:
        st.warning("参加者がまだ登録されていません。先にエントリー画面から登録してください。")
        return

    # ラウンド選択
    round_options = ["予選1", "予選2", "決勝"]
    default_round = db.get_setting("current_round", "予選1")
    selected_round = st.selectbox(
        "対象ラウンド",
        round_options,
        index=round_options.index(default_round) if default_round in round_options else 0,
    )

    # プレイヤー選択（名前リスト）
    player_map = {f"{p['name']} ({'運営' if p['role'] == 'admin' else '一般'})": p for p in players}
    player_display_list = ["-- プレイヤーを選択してください --"] + list(player_map.keys())
    
    selected_player_str = st.selectbox("あなたの名前", player_display_list)

    if selected_player_str == "-- プレイヤーを選択してください --":
        st.info("上のプルダウンからお名前を選択してください。")
        return

    selected_player = player_map[selected_player_str]
    player_id = selected_player["id"]

    # 該当プレイヤーの指定ラウンドの座席情報を取得
    seat_info = db.get_player_seat(selected_round, player_id)

    if not seat_info:
        st.error(
            f"⚠️ {selected_round} の座席割り当てがまだ完了していません。\n"
            f"運営が座席抽選を行うまでしばらくお待ちいただくか、運営スタッフにお問い合わせください。"
        )
        return

    table_name = seat_info["table_name"]
    seat_number = seat_info["seat_number"]

    # 座席情報の表示（自動確定）
    st.success(
        f"📍 あなたの割り当て卓: **{table_name}** | 座席番号: **{seat_number}番**\n\n"
        f"※卓情報はシステムが自動判定しているため、入力不要です。"
    )

    # 既に登録済みのスコアがあるか確認
    existing_scores = db.get_scores_by_round(selected_round)
    current_registered_score = None
    for s in existing_scores:
        if s["player_id"] == player_id:
            current_registered_score = s["score"]
            break

    with st.form("score_submit_form"):
        st.markdown(f"### {selected_round} 獲得スコア入力")
        
        default_val = current_registered_score if current_registered_score is not None else 0
        input_score = st.number_input(
            "ゲーム終了時の獲得スコア (数値)",
            min_value=0,
            max_value=9999,
            value=int(default_val),
            step=1,
            help="ダイスゲーム終了時に獲得した素点を入力してください",
        )

        if current_registered_score is not None:
            st.caption(f"ℹ️ 現在登録済みのスコア: {current_registered_score} 点 (再送信で上書き更新されます)")

        submit_btn = st.form_submit_button("📤 スコアを送信する", use_container_width=True)

        if submit_btn:
            # スコア保存
            db.save_score(selected_round, player_id, int(input_score), table_name)
            
            # 当該ラウンドの全スコアを取得し、卓内順位と順位点を再計算してDB反映
            round_all_scores = db.get_scores_by_round(selected_round)
            calculated_scores = logic.calculate_table_ranks_and_points(round_all_scores)
            db.update_rank_points_in_db(selected_round, calculated_scores)

            st.balloons()
            st.success(f"✅ {selected_round} のスコア ({input_score}点) を正常に記録しました！")
            st.rerun()

    # 該当卓のスコア入力進捗
    st.markdown("---")
    st.markdown(f"### 📋 {table_name} のスコア入力状況")
    table_scores = [s for s in existing_scores if s["table_name"] == table_name]
    
    # 当該卓の割り当て全プレイヤー
    seats_in_round = db.get_seats_by_round(selected_round)
    table_seats = [s for s in seats_in_round if s["table_name"] == table_name]
    
    progress_count = len(table_scores)
    total_table_seats = len(table_seats)
    st.caption(f"進捗: {progress_count}/{total_table_seats} 名 入力完了")

    if table_scores:
        df_table = pd.DataFrame(table_scores)
        df_table = df_table.rename(columns={
            "player_name": "名前",
            "score": "獲得スコア",
            "rank_in_table": "卓内暫定順位",
            "rank_points": "獲得順位点",
        })
        st.dataframe(
            df_table[["名前", "獲得スコア", "卓内暫定順位", "獲得順位点"]],
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# 画面3: ダッシュボード画面（閲覧専用）
# ==============================================================================
def render_dashboard_page():
    st.markdown('<div class="main-header">📊 大会ダッシュボード</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-text">リアルタイムの総合順位ランキングおよび各ラウンドの座席表を閲覧できます。</div>',
        unsafe_allow_html=True,
    )

    tab_ranking, tab_seats = st.tabs(["🏆 総合ランキング", "🪑 座席表"])

    # ---------------------------------------------------------
    # タブ1: 総合ランキング
    # ---------------------------------------------------------
    with tab_ranking:
        players = db.get_all_players()
        if not players:
            st.info("参加者がまだ登録されていません。")
        else:
            all_scores = db.get_all_scores_summary()
            
            col_filter1, col_filter2 = st.columns([2, 1])
            with col_filter1:
                calc_rounds = st.multiselect(
                    "ランキング集計対象ラウンド",
                    ["予選1", "予選2", "決勝"],
                    default=["予選1", "予選2"],
                    help="予選のみ、または決勝を含めた総合ランキングを切り替えられます",
                )
            with col_filter2:
                if st.button("🔄 最新状況に更新", use_container_width=True):
                    st.rerun()

            if not calc_rounds:
                st.warning("集計対象のラウンドを1つ以上選択してください。")
            else:
                ranking_data = logic.calculate_overall_ranking(players, all_scores, target_rounds=calc_rounds)
                
                # テーブル表示用のデータフレーム構築
                table_rows = []
                for p in ranking_data:
                    role_str = "運営" if p["role"] == "admin" else "一般"
                    row = {
                        "総合順位": f"{p['overall_rank']} 位",
                        "名前": p["player_name"],
                        "属性": role_str,
                        "合計順位点": f"{p['total_rank_points']} pt",
                        "合計スコア": f"{p['total_score']} 点",
                    }
                    # ラウンド別詳細
                    for r_name in ["予選1", "予選2", "決勝"]:
                        if r_name in calc_rounds:
                            r_info = p["round_details"].get(r_name)
                            if r_info:
                                row[f"{r_name} (点/pt)"] = f"{r_info['score']}点 ({r_info['rank_points']}pt)"
                            else:
                                row[f"{r_name} (点/pt)"] = "未記録"
                    table_rows.append(row)

                df_rank = pd.DataFrame(table_rows)

                # 上位入賞者を強調
                st.markdown(f"#### 🏅 総合順位一覧 ({len(df_rank)}名)")
                st.caption("※ 順位ルール: 「順位点の合計」優先 ＞ 同点の場合は「獲得スコアの合計」優先")
                
                st.dataframe(
                    df_rank,
                    use_container_width=True,
                    hide_index=True,
                )

    # ---------------------------------------------------------
    # タブ2: 座席表
    # ---------------------------------------------------------
    with tab_seats:
        round_for_seats = st.radio(
            "表示するラウンドの座席表",
            ["予選1", "予選2", "決勝"],
            horizontal=True,
        )

        seats = db.get_seats_by_round(round_for_seats)
        if not seats:
            st.info(f"💡 {round_for_seats} の座席割り当てはまだ行われていません。運営の抽選をお待ちください。")
        else:
            # 卓ごとに分割
            table_dict: Dict[str, List[Dict[str, Any]]] = {}
            for s in seats:
                table_dict.setdefault(s["table_name"], []).append(s)

            # 卓表示
            col_list = st.columns(len(table_dict))
            for idx, (tbl_name, p_list) in enumerate(table_dict.items()):
                with col_list[idx]:
                    badge_class = "metric-card"
                    if "チャンピオン" in tbl_name:
                        st.markdown(f"### 👑 {tbl_name}")
                    elif "シルバー" in tbl_name:
                        st.markdown(f"### 🥈 {tbl_name}")
                    elif "ブロンズ" in tbl_name:
                        st.markdown(f"### 🥉 {tbl_name}")
                    else:
                        st.markdown(f"### 🎲 {tbl_name}")

                    # 卓内の人数サマリー
                    admin_c = sum(1 for p in p_list if p["role"] == "admin")
                    gen_c = sum(1 for p in p_list if p["role"] == "general")
                    st.caption(f"定員: {len(p_list)}名 (運営: {admin_c}名 / 一般: {gen_c}名)")

                    # 座席番号順に表示
                    p_list.sort(key=lambda x: x["seat_number"])
                    df_seat_table = pd.DataFrame([
                        {
                            "席番": f"{p['seat_number']} 番",
                            "名前": p["player_name"],
                            "属性": "運営" if p["role"] == "admin" else "一般",
                        }
                        for p in p_list
                    ])
                    st.dataframe(df_seat_table, use_container_width=True, hide_index=True)


# ==============================================================================
# 画面4: 運営用管理画面
# ==============================================================================
def render_admin_page():
    st.markdown('<div class="main-header">⚙️ 運営用管理コンソール</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-text">大会の進行管理、座席の自動抽選、足切り設定、スコア進捗を管理します。</div>', unsafe_allow_html=True)

    # 運営ログイン認証（セッション管理）
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        with st.form("admin_login_form"):
            st.markdown("### 🔒 運営パスワード認証")
            pw_input = st.text_input("パスワード", type="password", placeholder="運営パスワードを入力")
            login_btn = st.form_submit_button("ログイン", use_container_width=True)

            if login_btn:
                if pw_input == DEFAULT_ADMIN_PASSWORD:
                    st.session_state["admin_logged_in"] = True
                    st.success("ログインしました！")
                    st.rerun()
                else:
                    st.error("パスワードが正しくありません。")
        return

    # ログアウトボタン
    top_col1, top_col2 = st.columns([4, 1])
    with top_col2:
        if st.button("🚪 ログアウト", use_container_width=True):
            st.session_state["admin_logged_in"] = False
            st.rerun()

    # タブ分け
    admin_tab1, admin_tab2, admin_tab3 = st.tabs([
        "🎯 座席抽選・大会進行",
        "👥 参加者・進捗管理",
        "🛠️ データ管理・テスト機能",
    ])

    # ---------------------------------------------------------
    # 運営タブ1: 座席抽選・大会進行
    # ---------------------------------------------------------
    with admin_tab1:
        st.markdown("### 🎲 各ラウンドの座席自動割り当て")
        
        players = db.get_all_players()
        if len(players) < 3:
            st.warning("⚠️ 参加者が3名未満のため、座席割り当てを実行できません。まずはエントリーを行ってください。")
        else:
            # 1. 予選1
            with st.expander("【アクション1】予選1の座席割り当て", expanded=True):
                st.markdown(
                    "運営メンバーをA/B/C卓に均等（各卓1〜2名）に振り分け、残りの枠に一般メンバーをシャッフル配分します。"
                )
                existing_p1_seats = db.get_seats_by_round("予選1")
                if existing_p1_seats:
                    st.info(f"ℹ️ 予選1は既に割り当て済みです（{len(existing_p1_seats)}名割り当て中）。再実行すると上書きされます。")
                
                if st.button("🚀 予選1の座席割り当てを実行する", type="primary", key="btn_assign_p1"):
                    assignments = logic.assign_preliminary_seats(players, table_names=["A卓", "B卓", "C卓"])
                    db.save_seats("予選1", assignments)
                    db.set_setting("current_round", "予選1")
                    st.success("🎉 予選1の座席割り当てが完了しました！")
                    st.rerun()

            # 2. 予選2
            with st.expander("【アクション2】予選2の座席割り当て", expanded=False):
                st.markdown(
                    "予選1と同様に、運営メンバーを均等に振り分け、一般メンバーをシャッフルしてA/B/C卓へ割り当てます。"
                )
                existing_p2_seats = db.get_seats_by_round("予選2")
                if existing_p2_seats:
                    st.info(f"ℹ️ 予選2は既に割り当て済みです（{len(existing_p2_seats)}名割り当て中）。再実行すると上書きされます。")

                if st.button("🚀 予選2の座席割り当てを実行する", type="primary", key="btn_assign_p2"):
                    assignments = logic.assign_preliminary_seats(players, table_names=["A卓", "B卓", "C卓"])
                    db.save_seats("予選2", assignments)
                    db.set_setting("current_round", "予選2")
                    st.success("🎉 予選2の座席割り当てが完了しました！")
                    st.rerun()

            # 3. 決勝ラウンド
            with st.expander("【アクション3】決勝ラウンドの座席割り当て (足切り機能付き)", expanded=True):
                st.markdown(
                    "予選1・2の総合順位に基づき、1〜10位を「チャンピオン卓」、11〜20位を「シルバー卓」、21〜30位を「ブロンズ卓」に仮配置します。\n\n"
                    "チャンピオン卓内の運営メンバーが上限を超える場合、**順位の低い運営をシルバー卓へ降格**させ、**シルバー卓の最上位一般メンバーをチャンピオン卓へ昇格**させます。"
                )

                # 上限人数設定
                current_limit = int(db.get_setting("admin_limit_champion", "3"))
                admin_limit = st.slider(
                    "👑 チャンピオン卓に進出できる運営メンバーの上限人数",
                    min_value=0,
                    max_value=10,
                    value=current_limit,
                    help="チャンピオン卓にこれ以上の運営が進出した場合、一般参加者が繰り上げ昇格します (デフォルト3人)",
                )
                if admin_limit != current_limit:
                    db.set_setting("admin_limit_champion", str(admin_limit))

                existing_final_seats = db.get_seats_by_round("決勝")
                if existing_final_seats:
                    st.info(f"ℹ️ 決勝ラウンドは既に割り当て済みです（{len(existing_final_seats)}名割り当て中）。再実行すると上書きされます。")

                if st.button("🏆 決勝ラウンドの座席割り当て（足切り含む）を実行する", type="primary", key="btn_assign_final"):
                    all_scores = db.get_all_scores_summary()
                    # 予選1・予選2のスコアに基づいて総合順位算出
                    overall_rankings = logic.calculate_overall_ranking(players, all_scores, target_rounds=["予選1", "予選2"])
                    
                    final_assignments, swap_history = logic.assign_final_seats_with_admin_cutoff(
                        overall_rankings,
                        admin_limit_champion=admin_limit,
                    )
                    
                    db.save_seats("決勝", final_assignments)
                    db.set_setting("current_round", "決勝")

                    st.success("🎉 決勝ラウンドの座席割り当てが完了しました！")

                    # 足切り入替履歴の表示
                    if swap_history:
                        st.markdown("#### 🔄 運営足切り・繰り上げ昇格の処理履歴")
                        for sw in swap_history:
                            st.write(
                                f"- 🔻 **降格**: 運営 **{sw['demoted_admin']}** 選手 (予選総合 {sw['demoted_rank']}位) ➔ {sw['from_table']}\n"
                                f"  🔺 **昇格**: 一般 **{sw['promoted_general']}** 選手 (予選総合 {sw['promoted_rank']}位) ➔ チャンピオン卓"
                            )
                    else:
                        st.info("※ チャンピオン卓内の運営人数は上限内だったため、足切り・繰り上げは発生しませんでした。")

                    st.rerun()

    # ---------------------------------------------------------
    # 運営タブ2: 参加者・進捗管理
    # ---------------------------------------------------------
    with admin_tab2:
        st.markdown("### 👥 参加者一覧および管理")
        players = db.get_all_players()
        if players:
            df_m = pd.DataFrame(players)
            df_m["属性"] = df_m["role"].apply(lambda r: "運営" if r == "admin" else "一般")
            st.dataframe(
                df_m[["id", "tsunagate_id", "name", "属性", "created_at"]].rename(columns={
                    "id": "ID", "tsunagate_id": "つなげーとID", "name": "名前", "created_at": "登録日時"
                }),
                use_container_width=True,
                hide_index=True,
            )

            # 参加者削除
            with st.expander("⚠️ 参加者の削除（誤登録の修正用）"):
                del_player_id = st.selectbox(
                    "削除する参加者を選択",
                    [p["id"] for p in players],
                    format_func=lambda pid: next(f"ID:{p['id']} - {p['name']} ({p['role']})" for p in players if p["id"] == pid),
                )
                if st.button("🗑️ 選択した参加者を削除する", type="secondary"):
                    db.delete_player(del_player_id)
                    st.warning("参加者を削除しました。")
                    st.rerun()
        else:
            st.info("参加者はまだいません。")

        st.markdown("---")
        st.markdown("### 📊 ラウンド別スコア入力進捗")
        for r_name in ["予選1", "予選2", "決勝"]:
            r_seats = db.get_seats_by_round(r_name)
            r_scores = db.get_scores_by_round(r_name)
            
            sc_count = len(r_scores)
            st_count = len(r_seats)
            pct = (sc_count / st_count) if st_count > 0 else 0
            
            st.markdown(f"**{r_name}**: {sc_count} / {st_count} 名 入力完了 ({int(pct*100)}%)")
            st.progress(pct)

            # 未入力者のリストアップ
            if st_count > 0 and sc_count < st_count:
                entered_pids = {s["player_id"] for s in r_scores}
                unentered = [s["player_name"] for s in r_seats if s["player_id"] not in entered_pids]
                st.caption(f"未入力者: {', '.join(unentered)}")

    # ---------------------------------------------------------
    # 運営タブ3: データ管理・テスト機能
    # ---------------------------------------------------------
    with admin_tab3:
        st.markdown("### 🧪 テスト用ダミーデータ投入 (リハーサル用)")
        st.caption("動作検証用に、30名（運営5名、一般25名）の一括登録および予選スコアを一括自動生成します。")

        col_dummy1, col_dummy2 = st.columns(2)
        with col_dummy1:
            if st.button("👥 30名のダミープレイヤーを一括作成", use_container_width=True):
                # 運営5名
                admin_names = ["運営パンダA", "運営パンダB", "運営パンダC", "運営パンダD", "運営パンダE"]
                for i, name in enumerate(admin_names, 1):
                    db.add_player(f"admin_{i:02d}", name, "admin")
                # 一般25名
                for i in range(1, 26):
                    db.add_player(f"user_{i:02d}", f"一般プレイヤー{i:02d}", "general")
                st.success("ダミープレイヤー30名を登録しました！")
                st.rerun()

        with col_dummy2:
            if st.button("🎲 予選1・2のランダムスコアを一括生成", use_container_width=True):
                # 予選1と予選2のスコアを自動生成
                for r_name in ["予選1", "予選2"]:
                    seats = db.get_seats_by_round(r_name)
                    if not seats:
                        st.error(f"{r_name} の座席割り当てがまだ実行されていません。")
                        continue
                    for s in seats:
                        # 30〜120点のランダムスコア
                        random_score = random.randint(30, 120)
                        db.save_score(r_name, s["player_id"], random_score, s["table_name"])
                    # 順位点計算
                    scs = db.get_scores_by_round(r_name)
                    calc = logic.calculate_table_ranks_and_points(scs)
                    db.update_rank_points_in_db(r_name, calc)
                st.success("予選1・2のスコアを自動生成し、順位点を計算しました！")
                st.rerun()

        st.markdown("---")
        st.markdown("### ⚠️ 大会データのリセット")
        st.caption("全スコア・座席割り当て・参加者情報を完全にクリアし、大会を初期状態に戻します。")
        
        with st.expander("🚨 全データ削除の確認"):
            confirm_text = st.text_input("確認のため「RESET」と入力してください")
            if st.button("💥 全データを完全にリセットする", type="primary"):
                if confirm_text == "RESET":
                    db.reset_all_data()
                    st.success("全データをリセットしました。")
                    st.rerun()
                else:
                    st.error("確認テキストが一致しません。")


# ==============================================================================
# メインエントリーポイント
# ==============================================================================
def main():
    selected_menu = render_sidebar()

    if selected_menu == "📝 エントリー画面":
        render_entry_page()
    elif selected_menu == "🎲 スコア入力画面":
        render_score_page()
    elif selected_menu == "📊 ダッシュボード (閲覧専用)":
        render_dashboard_page()
    elif selected_menu == "⚙️ 運営用管理画面":
        render_admin_page()


if __name__ == "__main__":
    main()
