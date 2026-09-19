from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from backend.database import get_db
from backend.auth import get_current_user, require_same_user
import uuid
import logging
import bcrypt

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="TripClip Backend",
    version="1.0",
    description="여행 코스 AI 추천 서비스"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 비밀번호 해싱 함수 ====================

def hash_password(password: str) -> str:
    """비밀번호를 해싱합니다"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('ascii')


# ==================== Pydantic 모델 ====================

class UserCreateRequest(BaseModel):
    """사용자 생성 요청 모델"""
    name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")
    email: str = Field(..., max_length=100, description="이메일")
    password: str = Field(..., min_length=6, description="비밀번호")

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        """bcrypt의 72바이트 제한을 초과하는 비밀번호는 거부한다."""
        if len(value.encode("utf-8")) > 72:
            raise ValueError("비밀번호는 UTF-8 기준 72바이트 이하여야 합니다.")
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "name": "테스트유저",
                "email": "test@example.com",
                "password": "password123"
            }
        }


class UserResponse(BaseModel):
    """사용자 응답 모델"""
    status: str
    message: str
    user_id: str
    name: str
    email: str


class TripCreateRequest(BaseModel):
    """여행 생성 요청 모델"""
    trip_name: str = Field(..., min_length=1, max_length=200, description="여행 이름")
    region: str = Field(..., min_length=1, max_length=100, description="여행 지역")
    start_date: str = Field(..., description="시작 날짜 (YYYY-MM-DD)")
    end_date: str = Field(..., description="종료 날짜 (YYYY-MM-DD)")
    owner_user_id: str = Field(..., min_length=1, max_length=36, description="방장 사용자 ID")
    day_start_time: str = Field(default="13:00:00", description="하루 시작 시간")
    day_end_time: str = Field(default="20:00:00", description="하루 종료 시간")
    description: str = Field(default="", description="여행 설명")

    class Config:
        json_schema_extra = {
            "example": {
                "trip_name": "성수 여행",
                "region": "성수",
                "start_date": "2026-09-20",
                "end_date": "2026-09-20",
                "owner_user_id": "user-123",
                "day_start_time": "13:00:00",
                "day_end_time": "20:00:00",
                "description": ""
            }
        }


class TripResponse(BaseModel):
    """여행 응답 모델"""
    status: str
    message: str
    trip_id: str
    trip_name: str
    region: str
    start_date: str
    end_date: str


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    status: str = "error"
    message: str
    detail: str = None


# ==================== 헬퍼 함수 ====================

def validate_date_format(date_string: str) -> bool:
    """날짜 형식 검증 (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_time_format(time_string: str) -> bool:
    """시간 형식 검증 (HH:MM:SS)"""
    try:
        datetime.strptime(time_string, "%H:%M:%S")
        return True
    except ValueError:
        return False


# ==================== 기본 라우트 ====================

@app.get("/")
def read_root():
    """서버 상태 확인"""
    return {
        "message": "TripClip Community Backend Server is running!",
        "version": "1.0",
        "status": "healthy"
    }


@app.get("/health")
def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# ==================== 사용자 API ====================

@app.get("/health/db")
def database_health(db: Session = Depends(get_db)) -> dict:
    """Check connectivity without returning database credentials or driver errors."""
    from sqlalchemy.exc import SQLAlchemyError
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok", "database": "connected"}

@app.post("/api/users", response_model=UserResponse, status_code=201)
def create_user(
        user_data: UserCreateRequest,
        db: Session = Depends(get_db)
):
    """
    사용자 생성 API

    - **name**: 사용자 이름 (필수)
    - **email**: 이메일 (필수)
    - **password**: 비밀번호 (필수, 6자 이상)
    """
    try:
        # 1. 이메일 중복 확인
        email_check = db.execute(
            text("SELECT user_id FROM users WHERE email = :email"),
            {"email": user_data.email}
        ).fetchone()

        if email_check:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 이메일입니다."
            )

        # 2. 사용자 생성
        user_id = str(uuid.uuid4())
        password_hash = hash_password(user_data.password)

        query = text("""
            INSERT INTO users (
                user_id,
                name,
                email,
                password_hash,
                is_active,
                created_at,
                updated_at
            )
            VALUES (
                :user_id,
                :name,
                :email,
                :password_hash,
                TRUE,
                NOW(),
                NOW()
            )
        """)

        db.execute(query, {
            "user_id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "password_hash": password_hash
        })
        db.commit()

        logger.info(f"User created successfully: {user_id}")

        return UserResponse(
            status="success",
            message="사용자가 성공적으로 생성되었습니다!",
            user_id=user_id,
            name=user_data.name,
            email=user_data.email
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 생성 중 오류가 발생했습니다: {type(e).__name__}"
        )


