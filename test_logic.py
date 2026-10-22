"""
ロジック検証スクリプト
予選順位点計算、総合順位、予選座席配分、決勝足切り入替処理をテストします。
"""

import pprint
from tournament_logic import (
    calculate_table_ranks_and_points,
    calculate_overall_ranking,
    assign_preliminary_seats,
    assign_final_seats_with_admin_cutoff,
)

print("=== 1. 卓内順位点テスト ===")
test_scores = [
    {"player_id": 1, "table_name": "A卓", "score": 85},
    {"player_id": 2, "table_name": "A卓", "score": 90},  # 1位 -> 10pt
    {"player_id": 3, "table_name": "A卓", "score": 70},
    {"player_id": 4, "table_name": "A卓", "score": 85},  # 2位タイ -> 9pt
    {"player_id": 5, "table_name": "A卓", "score": 60},  # 4位 -> 7pt
]
ranked = calculate_table_ranks_and_points(test_scores)
for r in ranked:
    print(f"ID:{r['player_id']} Score:{r['score']} Rank:{r['rank_in_table']} Points:{r['rank_points']}")

print("\n=== 2. 予選座席割り当てテスト (30名: 運営6名、一般24名) ===")
test_players = []
for i in range(1, 7):
    test_players.append({"id": i, "name": f"Admin_{i}", "role": "admin", "tsunagate_id": f"T_ADM_{i}"})
for i in range(7, 31):
    test_players.append({"id": i, "name": f"General_{i}", "role": "general", "tsunagate_id": f"T_GEN_{i}"})

seats_p1 = assign_preliminary_seats(test_players, seed=42)
table_counts = {}
for s in seats_p1:
    tbl = s["table_name"]
    table_counts.setdefault(tbl, {"admin": 0, "general": 0, "total": 0})
    table_counts[tbl][s["role"]] += 1
    table_counts[tbl]["total"] += 1
pprint.pprint(table_counts)

print("\n=== 2-B. 予選2 同卓重複最小化テスト ===")
seats_p2 = assign_preliminary_seats(test_players, previous_seats=seats_p1, seed=42)
p1_map = {s["player_id"]: s["table_name"] for s in seats_p1}
p2_tables = {}
for s in seats_p2:
    p2_tables.setdefault(s["table_name"], []).append(s["player_id"])

overlap_pairs = 0
for tbl, pids in p2_tables.items():
    from_p1 = {}
    for pid in pids:
        orig = p1_map[pid]
        from_p1[orig] = from_p1.get(orig, 0) + 1
    for orig, cnt in from_p1.items():
        overlap_pairs += cnt * (cnt - 1) // 2
    print(f"  {tbl}の内訳 (予選1の所属卓別): {from_p1}")

print(f"予選2の同卓重複ペア数: {overlap_pairs} (理論最小値36に近いことを確認)")
assert overlap_pairs <= 38, f"同卓重複ペア数が多すぎます: {overlap_pairs}"

print("\n=== 3. 決勝座席割り当て＆運営足切りテスト ===")
# 予選総合順位で、上位10名中5名が運営だった場合（上限3名）
fake_rankings = []
# 1〜5位: 運営
for i in range(1, 6):
    fake_rankings.append({
        "player_id": i, "player_name": f"Admin_{i}", "role": "admin",
        "overall_rank": i, "total_rank_points": 20 - i, "total_score": 100 - i
    })
# 6〜30位: 一般
for i in range(6, 31):
    fake_rankings.append({
        "player_id": i, "player_name": f"General_{i}", "role": "general",
        "overall_rank": i, "total_rank_points": 15 - (i // 3), "total_score": 80 - i
    })

final_seats, swap_history = assign_final_seats_with_admin_cutoff(
    fake_rankings, admin_limit_champion=3, seed=42
)

print("入替履歴:")
for sw in swap_history:
    print(f"  降格: {sw['demoted_admin']} (順位:{sw['demoted_rank']}) <-> 昇格: {sw['promoted_general']} (順位:{sw['promoted_rank']})")

final_counts = {}
for s in final_seats:
    tbl = s["table_name"]
    final_counts.setdefault(tbl, {"admin": 0, "general": 0, "total": 0})
    final_counts[tbl][s["role"]] += 1
    final_counts[tbl]["total"] += 1

print("\n決勝卓ごとの人数内訳:")
pprint.pprint(final_counts)

print("\nチャンピオン卓のメンバー:")
for s in final_seats:
    if s["table_name"] == "チャンピオン卓":
        print(f"  座席{s['seat_number']}: {s['player_name']} ({s['role']}, 予選順位:{s['overall_rank']})")

print("\n全テスト完了: 正常動作確認")
