"""
パンダロイヤル大会マネージャー - データベース管理モジュール (database.py)
SQLite3を使用したデータベースの初期化、接続、CRUD操作を提供します。
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panda_royal.db")


def get_connection() -> sqlite3.Connection:
    """データベース接続を取得します（行ファクトリを行辞書型に設定）。"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """テーブルが存在しない場合に初期化を作成します。"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 参加者テーブル
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tsunagate_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL CHECK(role IN ('admin', 'general')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # 2. 座席割り当てテーブル
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round TEXT NOT NULL CHECK(round IN ('予選1', '予選2', '決勝')),
            player_id INTEGER NOT NULL,
            table_name TEXT NOT NULL,
            seat_number INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
            UNIQUE(round, player_id)
        )
        """
    )

    # 3. スコアテーブル
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round TEXT NOT NULL CHECK(round IN ('予選1', '予選2', '決勝')),
            player_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            table_name TEXT NOT NULL,
            rank_in_table INTEGER,
            rank_points INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
            UNIQUE(round, player_id)
        )
        """
    )

    # 4. アプリケーション設定テーブル
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    # デフォルト設定値の投入（存在しない場合のみ）
    default_settings = [
        ("admin_limit_champion", "3"),
        ("current_round", "予選1"),
    ]
    for key, value in default_settings:
        cursor.execute(
            "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()


# ==========================================
# 設定関連
# ==========================================
def get_setting(key: str, default: str = "") -> str:
    """設定値を取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """設定値を更新・保存します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


# ==========================================
# 参加者関連
# ==========================================
def add_player(tsunagate_id: str, name: str, role: str) -> Tuple[bool, str]:
    """参加者を新規登録します。"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO players (tsunagate_id, name, role) VALUES (?, ?, ?)",
            (tsunagate_id.strip(), name.strip(), role),
        )
        conn.commit()
        return True, "登録が完了しました！"
    except sqlite3.IntegrityError as e:
        err_msg = str(e)
        if "tsunagate_id" in err_msg:
            return False, "このつなげーとIDは既に登録されています。"
        elif "name" in err_msg:
            return False, "この名前は既に登録されています。"
        else:
            return False, f"登録エラー: {err_msg}"
    finally:
        conn.close()


def get_all_players() -> List[Dict[str, Any]]:
    """全参加者を登録順で取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def delete_player(player_id: int) -> None:
    """参加者を削除します（関連する座席・スコアも外部キーにより削除されます）。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM players WHERE id = ?", (player_id,))
    conn.commit()
    conn.close()


# ==========================================
# 座席関連
# ==========================================
def save_seats(round_name: str, assignments: List[Dict[str, Any]]) -> None:
    """指定ラウンドの座席割り当てを一括保存します。既存データは上書きされます。"""
    conn = get_connection()
    cursor = conn.cursor()
    # 既存の当該ラウンドの割り当てを削除
    cursor.execute("DELETE FROM seats WHERE round = ?", (round_name,))
    for a in assignments:
        cursor.execute(
            """
            INSERT INTO seats (round, player_id, table_name, seat_number)
            VALUES (?, ?, ?, ?)
            """,
            (round_name, a["player_id"], a["table_name"], a["seat_number"]),
        )
    conn.commit()
    conn.close()


def get_seats_by_round(round_name: str) -> List[Dict[str, Any]]:
    """指定ラウンドの座席表をプレイヤー情報付きで取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            s.id AS seat_id,
            s.round,
            s.table_name,
            s.seat_number,
            p.id AS player_id,
            p.tsunagate_id,
            p.name AS player_name,
            p.role
        FROM seats s
        JOIN players p ON s.player_id = p.id
        WHERE s.round = ?
        ORDER BY s.table_name ASC, s.seat_number ASC
        """,
        (round_name,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_player_seat(round_name: str, player_id: int) -> Optional[Dict[str, Any]]:
    """特定プレイヤーの特定ラウンドの座席情報を取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT table_name, seat_number 
        FROM seats 
        WHERE round = ? AND player_id = ?
        """,
        (round_name, player_id),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ==========================================
# スコア関連
# ==========================================
def save_score(round_name: str, player_id: int, score: int, table_name: str) -> None:
    """スコアを登録または更新します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO scores (round, player_id, score, table_name, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(round, player_id) DO UPDATE SET
            score = excluded.score,
            table_name = excluded.table_name,
            updated_at = CURRENT_TIMESTAMP
        """,
        (round_name, player_id, score, table_name),
    )
    conn.commit()
    conn.close()


def get_scores_by_round(round_name: str) -> List[Dict[str, Any]]:
    """指定ラウンドの全スコア一覧を取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            s.id AS score_id,
            s.round,
            s.player_id,
            s.score,
            s.table_name,
            s.rank_in_table,
            s.rank_points,
            s.updated_at,
            p.name AS player_name,
            p.role
        FROM scores s
        JOIN players p ON s.player_id = p.id
        WHERE s.round = ?
        ORDER BY s.table_name ASC, s.score DESC
        """,
        (round_name,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_rank_points_in_db(round_name: str, rank_updates: List[Dict[str, Any]]) -> None:
    """計算された卓内順位と順位点をDBに反映します。"""
    conn = get_connection()
    cursor = conn.cursor()
    for item in rank_updates:
        cursor.execute(
            """
            UPDATE scores
            SET rank_in_table = ?, rank_points = ?
            WHERE round = ? AND player_id = ?
            """,
            (item["rank_in_table"], item["rank_points"], round_name, item["player_id"]),
        )
    conn.commit()
    conn.close()


def get_all_scores_summary() -> List[Dict[str, Any]]:
    """全ラウンドのスコア状況を取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            p.id AS player_id,
            p.tsunagate_id,
            p.name AS player_name,
            p.role,
            s.round,
            s.score,
            s.table_name,
            s.rank_in_table,
            s.rank_points
        FROM players p
        LEFT JOIN scores s ON p.id = s.player_id
        ORDER BY p.id ASC, s.round ASC
        """
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ==========================================
# データベースリセット / テストデータ
# ==========================================
def reset_all_data() -> None:
    """全テーブルのデータを削除します（大会の新規初期化用）。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scores")
    cursor.execute("DELETE FROM seats")
    cursor.execute("DELETE FROM players")
    cursor.execute("UPDATE app_settings SET value = '3' WHERE key = 'admin_limit_champion'")
    cursor.execute("UPDATE app_settings SET value = '予選1' WHERE key = 'current_round'")
    conn.commit()
    conn.close()
