"""
パンダロイヤル大会マネージャー - 大会ロジックモジュール (tournament_logic.py)
順位点計算、予選座席自動抽選、決勝座席抽選および運営足切り処理を提供します。
"""

import random
from typing import Any, Dict, List, Tuple
import pandas as pd


# ==============================================================================
# 1. 卓内順位および順位点の計算ロジック
# ==============================================================================
def calculate_table_ranks_and_points(scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    卓ごとに「獲得スコア」で順位を算出し、順位点を付与します。
    
    【ルール】
    - 卓ごとに獲得スコアの高い順に順位を決定。
    - 1位は必ず10pt。順位が1つ下がるごとに1pt減算 (2位: 9pt, 3位: 8pt ...)。
    - 例: 9人卓の最下位(9位)は 10 - (9 - 1) = 2pt。
    - 同点(タイ)の場合は、同順位として同一の順位点を付与（例: 2位タイが2人の場合、両者とも9pt）。
    
    Args:
        scores: [{'player_id': int, 'table_name': str, 'score': int, ...}, ...]
        
    Returns:
        順位(rank_in_table)と順位点(rank_points)が付与された辞書のリスト
    """
    if not scores:
        return []

    # 卓ごとにグループ分け
    tables: Dict[str, List[Dict[str, Any]]] = {}
    for s in scores:
        tbl = s.get("table_name", "未割当")
        tables.setdefault(tbl, []).append(dict(s))

    results: List[Dict[str, Any]] = []

    for tbl_name, player_scores in tables.items():
        # スコア降順でソート
        player_scores.sort(key=lambda x: x["score"], reverse=True)

        # 順位と順位点を算出 (ミニマムランク方式: 1, 2, 2, 4...)
        current_rank = 1
        for i, ps in enumerate(player_scores):
            if i > 0:
                prev_ps = player_scores[i - 1]
                if ps["score"] == prev_ps["score"]:
                    # 前の人と同点なら同じ順位
                    ps["rank_in_table"] = prev_ps["rank_in_table"]
                else:
                    # 異なるスコアなら、現在のインデックス+1が順位
                    ps["rank_in_table"] = i + 1
            else:
                ps["rank_in_table"] = 1

            # 順位点計算: 1位=10pt, 2位=9pt, ...
            # 10 - (rank - 1) = 11 - rank
            points = max(0, 11 - ps["rank_in_table"])
            ps["rank_points"] = points
            results.append(ps)

    return results


# ==============================================================================
# 2. 総合ランキング計算ロジック
# ==============================================================================
def calculate_overall_ranking(
    players: List[Dict[str, Any]],
    all_scores: List[Dict[str, Any]],
    target_rounds: List[str] = None
) -> List[Dict[str, Any]]:
    """
    全参加者の総合ランキングを算出します。
    
    【ルール】
    - 予選1・2の「順位点の合計」が最優先。
    - 同点の場合は「獲得スコアの合計」が大きい方を上位とする。
    - さらに同点の場合はプレイヤーID昇順（または登録順）。
    
    Args:
        players: 全プレイヤーリスト
        all_scores: 全スコアレコード (ラウンド、player_id、score、rank_points など)
        target_rounds: 集計対象のラウンド（Noneの場合は ['予選1', '予選2']）
        
    Returns:
        総合順位(overall_rank)が付与された集計済みプレイヤーリスト
    """
    if target_rounds is None:
        target_rounds = ["予選1", "予選2"]

    # プレイヤー情報マップ作成
    ranking_data: Dict[int, Dict[str, Any]] = {}
    for p in players:
        pid = p["id"]
        ranking_data[pid] = {
            "player_id": pid,
            "tsunagate_id": p["tsunagate_id"],
            "player_name": p["name"],
            "role": p["role"],
            "total_rank_points": 0,
            "total_score": 0,
            "round_details": {},
        }

    # スコア集計
    for s in all_scores:
        r = s.get("round")
        pid = s.get("player_id")
        if r in target_rounds and pid in ranking_data:
            rp = s.get("rank_points") or 0
            sc = s.get("score") or 0
            ranking_data[pid]["total_rank_points"] += rp
            ranking_data[pid]["total_score"] += sc
            ranking_data[pid]["round_details"][r] = {
                "score": sc,
                "rank_points": rp,
                "table_name": s.get("table_name", ""),
                "rank_in_table": s.get("rank_in_table", 0),
            }

    # リスト化してソート
    ranking_list = list(ranking_data.values())
    
    # ソート順: 
    # 1. 順位点合計 (降順)
    # 2. 獲得スコア合計 (降順)
    # 3. プレイヤーID (昇順: タイブレークの決定性のため)
    ranking_list.sort(
        key=lambda x: (
            x["total_rank_points"],
            x["total_score"],
            -x["player_id"]
        ),
        reverse=True,
    )

    # 総合順位 (overall_rank) を付与
    for i, item in enumerate(ranking_list):
        item["overall_rank"] = i + 1

    return ranking_list


# ==============================================================================
# 3. 予選（予選1・予選2）の座席自動割り当てロジック
# ==============================================================================
def assign_preliminary_seats(
    players: List[Dict[str, Any]],
    table_names: List[str] = None,
    max_seats_per_table: int = 10,
    seed: int = None
) -> List[Dict[str, Any]]:
    """
    予選の座席を自動割り当てします。
    
    【ルール】
    - 参加者を「運営(admin)」と「一般(general)」に分ける。
    - 運営メンバーをシャッフルし、A卓・B卓・C卓に均等（各卓1〜2名）に振り分ける。
    - 残りの枠に、一般メンバーをシャッフルして割り当てる。各卓最大10名。
    - 各卓内での席番号(1〜10)を割り当てる。
    
    Args:
        players: 全参加者リスト
        table_names: 卓名リスト (デフォルト: ['A卓', 'B卓', 'C卓'])
        max_seats_per_table: 各卓の上限人数 (デフォルト: 10)
        seed: 乱数シード（テスト再現用）
        
    Returns:
        座席割り当てリスト: [{'player_id': int, 'table_name': str, 'seat_number': int}, ...]
    """
    if table_names is None:
        table_names = ["A卓", "B卓", "C卓"]

    rng = random.Random(seed)

    # 属性ごとに分離
    admins = [p for p in players if p["role"] == "admin"]
    generals = [p for p in players if p["role"] == "general"]

    # それぞれシャッフル
    rng.shuffle(admins)
    rng.shuffle(generals)

    # 各卓のプレイヤーリスト初期化
    assigned_tables: Dict[str, List[Dict[str, Any]]] = {tbl: [] for tbl in table_names}

    # 1. 運営メンバーを均等（ラウンドロビン）に振り分け
    for i, admin in enumerate(admins):
        target_table = table_names[i % len(table_names)]
        assigned_tables[target_table].append(admin)

    # 2. 残りの枠に一般メンバーを均等に振り分け
    # 各卓が上限(max_seats_per_table)を超えないようにしつつ、卓ごとの人数ができるだけ均等になるように配置
    for general in generals:
        # 最も人数の少ない卓（複数ある場合はシャッフルされた順序で最初のもの）を選択
        available_tables = [
            tbl for tbl in table_names
            if len(assigned_tables[tbl]) < max_seats_per_table
        ]
        if not available_tables:
            # 全卓満席の場合（30名上限超過時）
            break

        # 人数が最も少ない卓を探す
        target_table = min(available_tables, key=lambda tbl: len(assigned_tables[tbl]))
        assigned_tables[target_table].append(general)

    # 3. 各卓内のプレイヤー席順を割り当て（運営スタッフを先頭席に配置）
    result_assignments: List[Dict[str, Any]] = []
    for tbl in table_names:
        table_players = assigned_tables[tbl]
        tbl_admins = [p for p in table_players if p.get("role") == "admin"]
        tbl_generals = [p for p in table_players if p.get("role") == "general"]
        rng.shuffle(tbl_admins)
        rng.shuffle(tbl_generals)
        ordered_players = tbl_admins + tbl_generals
        for seat_idx, p in enumerate(ordered_players, start=1):
            result_assignments.append({
                "player_id": p["id"],
                "table_name": tbl,
                "seat_number": seat_idx,
                "player_name": p["name"],
                "role": p["role"],
            })

    return result_assignments


# ==============================================================================
# 4. 決勝の座席割り当てロジック & 運営足切り処理
# ==============================================================================
def assign_final_seats_with_admin_cutoff(
    overall_rankings: List[Dict[str, Any]],
    admin_limit_champion: int = 3,
    champion_capacity: int = 10,
    silver_capacity: int = 10,
    bronze_capacity: int = 10,
    seed: int = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    決勝ラウンドの座席割り当てを行い、運営足切り・繰り上げ処理を実行します。
    
    【ルール】
    1. 予選終了時の総合順位に基づき：
       - 1〜10位: 「チャンピオン卓」
       - 11〜20位: 「シルバー卓」
       - 21〜30位: 「ブロンズ卓」
       に仮配置。
    2. 【運営足切り処理】
       - チャンピオン卓内の運営メンバー数をカウント。
       - 上限（admin_limit_champion、デフォルト3名）を超える場合：
         - チャンピオン卓内の「総合順位が最も低い運営メンバー」をシルバー卓へ降格。
         - シルバー卓（11位以下）の「最上位の一般メンバー」をチャンピオン卓へ繰り上げ昇格。
         - 上限人数に収まるまでループ（再帰的）に処理を繰り返す。
    3. 各卓内で座席番号(1〜10)をシャッフル付与。
    
    Args:
        overall_rankings: calculate_overall_ranking で算出された1位からのリスト
        admin_limit_champion: チャンピオン卓に進出できる運営上限人数 (通常3名)
        champion_capacity: チャンピオン卓定員 (通常10名)
        silver_capacity: シルバー卓定員 (通常10名)
        bronze_capacity: ブロンズ卓定員 (通常10名)
        seed: 乱数シード
        
    Returns:
        (座席割り当てリスト, 足切り・入替履歴リスト)
    """
    rng = random.Random(seed)

    # 順位順に仮配置（ディープコピーで独立させる）
    ranked_list = [dict(p) for p in overall_rankings]

    champion_table = ranked_list[:champion_capacity]
    silver_table = ranked_list[champion_capacity: champion_capacity + silver_capacity]
    bronze_table = ranked_list[champion_capacity + silver_capacity: champion_capacity + silver_capacity + bronze_capacity]

    # 入替ログの記録用
    swap_history: List[Dict[str, Any]] = []

    # 運営足切りループ処理
    # チャンピオン卓の運営数が上限を超えている限り繰り返す
    while True:
        champion_admins = [p for p in champion_table if p["role"] == "admin"]
        if len(champion_admins) <= admin_limit_champion:
            # 上限以下になったので終了
            break

        # チャンピオン卓の中で「総合順位が最も低い（数値が大きい）運営メンバー」
        # overall_rank が最大の運営を取得
        demote_admin = max(champion_admins, key=lambda p: p["overall_rank"])

        # シルバー卓（11位以下）の中で「最上位（overall_rankが最小）の一般メンバー」
        silver_generals = [p for p in silver_table if p["role"] == "general"]

        # もしシルバー卓に一般がいない場合はブロンズ卓も含めて探す
        promote_general = None
        source_table_name = "シルバー卓"
        if silver_generals:
            promote_general = min(silver_generals, key=lambda p: p["overall_rank"])
        else:
            bronze_generals = [p for p in bronze_table if p["role"] == "general"]
            if bronze_generals:
                promote_general = min(bronze_generals, key=lambda p: p["overall_rank"])
                source_table_name = "ブロンズ卓"

        # 繰り上げ可能な一般メンバーがいない場合はループ終了（安全措置）
        if promote_general is None:
            break

        # 入れ替え実行
        # 1. チャンピオン卓から降格運営を除去し、昇格一般を追加
        champion_table.remove(demote_admin)
        champion_table.append(promote_general)

        # 2. 該当卓から昇格一般を除去し、降格運営を追加
        if source_table_name == "シルバー卓":
            silver_table.remove(promote_general)
            silver_table.append(demote_admin)
        else:
            bronze_table.remove(promote_general)
            bronze_table.append(demote_admin)

        # 履歴記録
        swap_history.append({
            "demoted_admin": demote_admin["player_name"],
            "demoted_rank": demote_admin["overall_rank"],
            "promoted_general": promote_general["player_name"],
            "promoted_rank": promote_general["overall_rank"],
            "from_table": source_table_name,
        })

    # 各卓内で席順をシャッフルし、seat_number(1〜)を付与
    final_assignments: List[Dict[str, Any]] = []

    table_configs = [
        ("チャンピオン卓", champion_table),
        ("シルバー卓", silver_table),
        ("ブロンズ卓", bronze_table),
    ]

    for tbl_name, player_list in table_configs:
        if not player_list:
            continue
        # 卓内で運営を先頭（1番席〜）、一般をその後に割り当て
        tbl_admins = [p for p in player_list if p.get("role") == "admin"]
        tbl_generals = [p for p in player_list if p.get("role") == "general"]
        rng.shuffle(tbl_admins)
        rng.shuffle(tbl_generals)
        ordered_players = tbl_admins + tbl_generals
        for seat_num, p in enumerate(ordered_players, start=1):
            final_assignments.append({
                "player_id": p["player_id"],
                "table_name": tbl_name,
                "seat_number": seat_num,
                "player_name": p["player_name"],
                "role": p["role"],
                "overall_rank": p["overall_rank"],
            })

    return final_assignments, swap_history
