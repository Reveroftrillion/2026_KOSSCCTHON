"""Adapt Backend UUIDs to AI2, persist candidate FKs and full itinerary snapshots."""
import copy
import json
import re
import uuid
from datetime import date, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from ai.itinerary_planner.ai2_pipeline import run_ai2_pipeline
from backend.services.common import ServiceError, decode, require, row, transaction
from backend.services.preference_service import trip_profiles
from backend.services.place_service import search_places


def time_text(value) -> str:
    """Support MySQL TIME timedelta, datetime.time and SQLite text."""
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        if seconds < 0 or seconds >= 86400 or seconds % 60:
            raise ServiceError(400, "시간은 같은 날의 분 단위여야 합니다.")
        return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}"
    raw = str(value)
    if not re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d(?::00)?", raw):
        raise ServiceError(400, "여행 시간이 올바르지 않습니다.")
    parts = raw.split(":")
    return f"{int(parts[0]):02d}:{parts[1]}"


def conditions_for(trip: dict, target: date, user_conditions: list[str]) -> dict:
    """Validate the requested day and convert trip DB time fields to AI2 format."""
    if not date.fromisoformat(str(trip["start_date"])) <= target <= date.fromisoformat(str(trip["end_date"])):
        raise ServiceError(400, "여행 기간 밖의 날짜입니다.")
    start, end = time_text(trip["day_start_time"]), time_text(trip["day_end_time"])
    if start >= end:
        raise ServiceError(400, "종료 시간은 시작 시간보다 늦어야 합니다.")
    return {"region": trip["region"], "date": target.isoformat(), "time": f"{start} ~ {end}", "user_conditions": user_conditions}


def restore_ids(result: dict, ids: dict[int, str]) -> dict:
    """Translate all AI2 identity fields and generated user references back to UUIDs."""
    result = copy.deepcopy(result)
    for key in ("preference_coverage", "preference_reflection"):
        result[key] = {ids[int(user)]: value for user, value in result[key].items()}
    for stop in result["schedule"]:
        stop["user_scores"] = {ids[int(user)]: score for user, score in stop["user_scores"].items()}
        stop["related_users"] = [ids[int(user)] for user in stop["related_users"]]
        stop["reason"] = re.sub(r"(\d+)번 사용자", lambda match: f"{ids[int(match[1])]} 사용자", stop["reason"])
    return result


def persist_places(db: Session, places: list[dict], region: str) -> dict[str, str]:
    """Namespace provider IDs into stable DB UUIDs and upsert actual FK rows."""
    mapping = {}
    for place in places:
        source_id = place["place_id"]
        db_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"tripclip:{place.get('source', 'provider')}:{source_id}"))
        mapping[source_id] = db_id
        values = {"id": db_id, "name": place["name"], "category": place["category"], "lat": place.get("lat"), "lng": place.get("lng"), "region": region, "address": place.get("address")}
        # MySQL upsert avoids concurrent INSERT races across different trips.
        if db.bind.dialect.name == "mysql":
            db.execute(text("""INSERT INTO places (place_id,place_name,category,latitude,longitude,region,address)
                VALUES (:id,:name,:category,:lat,:lng,:region,:address) ON DUPLICATE KEY UPDATE
                place_name=:name,category=:category,latitude=:lat,longitude=:lng,region=:region,address=COALESCE(:address,address)"""), values)
        elif row(db, "SELECT place_id FROM places WHERE place_id=:id", id=db_id):
            db.execute(text("UPDATE places SET place_name=:name,category=:category,latitude=:lat,longitude=:lng,region=:region,address=COALESCE(:address,address) WHERE place_id=:id"), values)
        else:
            db.execute(text("INSERT INTO places (place_id,place_name,category,latitude,longitude,region,address) VALUES (:id,:name,:category,:lat,:lng,:region,:address)"), values)
    return mapping


