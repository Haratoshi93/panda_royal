"""
DB・アプリ統合テストスクリプト
"""

import database as db
import tournament_logic as logic

# DB初期化
db.init_db()
db.reset_all_data()

# プレイヤー追加
print("1. プレイヤー登録テスト")
success, msg = db.add_player("tsuna_01", "パンダ太郎", "admin")
assert success, msg
success, msg = db.add_player("tsuna_02", "パンダ次郎", "general")
assert success, msg
success, msg = db.add_player("tsuna_01", "別の人", "general")
assert not success, "重複登録が弾かれていません"

# 30名登録
for i in range(3, 7):
    db.add_player(f"admin_{i}", f"運営スタッフ{i}", "admin")
for i in range(7, 31):
    db.add_player(f"user_{i}", f"一般参加者{i}", "general")

players = db.get_all_players()
assert len(players) == 30, f"プレイヤー数が不正: {len(players)}"
print(f"プレイヤー登録成功: {len(players)}名")

# 予選1座席割り当て
print("2. 予選1座席割り当てテスト")
p1_assignments = logic.assign_preliminary_seats(players, ["A卓", "B卓", "C卓"], seed=100)
db.save_seats("予選1", p1_assignments)
p1_seats = db.get_seats_by_round("予選1")
assert len(p1_seats) == 30, "座席保存数が不正"

# スコア入力
print("3. スコア登録・順位点計算テスト")
for s in p1_seats:
    score_val = (s["player_id"] * 7) % 100 + 20
    db.save_score("予選1", s["player_id"], score_val, s["table_name"])

p1_scores = db.get_scores_by_round("予選1")
calc_p1 = logic.calculate_table_ranks_and_points(p1_scores)
db.update_rank_points_in_db("予選1", calc_p1)

# ランキング確認
overall = logic.calculate_overall_ranking(players, db.get_all_scores_summary(), ["予選1"])
# プレイヤー属性更新・タグ付けテスト
print("4. 属性更新・タグ付けテスト")
db.update_player_role(players[0]["id"], "general")
updated_p0 = next(p for p in db.get_all_players() if p["id"] == players[0]["id"])
assert updated_p0["role"] == "general", "個別属性更新が反映されていません"

bulk_updates = {players[1]["id"]: "admin", players[2]["id"]: "general"}
db.update_player_roles_bulk(bulk_updates)
all_p = db.get_all_players()
p1_after = next(p for p in all_p if p["id"] == players[1]["id"])
p2_after = next(p for p in all_p if p["id"] == players[2]["id"])
assert p1_after["role"] == "admin", "一括属性更新が反映されていません"
assert p2_after["role"] == "general", "一括属性更新が反映されていません"
print("属性更新・タグ付けテスト成功！")

print("DB統合テスト全て成功！")

