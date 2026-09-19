"""AI1 adapter and transactional SQL-backed content/preference persistence."""

import json
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from ai.preference_analyzer import (
    analyze_youtube_url,
    calculate_preferences,
)
from ai.preference_analyzer.metadata_fetcher import (
    MetadataError,
    extract_youtube_video_id,
)
from ai.preference_analyzer.schemas import AnalyzedContent

from backend.services.common import (
    ServiceError,
    decode,
    member,
    require,
    row,
    transaction,
)
from backend.services.place_service import (
    stable_place_db_id,
    verify_named_place,
)


def ai_user_id(user_id: str) -> int:
    """Backend UUID를 AI 내부용 양의 정수 ID로 변환한다."""
    return int.from_bytes(
        user_id.encode("utf-8"),
        "big",
    ) + 1


def get_profile(
    db: Session,
    user_id: str,
) -> dict:
    """저장된 사용자 취향을 Backend UUID 기준으로 반환한다."""

    require(
        db,
        "users",
        user_id,
    )

    saved = (
        row(
            db,
            """
            SELECT
                category_scores,
                tag_scores
            FROM user_preferences
            WHERE user_id=:id
            """,
            id=user_id,
        )
        or {}
    )

    return {
        "user_id": user_id,
        "category_preferences": decode(
            saved.get("category_scores"),
            {},
        ),
        "keyword_preferences": decode(
            saved.get("tag_scores"),
            {},
        ),
    }


def trip_profiles(
    db: Session,
    trip_id: str,
) -> list[dict]:
    """콘텐츠가 없는 사용자를 포함하여 여행 멤버의 취향을 반환한다."""

    require(
        db,
        "trips",
        trip_id,
    )

    ids = (
        db.execute(
            text("""
                SELECT user_id
                FROM trip_members
                WHERE trip_id=:id
                ORDER BY user_id
            """),
            {
                "id": trip_id,
            },
        )
        .scalars()
        .all()
    )

    return [
        get_profile(
            db,
            user_id,
        )
        for user_id in ids
    ]


def recalculate(
    db: Session,
    user_id: str,
) -> dict:
    """
    사용자의 전체 숏폼 이력을 읽어
    AI1 방식으로 취향을 다시 계산한다.
    """

    rows = db.execute(
        text("""
            SELECT
                category,
                keywords
            FROM shortform_contents
            WHERE user_id=:id
        """),
        {
            "id": user_id,
        },
    ).mappings()

    contents = [
        AnalyzedContent(
            category=item["category"],
            keywords=decode(
                item["keywords"],
                [],
            ),
        )
        for item in rows
    ]

    profile = calculate_preferences(
        ai_user_id(user_id),
        contents,
    ).model_dump()

    profile["user_id"] = user_id

    values = {
        "user": user_id,
        "categories": json.dumps(
            profile[
                "category_preferences"
            ]
        ),
        "tags": json.dumps(
            profile[
                "keyword_preferences"
            ]
        ),
    }

    existing = row(
        db,
        """
        SELECT preference_id
        FROM user_preferences
        WHERE user_id=:id
        """,
        id=user_id,
    )

    if existing:
        db.execute(
            text("""
                UPDATE user_preferences
                SET
                    category_scores=:categories,
                    tag_scores=:tags,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=:user
            """),
            values,
        )

    else:
        db.execute(
            text("""
                INSERT INTO user_preferences (
                    preference_id,
                    user_id,
                    category_scores,
                    tag_scores
                )
                VALUES (
                    :id,
                    :user,
                    :categories,
                    :tags
                )
            """),
            {
                **values,
                "id": str(
                    uuid.uuid4()
                ),
            },
        )

    return profile


def check_duplicate(
    db: Session,
    trip_id: str,
    user_id: str,
    url: str,
) -> None:
    """같은 여행에서 같은 사용자가 같은 영상을 중복 저장하지 못하게 한다."""

    duplicate = row(
        db,
        """
        SELECT content_id
        FROM shortform_contents
        WHERE
            trip_id=:trip
            AND user_id=:user
            AND url=:url
        """,
        trip=trip_id,
        user=user_id,
        url=url,
    )

    if duplicate:
        raise ServiceError(
            409,
            "이미 저장한 숏폼입니다.",
        )


def save_shortform(
    db: Session,
    trip_id: str,
    user_id: str,
    url: str,
) -> dict:
    """
    Shorts 분석 → 단일 장소 Kakao 검증 →
    콘텐츠/장소/취향을 하나의 트랜잭션으로 저장한다.
    """

    # ---------------------------------------------------------
    # 1. YouTube URL 정규화
    # ---------------------------------------------------------

    try:
        video_id = (
            extract_youtube_video_id(
                url
            )
        )

    except MetadataError:
        raise ServiceError(
            400,
            "올바른 YouTube URL을 입력해주세요.",
        ) from None

    canonical = (
        "https://www.youtube.com/watch"
        f"?v={video_id}"
    )

    # ---------------------------------------------------------
    # 2. 여행 멤버 및 중복 검사
    # ---------------------------------------------------------

    member(
        db,
        trip_id,
        user_id,
    )

    check_duplicate(
        db,
        trip_id,
        user_id,
        canonical,
    )

    # 외부 AI 호출 전에 validation read transaction 해제
    db.rollback()

    # ---------------------------------------------------------
    # 3. AI1 분석
    # ---------------------------------------------------------

    try:
        result = analyze_youtube_url(
            ai_user_id(user_id),
            canonical,
        )

        analysis = (
            AnalyzedContent.model_validate(
                result["analysis"]
            )
        )

        title = result[
            "metadata"
        ]["title"]

        if (
            not isinstance(
                title,
                str,
            )
            or not title.strip()
            or len(title) > 500
        ):
            raise ValueError(
                "Invalid metadata title"
            )

        for value, limit in (
            (
                analysis.area,
                100,
            ),
            (
                analysis.activity,
                255,
            ),
            (
                analysis.place_name,
                255,
            ),
        ):
            if (
                value
                and len(value) > limit
            ):
                raise ValueError(
                    "Analysis field too long"
                )

    except Exception:
        raise ServiceError(
            502,
            "숏폼 분석 또는 메타데이터 수집에 실패했습니다.",
        ) from None

    # ---------------------------------------------------------
    # 4. 단일 장소일 때만 Kakao Local 검증
    # ---------------------------------------------------------

    verified_place = None

    if analysis.place_name:
        verified_place = (
            verify_named_place(
                analysis.area,
                analysis.place_name,
            )
        )

    content_id = str(
        uuid.uuid4()
    )

    # ---------------------------------------------------------
    # 5. DB 저장
    # ---------------------------------------------------------

    with transaction(db):

        require(
            db,
            "trips",
            trip_id,
            lock=True,
        )

        require(
            db,
            "users",
            user_id,
            lock=True,
        )

        member(
            db,
            trip_id,
            user_id,
        )

        check_duplicate(
            db,
            trip_id,
            user_id,
            canonical,
        )

        # -----------------------------------------------------
        # 5-1. Kakao 검증 장소가 있으면 places에 upsert
        # -----------------------------------------------------

        place_id = None

        if verified_place is not None:

            place_id = (
                stable_place_db_id(
                    verified_place
                )
            )

            address = (
                verified_place.get(
                    "address",
                    "",
                )
                or ""
            )

            region = (
                analysis.area
                or (
                    address.split()[0]
                    if address
                    else "unknown"
                )
            )

            place_values = {
                "place_id":
                    place_id,

                "place_name":
                    verified_place[
                        "name"
                    ],

                "category":
                    verified_place[
                        "category"
                    ],

                "latitude":
                    verified_place[
                        "lat"
                    ],

                "longitude":
                    verified_place[
                        "lng"
                    ],

                "address":
                    address,

                "region":
                    region,
            }

            # MySQL
            if (
                db.bind.dialect.name
                == "mysql"
            ):
                db.execute(
                    text("""
                        INSERT INTO places (
                            place_id,
                            place_name,
                            category,
                            latitude,
                            longitude,
                            address,
                            region
                        )
                        VALUES (
                            :place_id,
                            :place_name,
                            :category,
                            :latitude,
                            :longitude,
                            :address,
                            :region
                        )
                        ON DUPLICATE KEY UPDATE
                            place_name =
                                :place_name,
                            category =
                                :category,
                            latitude =
                                :latitude,
                            longitude =
                                :longitude,
                            address =
                                :address,
                            region =
                                :region
                    """),
                    place_values,
                )

            # SQLite 테스트 환경
            else:
                existing_place = row(
                    db,
                    """
                    SELECT place_id
                    FROM places
                    WHERE place_id=:id
                    """,
                    id=place_id,
                )

                if existing_place:
                    db.execute(
                        text("""
                            UPDATE places
                            SET
                                place_name=:place_name,
                                category=:category,
                                latitude=:latitude,
                                longitude=:longitude,
                                address=:address,
                                region=:region
                            WHERE
                                place_id=:place_id
                        """),
                        place_values,
                    )

                else:
                    db.execute(
                        text("""
                            INSERT INTO places (
                                place_id,
                                place_name,
                                category,
                                latitude,
                                longitude,
                                address,
                                region
                            )
                            VALUES (
                                :place_id,
                                :place_name,
                                :category,
                                :latitude,
                                :longitude,
                                :address,
                                :region
                            )
                        """),
                        place_values,
                    )

        # -----------------------------------------------------
        # 5-2. shortform_contents 저장
        # -----------------------------------------------------

        values = (
            analysis.model_dump(
                mode="json"
            )
        )

        values.update(
            content_id=content_id,
            trip_id=trip_id,
            user_id=user_id,
            url=canonical,
            title=title,
            place_id=place_id,
            keywords=json.dumps(
                analysis.keywords,
                ensure_ascii=False,
            ),
        )

        db.execute(
            text("""
                INSERT INTO shortform_contents (
                    content_id,
                    trip_id,
                    user_id,
                    url,
                    title,
                    category,
                    keywords,
                    area,
                    activity,
                    place_name,
                    place_id,
                    recommended_time
                )
                VALUES (
                    :content_id,
                    :trip_id,
                    :user_id,
                    :url,
                    :title,
                    :category,
                    :keywords,
                    :area,
                    :activity,
                    :place_name,
                    :place_id,
                    :recommended_time
                )
            """),
            values,
        )

        # -----------------------------------------------------
        # 5-3. 사용자 취향 재계산
        # -----------------------------------------------------

        profile = recalculate(
            db,
            user_id,
        )

    # ---------------------------------------------------------
    # 6. API 응답
    # ---------------------------------------------------------

    return {
        "content_id":
            content_id,

        "trip_id":
            trip_id,

        "user_id":
            user_id,

        "analysis": {
            **analysis.model_dump(
                mode="json"
            ),

            "user_id":
                user_id,

            "title":
                title,

            "url":
                canonical,

            "place_id":
                place_id,

            "place_verified":
                place_id is not None,
        },

        "preference_profile":
            profile,
    }


def list_shortforms(
    db: Session,
    trip_id: str,
) -> list[dict]:
    """
    여행의 저장된 숏폼과
    Kakao에서 검증된 장소 정보를 함께 반환한다.
    """

    require(
        db,
        "trips",
        trip_id,
    )

    rows = db.execute(
        text("""
            SELECT
                c.*,
                u.name
                    AS user_name,

                p.place_name
                    AS verified_place_name,

                p.address
                    AS place_address,

                p.latitude
                    AS place_latitude,

                p.longitude
                    AS place_longitude

            FROM shortform_contents c

            JOIN users u
                ON u.user_id =
                   c.user_id

            LEFT JOIN places p
                ON p.place_id =
                   c.place_id

            WHERE
                c.trip_id=:id

            ORDER BY
                c.created_at,
                c.content_id
        """),
        {
            "id": trip_id,
        },
    ).mappings()

    result = []

    for item in rows:
        data = dict(
            item
        )

        data["keywords"] = decode(
            data.get(
                "keywords"
            ),
            [],
        )

        data["place_verified"] = (
            data.get(
                "place_id"
            )
            is not None
        )

        if (
            data.get(
                "place_latitude"
            )
            is not None
        ):
            data[
                "place_latitude"
            ] = float(
                data[
                    "place_latitude"
                ]
            )

        if (
            data.get(
                "place_longitude"
            )
            is not None
        ):
            data[
                "place_longitude"
            ] = float(
                data[
                    "place_longitude"
                ]
            )

        result.append(
            data
        )

    return result

