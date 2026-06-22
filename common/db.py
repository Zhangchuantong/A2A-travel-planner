# common/db.py
import os

import pymysql
from dbutils.pooled_db import PooledDB
from pymysql.cursors import DictCursor

from config.settings import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)

# 连接池：进程启动时预建若干连接放进池子，查询时借用、用完归还，
# 避免每次查询都重新和 MySQL 建立连接（建连开销远大于一次普通查询）。
_POOL = PooledDB(
    creator=pymysql,                # 用 pymysql 创建底层连接
    maxconnections=int(os.getenv("MYSQL_POOL_MAX", "10")),   # 池子最多允许的连接数
    mincached=int(os.getenv("MYSQL_POOL_MIN", "0")),         # 启动时预建的空闲连接数（0=懒加载，import 时不连库）
    maxcached=int(os.getenv("MYSQL_POOL_MAX_IDLE", "5")),    # 空闲时最多保留的连接数
    blocking=True,                  # 池满时排队等待，而不是直接报错
    ping=1,                         # 借出连接前 ping 一下，自动剔除已失效的连接
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE,
    charset="utf8mb4",
    cursorclass=DictCursor,
)


def get_connection():
    """
    从连接池借一个连接。
    注意：返回的是池化连接，调用 conn.close() 不会真正关闭连接，
    而是把它归还到池里复用，所以下面的查询函数无需改动。
    """
    return _POOL.connection()


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
