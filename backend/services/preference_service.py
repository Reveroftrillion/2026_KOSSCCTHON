"""AI1 adapter and transactional SQL-backed content/preference persistence."""

import json
import uuid
from sqlalchemy import text
from sqlalchemy.orm import Session
from ai.preference_analyzer import analyze_youtube_url, calculate_preferences
from ai.preference_analyzer.metadata_fetcher import extract_youtube_video_id, MetadataError
from ai.preference_analyzer.schemas import AnalyzedContent
from backend.services.common import ServiceError, decode, member, require, row, transaction


def ai_user_id(user_id: str) -> int:
    """Injectively encode the Backend ID as a positive, request-internal AI integer."""
    return int.from_bytes(user_id.encode("utf-8"), "big") + 1


def get_profile(db: Session, user_id: str) -> dict:
    """Expose persistent preferences using the Backend UUID, never the AI integer."""
    require(db, "users", user_id)
    saved = row(db, "SELECT category_scores,tag_scores FROM user_preferences WHERE user_id=:id", id=user_id) or {}
    return {"user_id": user_id, "category_preferences": decode(saved.get("category_scores"), {}),
            "keyword_preferences": decode(saved.get("tag_scores"), {})}


def trip_profiles(db: Session, trip_id: str) -> list[dict]:
    """Include all current members, even those without content."""
    require(db, "trips", trip_id)
    ids = db.execute(text("SELECT user_id FROM trip_members WHERE trip_id=:id ORDER BY user_id"), {"id": trip_id}).scalars().all()
    return [get_profile(db, user_id) for user_id in ids]


def recalculate(db: Session, user_id: str) -> dict:
    """Recalculate all-trip history with AI1 semantics; caller owns transaction/user lock."""
    rows = db.execute(text("SELECT category,keywords FROM shortform_contents WHERE user_id=:id"), {"id": user_id}).mappings()
    contents = [AnalyzedContent(category=item["category"], keywords=decode(item["keywords"], [])) for item in rows]
    profile = calculate_preferences(ai_user_id(user_id), contents).model_dump()
    profile["user_id"] = user_id
    values = {"user": user_id, "categories": json.dumps(profile["category_preferences"]), "tags": json.dumps(profile["keyword_preferences"])}
    if row(db, "SELECT preference_id FROM user_preferences WHERE user_id=:id", id=user_id):
        db.execute(text("UPDATE user_preferences SET category_scores=:categories,tag_scores=:tags,updated_at=CURRENT_TIMESTAMP WHERE user_id=:user"), values)
    else:
        db.execute(text("INSERT INTO user_preferences (preference_id,user_id,category_scores,tag_scores) VALUES (:id,:user,:categories,:tags)"), {**values, "id": str(uuid.uuid4())})
    return profile


def check_duplicate(db: Session, trip_id: str, user_id: str, url: str) -> None:
    """Reject a canonical URL already saved by this member in this trip."""
    if row(db, "SELECT content_id FROM shortform_contents WHERE trip_id=:trip AND user_id=:user AND url=:url", trip=trip_id, user=user_id, url=url):
        raise ServiceError(409, "이미 저장한 숏폼입니다.")


def save_shortform(db: Session, trip_id: str, user_id: str, url: str) -> dict:
    """Analyze outside the write transaction, then atomically persist content and scores."""
    try:
        video_id = extract_youtube_video_id(url)
    except MetadataError:
        raise ServiceError(400, "올바른 YouTube URL을 입력해주세요.") from None
    canonical = f"https://www.youtube.com/watch?v={video_id}"
    member(db, trip_id, user_id)
    check_duplicate(db, trip_id, user_id, canonical)
    db.rollback()  # release validation reads before external calls
    try:
        result = analyze_youtube_url(ai_user_id(user_id), canonical)
        analysis = AnalyzedContent.model_validate(result["analysis"])
        title = result["metadata"]["title"]
        if not isinstance(title, str) or not title.strip() or len(title) > 500:
            raise ValueError("Invalid metadata title")
        for value, limit in ((analysis.area, 100), (analysis.activity, 255), (analysis.place_name, 255)):
            if value and len(value) > limit:
                raise ValueError("Analysis field too long")
    except Exception:
        raise ServiceError(502, "숏폼 분석 또는 메타데이터 수집에 실패했습니다.") from None
    content_id = str(uuid.uuid4())
    with transaction(db):
        require(db, "trips", trip_id, lock=True)
        require(db, "users", user_id, lock=True)
        member(db, trip_id, user_id)
        check_duplicate(db, trip_id, user_id, canonical)
        values = analysis.model_dump(mode="json")
        values.update(content_id=content_id, trip_id=trip_id, user_id=user_id, url=canonical, title=title,
                      keywords=json.dumps(analysis.keywords, ensure_ascii=False))
        db.execute(text("""INSERT INTO shortform_contents
            (content_id,trip_id,user_id,url,title,category,keywords,area,activity,place_name,recommended_time)
            VALUES (:content_id,:trip_id,:user_id,:url,:title,:category,:keywords,:area,:activity,:place_name,:recommended_time)"""), values)
        profile = recalculate(db, user_id)
    return {"content_id": content_id, "trip_id": trip_id, "user_id": user_id,
            "analysis": {**analysis.model_dump(mode="json"), "user_id": user_id, "title": title, "url": canonical},
            "preference_profile": profile}


def list_shortforms(db: Session, trip_id: str) -> list[dict]:
    """List stored content with user names and decoded keywords."""
    require(db, "trips", trip_id)
    rows = db.execute(text("SELECT c.*,u.name AS user_name FROM shortform_contents c JOIN users u ON u.user_id=c.user_id WHERE c.trip_id=:id ORDER BY c.created_at,c.content_id"), {"id": trip_id}).mappings()
    return [{**dict(item), "keywords": decode(item["keywords"], [])} for item in rows]


def delete_shortform(db: Session, trip_id: str, content_id: str) -> dict:
    """Delete and recalculate atomically, including the empty-history case."""
    with transaction(db):
        require(db, "trips", trip_id, lock=True)
        content = row(db, "SELECT user_id FROM shortform_contents WHERE content_id=:id AND trip_id=:trip", id=content_id, trip=trip_id)
        if not content:
            raise ServiceError(404, "콘텐츠를 찾을 수 없습니다.")
        require(db, "users", content["user_id"], lock=True)
        db.execute(text("DELETE FROM shortform_contents WHERE content_id=:id"), {"id": content_id})
        profile = recalculate(db, content["user_id"])
    return {"status": "success", "preference_profile": profile}