def update_shortform(
    db: Session,
    trip_id: str,
    content_id: str,
    patch: dict,
) -> dict:
    """사용자가 AI 분석 결과를 수정하고 취향을 다시 계산한다."""

    allowed_categories = {
        "cafe",
        "food",
        "exhibition",
        "shopping",
        "outdoor",
        "activity",
        "sightseeing",
        "nightlife",
        "accommodation",
        "other",
    }

    allowed_times = {
        "morning",
        "afternoon",
        "evening",
        "night",
    }

    if "category" in patch:
        category = patch["category"]

        if (
            category is None
            or category not in allowed_categories
        ):
            raise ServiceError(
                400,
                "올바른 카테고리를 입력해주세요.",
            )

    if "recommended_time" in patch:
        value = patch["recommended_time"]

        if (
            value is not None
            and value not in allowed_times
        ):
            raise ServiceError(
                400,
                "추천 시간대가 올바르지 않습니다.",
            )

    if "keywords" in patch:
        keywords = patch["keywords"]

        if (
            keywords is None
            or not isinstance(keywords, list)
            or any(
                not isinstance(keyword, str)
                or not keyword.strip()
                for keyword in keywords
            )
        ):
            raise ServiceError(
                400,
                "태그 형식이 올바르지 않습니다.",
            )

        patch["keywords"] = [
            keyword.strip()
            for keyword in keywords
        ]

    with transaction(db):
        require(
            db,
            "trips",
            trip_id,
            lock=True,
        )

        content = row(
            db,
            """
            SELECT *
            FROM shortform_contents
            WHERE
                content_id=:content_id
                AND trip_id=:trip_id
            """,
            content_id=content_id,
            trip_id=trip_id,
        )

        if not content:
            raise ServiceError(
                404,
                "콘텐츠를 찾을 수 없습니다.",
            )

        user_id = content["user_id"]

        require(
            db,
            "users",
            user_id,
            lock=True,
        )

        new_place_name = (
            patch.get(
                "place_name",
                content.get("place_name"),
            )
        )

        if isinstance(
            new_place_name,
            str,
        ):
            new_place_name = (
                new_place_name.strip()
                or None
            )

        new_category = patch.get(
            "category",
            content.get("category"),
        )

        new_keywords = patch.get(
            "keywords",
            decode(
                content.get("keywords"),
                [],
            ),
        )

        new_recommended_time = patch.get(
            "recommended_time",
            content.get("recommended_time"),
        )

        # 장소명을 사용자가 수정했으면 Kakao 재검증
        place_id = content.get(
            "place_id"
        )

        old_place_name = content.get(
            "place_name"
        )

        if (
            new_place_name
            != old_place_name
        ):
            place_id = None

            if new_place_name:
                verified_place = (
                    verify_named_place(
                        content.get("area"),
                        new_place_name,
                    )
                )

                if verified_place:
                    place_id = (
                        stable_place_db_id(
                            verified_place
                        )
                    )

                    address = (
                        verified_place.get(
                            "address",
                            "",
                        )
                        or ""
                    )

                    region = (
                        content.get("area")
                        or (
                            address.split()[0]
                            if address
                            else "unknown"
                        )
                    )

                    place_values = {
                        "place_id":
                            place_id,

                        "place_name":
                            verified_place[
                                "name"
                            ],

                        "category":
                            verified_place[
                                "category"
                            ],

                        "latitude":
                            verified_place[
                                "lat"
                            ],

                        "longitude":
                            verified_place[
                                "lng"
                            ],

                        "address":
                            address,

                        "region":
                            region,
                    }

                    db.execute(
                        text("""
                            INSERT INTO places (
                                place_id,
                                place_name,
                                category,
                                latitude,
                                longitude,
                                address,
                                region
                            )
                            VALUES (
                                :place_id,
                                :place_name,
                                :category,
                                :latitude,
                                :longitude,
                                :address,
                                :region
                            )
                            ON DUPLICATE KEY UPDATE
                                place_name=:place_name,
                                category=:category,
                                latitude=:latitude,
                                longitude=:longitude,
                                address=:address,
                                region=:region
                        """),
                        place_values,
                    )

        db.execute(
            text("""
                UPDATE shortform_contents
                SET
                    place_name=:place_name,
                    place_id=:place_id,
                    category=:category,
                    keywords=:keywords,
                    recommended_time=:recommended_time
                WHERE
                    content_id=:content_id
                    AND trip_id=:trip_id
            """),
            {
                "place_name":
                    new_place_name,

                "place_id":
                    place_id,

                "category":
                    new_category,

                "keywords":
                    json.dumps(
                        new_keywords,
                        ensure_ascii=False,
                    ),

                "recommended_time":
                    new_recommended_time,

                "content_id":
                    content_id,

                "trip_id":
                    trip_id,
            },
        )

        profile = recalculate(
            db,
            user_id,
        )

    updated = next(
        (
            item
            for item
            in list_shortforms(
                db,
                trip_id,
            )
            if item["content_id"]
            == content_id
        ),
        None,
    )

    if updated is None:
        raise ServiceError(
            404,
            "수정된 콘텐츠를 찾을 수 없습니다.",
        )

    return {
        "status": "success",
        "data": updated,
        "preference_profile": profile,
    }

def delete_shortform(
    db: Session,
    trip_id: str,
    content_id: str,
) -> dict:
    """숏폼 삭제 후 해당 사용자의 취향을 다시 계산한다."""

    with transaction(db):

        require(
            db,
            "trips",
            trip_id,
            lock=True,
        )

        content = row(
            db,
            """
            SELECT user_id
            FROM shortform_contents
            WHERE
                content_id=:id
                AND trip_id=:trip
            """,
            id=content_id,
            trip=trip_id,
        )

        if not content:
            raise ServiceError(
                404,
                "콘텐츠를 찾을 수 없습니다.",
            )

        require(
            db,
            "users",
            content["user_id"],
            lock=True,
        )

        db.execute(
            text("""
                DELETE FROM shortform_contents
                WHERE content_id=:id
            """),
            {
                "id": content_id,
            },
        )

        profile = recalculate(
            db,
            content["user_id"],
        )

    return {
        "status": "success",
        "preference_profile":
            profile,
    }