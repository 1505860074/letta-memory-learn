"""数据库连接工具：所有三层记忆最终都落在这一个 Postgres 连接上。"""
# os：Python 标准库，用来读取操作系统环境变量
import os

# psycopg 第三方库：Postgres 的 Python 驱动（psycopg 3），负责和数据库通信
import psycopg
from dotenv import load_dotenv
# pgvector 第三方库：让 Postgres 支持向量列（vector 类型）；register_vector 注册后，
# psycopg 才能把 Python 的 list 与数据库里的 vector 类型自动互相转换
from pgvector.psycopg import register_vector

load_dotenv()

# os.environ.get(key, 默认值)：读环境变量，取不到时用默认值，避免键不存在直接报错
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://letta:letta@localhost:5432/letta_memory_learn")


def get_connection():
    # autocommit=True：这是个教学项目，不需要跨多条记忆操作做事务，简化心智负担
    # psycopg.connect(...)：根据 DATABASE_URL 建立一条到 Postgres 的连接
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    register_vector(conn)  # 让 psycopg 认识 Python list <-> pgvector 的 vector 类型
    return conn
