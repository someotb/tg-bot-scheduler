import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "../data/userdata.db")


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        group_id TEXT,
        username TEXT,
        firstname TEXT,
        lastname TEXT
    )
    """)
    conn.commit()
    conn.close()


def add_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,),
    )
    conn.commit()
    conn.close()


def set_group(user_id: int, gid: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET group_id = ? WHERE user_id = ?",
        (gid, user_id),
    )
    conn.commit()
    conn.close()


def get_group(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT group_id FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def set_username(user_id: int, username: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET username = ? WHERE user_id = ?",
        (username, user_id),
    )
    conn.commit()
    conn.close()
    
    
def get_username(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None
    

def set_firstname(user_id: int, firstname: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET firstname = ? WHERE user_id = ?",
        (firstname, user_id),
    )
    conn.commit()
    conn.close()


def get_firstname(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT firstname FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def set_lastname(user_id: int, lastname: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET lastname = ? WHERE user_id = ?",
        (lastname, user_id),
    )
    conn.commit()
    conn.close()


def get_lastname(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT lastname FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def user_exists(user_id: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM users WHERE user_id = ?",
        (user_id,),
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists
