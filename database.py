import os
from sqlalchemy.engine import URL
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

# MySQL 연결 URL
SQLALCHEMY_DATABASE_URL = URL.create(
    "mysql+pymysql",
    username=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "tripclip"),
)

# 엔진 생성 (연결 풀 설정 포함)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=False,  # SQL 쿼리 로깅 (개발 시 True로 변경 가능)
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": 10,
    }
)

# MySQL 연결 시 utf8mb4 설정
@event.listens_for(engine, "connect")
def set_mysql_charset(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET NAMES utf8mb4")
    cursor.execute("SET CHARACTER SET utf8mb4")
    cursor.execute("SET SESSION COLLATION_CONNECTION=utf8mb4_unicode_ci")
    cursor.close()

# 세션 생성
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base 선언
Base = declarative_base()

# DB 세션 의존성 주입 함수
def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database error: %s", type(e).__name__)
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """등록된 ORM 모델만 초기화한다. 현재 테이블은 schema.sql로 별도 생성해야 한다."""
    Base.metadata.create_all(bind=engine)
    logger.info("Registered ORM metadata initialization completed")