def generate_and_save(db: Session, trip_id: str, target: date, user_conditions: list[str]) -> dict:
    """Compute outside DB transaction; serialize and atomically replace a trip/day result."""
    trip = require(db, "trips", trip_id)
    profiles = trip_profiles(db, trip_id)
    conditions = conditions_for(trip, target, user_conditions)
    db.rollback()
    try:
        places = search_places(trip["region"], profiles)
        ids = {index: profile["user_id"] for index, profile in enumerate(profiles, 1)}
        adapted = [{**profile, "user_id": index} for index, profile in enumerate(profiles, 1)]
        result = restore_ids(run_ai2_pipeline(conditions, profiles=adapted, place_candidates=places), ids)
        source = places[0].get("source", "provider") if places else "mock"
    except ServiceError:
        raise
    except Exception:
        raise ServiceError(502, "장소 조회 또는 일정 생성에 실패했습니다.") from None
    with transaction(db):
        current = require(db, "trips", trip_id, lock=True)
        # Lock member user rows in stable order before validating the preference snapshot.
        for user in sorted(ids.values()):
            require(db, "users", user, lock=True)
        if conditions_for(current, target, user_conditions) != conditions or trip_profiles(db, trip_id) != profiles:
            raise ServiceError(409, "여행 또는 취향 정보가 변경되었습니다. 다시 생성해주세요.")
        selected_ids = {stop["place_id"] for stop in result["schedule"]}
        mapping = persist_places(db, [p for p in places if p["place_id"] in selected_ids], trip["region"])
        candidates = {p["place_id"]: p for p in places}
        for stop in result["schedule"]:
            place = candidates[stop["place_id"]]
            stop.update(latitude=place.get("lat"), longitude=place.get("lng"), address=place.get("address"))
            stop["place_id"] = mapping[stop["place_id"]]
        day = (target - date.fromisoformat(str(current["start_date"]))).days + 1
        existing = row(db, "SELECT itinerary_id FROM trip_itineraries WHERE trip_id=:trip AND day_number=:day", trip=trip_id, day=day)
        itinerary_id = existing["itinerary_id"] if existing else str(uuid.uuid4())
        result.update(itinerary_id=itinerary_id, trip_id=trip_id, day_number=day, place_source=source)
        values = {"id": itinerary_id, "trip": trip_id, "day": day, "summary": result["summary"],
                  "coverage": json.dumps(result["preference_coverage"]), "reflection": json.dumps(result["preference_reflection"]),
                  "snapshot": json.dumps(result, ensure_ascii=False)}
        if existing:
            db.execute(text("DELETE FROM itinerary_places WHERE itinerary_id=:id"), values)
            db.execute(text("UPDATE trip_itineraries SET summary=:summary,preference_coverage=:coverage,preference_reflection=:reflection,result_json=:snapshot,updated_at=CURRENT_TIMESTAMP WHERE itinerary_id=:id"), values)
        else:
            db.execute(text("INSERT INTO trip_itineraries (itinerary_id,trip_id,day_number,summary,preference_coverage,preference_reflection,result_json) VALUES (:id,:trip,:day,:summary,:coverage,:reflection,:snapshot)"), values)
        for index, stop in enumerate(result["schedule"]):
            end = result["schedule"][index + 1]["time"] if index + 1 < len(result["schedule"]) else conditions["time"].split(" ~ ")[1]
            db.execute(text("""INSERT INTO itinerary_places (itinerary_place_id,itinerary_id,place_id,sequence_order,
                visit_start_time,visit_end_time,related_users,notes,user_scores,group_score)
                VALUES (:id,:itinerary,:place,:sequence,:start,:end,:related,:notes,:scores,:score)"""),
                {"id": str(uuid.uuid4()), "itinerary": itinerary_id, "place": stop["place_id"], "sequence": index + 1,
                 "start": stop["time"] + ":00", "end": end + ":00", "related": json.dumps(stop["related_users"]),
                 "notes": stop["reason"], "scores": json.dumps(stop["user_scores"]), "score": stop["group_score"]})
    return result


def get_itineraries(db: Session, trip_id: str, itinerary_id: str | None = None) -> list[dict]:
    """Return saved snapshots; legacy pre-migration rows are explicitly marked."""
    require(db, "trips", trip_id)
    sql = "SELECT * FROM trip_itineraries WHERE trip_id=:trip"
    if itinerary_id:
        sql += " AND itinerary_id=:id"
    rows = db.execute(text(sql + " ORDER BY day_number"), {"trip": trip_id, "id": itinerary_id}).mappings().all()
    if itinerary_id and not rows:
        raise ServiceError(404, "일정을 찾을 수 없습니다.")
    results = [decode(item["result_json"], {"itinerary_id": item["itinerary_id"], "summary": item["summary"], "legacy": True}) for item in rows]
    # Older snapshots lack map fields. Fill only missing fields; preserve generation-time data.
    locations = db.execute(text("""SELECT DISTINCT p.place_id,p.latitude,p.longitude,p.address
        FROM places p JOIN itinerary_places ip ON ip.place_id=p.place_id
        JOIN trip_itineraries ti ON ti.itinerary_id=ip.itinerary_id WHERE ti.trip_id=:trip"""),
        {"trip": trip_id}).mappings()
    by_id = {p["place_id"]: p for p in locations}
    for result in results:
        for stop in result.get("schedule", []):
            place = by_id.get(stop["place_id"], {})
            for key in ("latitude", "longitude", "address"):
                value = place.get(key)
                stop.setdefault(key, float(value) if key != "address" and value is not None else value)
    return results
