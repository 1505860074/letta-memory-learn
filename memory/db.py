"""数据库连接工具：所有三层记忆最终都落在这一个 Postgres 连接上。"""
import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://letta:letta@localhost:5432/letta_memory_learn")


def get_connection():
    # autocommit=True：这是个教学项目，不需要跨多条记忆操作做事务，简化心智负担
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    register_vector(conn)  # 让 psycopg 认识 Python list <-> pgvector 的 vector 类型
    return conn
