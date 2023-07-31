import datetime
import os
import sqlite3
from utils import processing
import json
from dataclasses import dataclass


@dataclass
class User:
    user_id: int
    login: str
    password: str
    grades: str
    time: str


def create_connection():
    conn = sqlite3.connect('database/main.db')
    return conn


def create_table(conn):
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            login TEXT,
            password TEXT,
            grades TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()


def insert_values(conn, user):
    c = conn.cursor()
    c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?)', (user.user_id, user.login,
                                                           processing.encrypt_password(user.password,
                                                                                       os.getenv("PASSWORD_CRYPT_KEY")),
                                                           user.grades, user.time))
    conn.commit()


def get_data_user(conn, user_id, table_name):
    c = conn.cursor()
    c.execute(f'SELECT login, password FROM {table_name} WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row:
        login, password = row
        return login, processing.decrypt_password(password, os.getenv("PASSWORD_CRYPT_KEY"))
    else:
        return None, None


def get_grades_db(conn, user_id):
    c = conn.cursor()
    c.execute('SELECT grades FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row:
        grades_json = row[0]
        grades_list = json.loads(grades_json)
        dr = [eval(i) for i in grades_list]

        return dr
    else:
        return None


def is_record_exists(conn, table_name, user_id):
    c = conn.cursor()
    query = f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE user_id = ?)"
    c.execute(query, (user_id,))
    result = c.fetchone()[0]
    return result == 1


def remove_user(conn, table_name, user_id):
    c = conn.cursor()
    c.execute(f'DELETE FROM {table_name} WHERE user_id = ?', (user_id,))
    conn.commit()


def update_user_grades(conn, user_id, new_grades):
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Выполните обновление данных с добавлением времени
    c = conn.cursor()
    c.execute('UPDATE users SET grades = ?, updated_at = ? WHERE user_id = ?', (new_grades, current_time, user_id))
    conn.commit()


def get_all_user_ids(conn) -> list:
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    user_ids = [row[0] for row in c.fetchall()]
    conn.close()
    return user_ids