@app.get("/api/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    """
    특정 사용자 정보 조회 API
    """
    try:
        query = text("""
            SELECT
                user_id,
                name,
                email,
                profile_image_url,
                bio,
                is_active,
                created_at
            FROM users
            WHERE user_id = :user_id
        """)

        result = db.execute(query, {"user_id": user_id}).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        return {
            "status": "success",
            "data": {
                "user_id": result[0],
                "name": result[1],
                "email": result[2],
                "profile_image_url": result[3],
                "bio": result[4],
                "is_active": result[5],
                "created_at": str(result[6])
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 조회 중 오류가 발생했습니다: {type(e).__name__}"
        )

@app.get("/api/users")
def list_users(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """활성 사용자 목록 조회 API"""
    try:
        results = db.execute(
            text("""
                SELECT
                    user_id,
                    name,
                    email
                FROM users
                WHERE is_active = TRUE
                ORDER BY created_at, user_id
            """)
        ).mappings().all()

        return {
            "status": "success",
            "data": [
                {
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "email": row["email"],
                }
                for row in results
            ],
        }

    except Exception as e:
        logger.error("Error fetching users: %s", type(e).__name__)
        raise HTTPException(
            status_code=500,
            detail="사용자 목록 조회 중 오류가 발생했습니다.",
        )


# ==================== 여행 API ====================

@app.post("/api/trips", response_model=TripResponse, status_code=201)
def create_trip(
        trip_data: TripCreateRequest,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user),
):
    """
    여행 그룹 생성 API

    - **trip_name**: 여행 이름 (필수)
    - **region**: 여행 지역 (필수)
    - **start_date**: 시작 날짜 YYYY-MM-DD (필수)
    - **end_date**: 종료 날짜 YYYY-MM-DD (필수)
    - **owner_user_id**: 방장 사용자 ID (필수)
    - **day_start_time**: 하루 시작 시간 (기본값: 13:00:00)
    - **day_end_time**: 하루 종료 시간 (기본값: 20:00:00)
    - **description**: 여행 설명 (선택사항)
    """
    require_same_user(trip_data.owner_user_id, current_user)
    try:
        # 1. 입력값 검증
        if not validate_date_format(trip_data.start_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date 형식이 잘못되었습니다. (YYYY-MM-DD)"
            )

        if not validate_date_format(trip_data.end_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date 형식이 잘못되었습니다. (YYYY-MM-DD)"
            )

        if not validate_time_format(trip_data.day_start_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="day_start_time 형식이 잘못되었습니다. (HH:MM:SS)"
            )

        if not validate_time_format(trip_data.day_end_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="day_end_time 형식이 잘못되었습니다. (HH:MM:SS)"
            )

        # 시작일이 종료일보다 이전인지 확인
        start = datetime.strptime(trip_data.start_date, "%Y-%m-%d")
        end = datetime.strptime(trip_data.end_date, "%Y-%m-%d")

        if start > end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="시작 날짜가 종료 날짜보다 클 수 없습니다."
            )

        # 사용자 존재 여부 확인
        user_check = db.execute(
            text("SELECT user_id FROM users WHERE user_id = :user_id"),
            {"user_id": trip_data.owner_user_id}
        ).fetchone()

        if not user_check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        # 2. 여행 생성
        trip_id = str(uuid.uuid4())

        query = text("""
            INSERT INTO trips (
                trip_id,
                owner_user_id,
                trip_name,
                region,
                start_date,
                end_date,
                day_start_time,
                day_end_time,
                description,
                status,
                created_at,
                updated_at
            )
            VALUES (
                :trip_id,
                :owner_user_id,
                :trip_name,
                :region,
                :start_date,
                :end_date,
                :day_start_time,
                :day_end_time,
                :description,
                'planning',
                NOW(),
                NOW()
            )
        """)

        db.execute(query, {
            "trip_id": trip_id,
            "owner_user_id": trip_data.owner_user_id,
            "trip_name": trip_data.trip_name,
            "region": trip_data.region,
            "start_date": trip_data.start_date,
            "end_date": trip_data.end_date,
            "day_start_time": trip_data.day_start_time,
            "day_end_time": trip_data.day_end_time,
            "description": trip_data.description
        })
        db.execute(text("INSERT INTO trip_members (trip_member_id,trip_id,user_id) VALUES (:id,:trip,:user)"),
                   {"id": str(uuid.uuid4()), "trip": trip_id, "user": trip_data.owner_user_id})
        db.commit()

        logger.info(f"Trip created successfully: {trip_id}")

        return TripResponse(
            status="success",
            message="여행 그룹이 성공적으로 생성되었습니다!",
            trip_id=trip_id,
            trip_name=trip_data.trip_name,
            region=trip_data.region,
            start_date=trip_data.start_date,
            end_date=trip_data.end_date
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating trip: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 생성 중 오류가 발생했습니다: {type(e).__name__}"
        )


@app.get("/api/trips/{trip_id}")
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    """
    특정 여행 정보 조회 API
    """
    try:
        query = text("""
            SELECT
                trip_id,
                owner_user_id,
                trip_name,
                region,
                start_date,
                end_date,
                day_start_time,
                day_end_time,
                status,
                description,
                created_at,
                updated_at
            FROM trips
            WHERE trip_id = :trip_id
        """)

        result = db.execute(query, {"trip_id": trip_id}).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="여행을 찾을 수 없습니다."
            )

        return {
            "status": "success",
            "data": {
                "trip_id": result[0],
                "owner_user_id": result[1],
                "trip_name": result[2],
                "region": result[3],
                "start_date": str(result[4]),
                "end_date": str(result[5]),
                "day_start_time": str(result[6]),
                "day_end_time": str(result[7]),
                "status": result[8],
                "description": result[9],
                "created_at": str(result[10]),
                "updated_at": str(result[11])
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trip: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 조회 중 오류가 발생했습니다: {type(e).__name__}"
        )


@app.get("/api/users/{user_id}/trips")
def get_user_trips(user_id: str, db: Session = Depends(get_db)):
    """
    특정 사용자의 모든 여행 조회 API
    """
    try:
        query = text("""
            SELECT
                trip_id,
                owner_user_id,
                trip_name,
                region,
                start_date,
                end_date,
                status,
                created_at
            FROM trips
            WHERE owner_user_id = :user_id
            ORDER BY created_at DESC
        """)

        results = db.execute(query, {"user_id": user_id}).fetchall()

        trips = [
            {
                "trip_id": row[0],
                "owner_user_id": row[1],
                "trip_name": row[2],
                "region": row[3],
                "start_date": str(row[4]),
                "end_date": str(row[5]),
                "status": row[6],
                "created_at": str(row[7])
            }
            for row in results
        ]

        return {
            "status": "success",
            "data": trips,
            "count": len(trips)
        }

    except Exception as e:
        logger.error(f"Error fetching user trips: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 여행 조회 중 오류가 발생했습니다: {type(e).__name__}"
        )


@app.put("/api/trips/{trip_id}")
def update_trip(
        trip_id: str,
        trip_data: TripCreateRequest,
        db: Session = Depends(get_db)
):
    """
    여행 정보 수정 API
    """
    try:
        # 1. 여행 존재 여부 확인
        check_query = text("SELECT trip_id FROM trips WHERE trip_id = :trip_id")
        existing_trip = db.execute(check_query, {"trip_id": trip_id}).fetchone()

        if not existing_trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="여행을 찾을 수 없습니다."
            )

        # 2. 날짜 형식 검증
        if not validate_date_format(trip_data.start_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date 형식이 잘못되었습니다. (YYYY-MM-DD)"
            )

        if not validate_date_format(trip_data.end_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date 형식이 잘못되었습니다. (YYYY-MM-DD)"
            )

        if not validate_time_format(trip_data.day_start_time) or not validate_time_format(trip_data.day_end_time):
            raise HTTPException(status_code=400, detail="시간 형식이 잘못되었습니다. (HH:MM:SS)")
        if datetime.strptime(trip_data.start_date, "%Y-%m-%d") > datetime.strptime(trip_data.end_date, "%Y-%m-%d"):
            raise HTTPException(status_code=400, detail="시작 날짜가 종료 날짜보다 클 수 없습니다.")
        if not db.execute(text("SELECT user_id FROM users WHERE user_id = :user_id"),
                          {"user_id": trip_data.owner_user_id}).fetchone():
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        # 3. 여행 정보 수정
        update_query = text("""
            UPDATE trips
            SET
                owner_user_id = :owner_user_id,
                trip_name = :trip_name,
                region = :region,
                start_date = :start_date,
                end_date = :end_date,
                day_start_time = :day_start_time,
                day_end_time = :day_end_time,
                description = :description,
                updated_at = NOW()
            WHERE trip_id = :trip_id
        """)

        db.execute(update_query, {
            "trip_id": trip_id,
            "owner_user_id": trip_data.owner_user_id,
            "trip_name": trip_data.trip_name,
            "region": trip_data.region,
            "start_date": trip_data.start_date,
            "end_date": trip_data.end_date,
            "day_start_time": trip_data.day_start_time,
            "day_end_time": trip_data.day_end_time,
            "description": trip_data.description
        })
        if not db.execute(text("SELECT user_id FROM trip_members WHERE trip_id=:trip AND user_id=:user"),
                          {"trip": trip_id, "user": trip_data.owner_user_id}).fetchone():
            db.execute(text("INSERT INTO trip_members (trip_member_id,trip_id,user_id) VALUES (:id,:trip,:user)"),
                       {"id": str(uuid.uuid4()), "trip": trip_id, "user": trip_data.owner_user_id})
        db.commit()

        logger.info(f"Trip updated successfully: {trip_id}")

        return {
            "status": "success",
            "message": "여행 정보가 성공적으로 수정되었습니다!",
            "trip_id": trip_id
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating trip: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 수정 중 오류가 발생했습니다: {type(e).__name__}"
        )


@app.delete("/api/trips/{trip_id}")
def delete_trip(trip_id: str, db: Session = Depends(get_db)):
    """
    여행 삭제 API
    """
    try:
        # 1. 여행 존재 여부 확인
        check_query = text("SELECT trip_id FROM trips WHERE trip_id = :trip_id")
        existing_trip = db.execute(check_query, {"trip_id": trip_id}).fetchone()

        if not existing_trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="여행을 찾을 수 없습니다."
            )

        from backend.services.common import require
        from backend.services.preference_service import recalculate
        require(db, "trips", trip_id, lock=True)
        affected_users = db.execute(text("SELECT DISTINCT user_id FROM shortform_contents WHERE trip_id=:id ORDER BY user_id"), {"id": trip_id}).scalars().all()
        for affected_user in affected_users:
            require(db, "users", affected_user, lock=True)

        # 2. 여행 삭제
        delete_query = text("DELETE FROM trips WHERE trip_id = :trip_id")
        db.execute(delete_query, {"trip_id": trip_id})
        for affected_user in affected_users:
            recalculate(db, affected_user)
        db.commit()

        logger.info(f"Trip deleted successfully: {trip_id}")

        return {
            "status": "success",
            "message": "여행이 성공적으로 삭제되었습니다!"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting trip: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 삭제 중 오류가 발생했습니다: {type(e).__name__}"
        )


# ==================== 서버 실행 ====================

from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from backend.services.common import ServiceError
from backend.routers import members, shortforms, preferences, itineraries
app.include_router(members.router)
app.include_router(shortforms.router)
app.include_router(preferences.router)
app.include_router(itineraries.router)
from backend.routers import auth
app.include_router(auth.router)


@app.exception_handler(ServiceError)
async def service_error_handler(request, error):
    return JSONResponse(status_code=error.status, content={"detail": error.message})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request, error):
    logger.error("Database operation failed: %s", type(error).__name__)
    return JSONResponse(status_code=500, content={"detail": "Database operation failed."})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
