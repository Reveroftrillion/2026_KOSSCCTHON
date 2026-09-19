from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

# MySQL 연결 URL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost/TripClip"

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
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """데이터베이스 테이블 초기화"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
