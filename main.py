from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db
import uuid
import logging
import hashlib  # bcrypt 대신 hashlib 사용

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
    hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return hashed


# ==================== Pydantic 모델 ====================

class UserCreateRequest(BaseModel):
    """사용자 생성 요청 모델"""
    name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")
    email: str = Field(..., description="이메일")
    password: str = Field(..., min_length=6, description="비밀번호")

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
    user_id: str = Field(..., description="사용자 ID")
    day_start_time: str = Field(default="09:00:00", description="하루 시작 시간")
    day_end_time: str = Field(default="22:00:00", description="하루 종료 시간")
    description: str = Field(default="", description="여행 설명")

    class Config:
        json_schema_extra = {
            "example": {
                "trip_name": "서울 여행",
                "region": "서울",
                "start_date": "2026-05-10",
                "end_date": "2026-05-12",
                "user_id": "user-123",
                "day_start_time": "09:00:00",
                "day_end_time": "22:00:00",
                "description": "서울 강남 지역 여행"
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
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 생성 중 오류가 발생했습니다: {str(e)}"
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
        logger.error(f"Error fetching user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 조회 중 오류가 발생했습니다: {str(e)}"
        )


# ==================== 여행 API ====================

@app.post("/api/trips", response_model=TripResponse, status_code=201)
def create_trip(
        trip_data: TripCreateRequest,
        db: Session = Depends(get_db)
):
    """
    여행 그룹 생성 API

    - **trip_name**: 여행 이름 (필수)
    - **region**: 여행 지역 (필수)
    - **start_date**: 시작 날짜 YYYY-MM-DD (필수)
    - **end_date**: 종료 날짜 YYYY-MM-DD (필수)
    - **user_id**: 사용자 ID (필수)
    - **day_start_time**: 하루 시작 시간 (기본값: 09:00:00)
    - **day_end_time**: 하루 종료 시간 (기본값: 22:00:00)
    - **description**: 여행 설명 (선택사항)
    """
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
            {"user_id": trip_data.user_id}
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
                user_id, 
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
                :user_id, 
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
            "user_id": trip_data.user_id,
            "trip_name": trip_data.trip_name,
            "region": trip_data.region,
            "start_date": trip_data.start_date,
            "end_date": trip_data.end_date,
            "day_start_time": trip_data.day_start_time,
            "day_end_time": trip_data.day_end_time,
            "description": trip_data.description
        })
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
        logger.error(f"Error creating trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 생성 중 오류가 발생했습니다: {str(e)}"
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
                user_id,
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
                "user_id": result[1],
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
        logger.error(f"Error fetching trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 조회 중 오류가 발생했습니다: {str(e)}"
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
                user_id,
                trip_name,
                region,
                start_date,
                end_date,
                status,
                created_at
            FROM trips
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """)

        results = db.execute(query, {"user_id": user_id}).fetchall()

        trips = [
            {
                "trip_id": row[0],
                "user_id": row[1],
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
        logger.error(f"Error fetching user trips: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 여행 조회 중 오류가 발생했습니다: {str(e)}"
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

        # 3. 여행 정보 수정
        update_query = text("""
            UPDATE trips
            SET 
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
            "trip_name": trip_data.trip_name,
            "region": trip_data.region,
            "start_date": trip_data.start_date,
            "end_date": trip_data.end_date,
            "day_start_time": trip_data.day_start_time,
            "day_end_time": trip_data.day_end_time,
            "description": trip_data.description
        })
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
        logger.error(f"Error updating trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 수정 중 오류가 발생했습니다: {str(e)}"
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

        # 2. 여행 삭제
        delete_query = text("DELETE FROM trips WHERE trip_id = :trip_id")
        db.execute(delete_query, {"trip_id": trip_id})
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
        logger.error(f"Error deleting trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"여행 삭제 중 오류가 발생했습니다: {str(e)}"
        )


# ==================== 서버 실행 ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
