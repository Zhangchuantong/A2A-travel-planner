# common/db.py
import pymysql
from pymysql.cursors import DictCursor
from config.settings import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)
def get_connection():
    """
    Create a MySQL connection.
    """
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )


def query_one(sql: str, params: tuple = None):
    """
    Execute a SELECT query and return one row.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()
    finally:
        conn.close()


def query_all(sql: str, params: tuple = None):
    """
    Execute a SELECT query and return all rows.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    finally:
        conn.close()