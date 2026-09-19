"""Bounded Kakao Local search and explicit mock mode for AI2 candidates."""

import json
import math
import os
import re
import uuid
from pathlib import Path

import httpx

from backend.services.common import ServiceError


CATEGORY_MAP = {
    "카페": "cafe",
    "음식점": "food",
    "식당": "food",
    "미술관": "exhibition",
    "전시": "exhibition",
    "문화시설": "exhibition",

    "쇼핑": "shopping",
    "복합쇼핑몰": "shopping",
    "백화점": "shopping",
    "아울렛": "shopping",
    "쇼핑센터": "shopping",

    "공원": "outdoor",
    "관광명소": "sightseeing",
    "숙박": "accommodation",
    "술집": "nightlife",
    "주점": "nightlife",
    "스포츠": "activity",
}


NON_VISITABLE_SHOPPING_LABELS = {
    "통신판매",
    "인터넷쇼핑몰",
}


CATEGORIES = {
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


GROUP_CODES = {
    "CE7": "cafe",
    "FD6": "food",
    "CT1": "exhibition",
    "AT4": "sightseeing",
    "AD5": "accommodation",
    "MT1": "shopping",
}


SEARCH_TERMS = {
    "cafe": "카페",
    "food": "맛집",
    "exhibition": "전시",
    "shopping": "쇼핑",
    "outdoor": "공원",
    "activity": "체험",
    "sightseeing": "관광명소",
    "nightlife": "술집",
    "accommodation": "숙박",
    "other": "가볼만한곳",
}


TOP_CATEGORIES = 4
RESULTS_PER_QUERY = 5
MAX_CANDIDATES = 20

KAKAO_URL = (
    "https://dapi.kakao.com/v2/local/search/keyword.json"
)


def normalize_category(
    category: str,
) -> str:
    """Translate provider labels to the existing AI2 vocabulary."""

    value = (
        category
        .strip()
        .lower()
    )

    return CATEGORY_MAP.get(
        value,
        value
        if value in CATEGORIES
        else "other",
    )


def kakao_category(
    category_name: str,
    group_code: str = "",
) -> str:
    """Prefer specific category labels over broad Kakao group codes."""

    for label in reversed(
        category_name.split(">")
    ):
        normalized = normalize_category(
            label
        )

        if normalized != "other":
            return normalized

    return GROUP_CODES.get(
        group_code,
        "other",
    )


def search_queries(
    region: str,
    profiles: list[dict],
) -> list[str]:
    """
    Rank category means.
    Missing scores count as zero.
    """

    totals = {}

    for profile in profiles:
        for category, score in (
            profile
            .get(
                "category_preferences",
                {},
            )
            .items()
        ):
            if (
                category in SEARCH_TERMS
                and isinstance(
                    score,
                    (int, float),
                )
                and math.isfinite(score)
                and score > 0
            ):
                totals[category] = (
                    totals.get(
                        category,
                        0,
                    )
                    + score
                    / max(
                        1,
                        len(profiles),
                    )
                )

    categories = sorted(
        totals,
        key=lambda category: (
            -totals[category],
            category,
        ),
    )[:TOP_CATEGORIES]

    return [
        f"{region.strip()} {SEARCH_TERMS[category]}"
        for category in (
            categories
            or ["sightseeing"]
        )
    ]


def is_non_visitable_place(
    document: dict,
) -> bool:
    """Filter places that are not useful as offline itinerary stops."""

    category_name = document.get(
        "category_name",
        "",
    )

    labels = {
        label.strip()
        for label in category_name.split(">")
        if label.strip()
    }

    return bool(
        labels
        & NON_VISITABLE_SHOPPING_LABELS
    )


def normalize_kakao_place(
    document: dict,
) -> dict:
    """
    Normalize a Kakao Local result.

    Only provider facts are used.
    Mood or amenities are not inferred.
    """

    place_id = document["id"]
    name = document["place_name"]

    if (
        not isinstance(
            place_id,
            str,
        )
        or not place_id
        or not isinstance(
            name,
            str,
        )
        or not 0 < len(name) <= 200
    ):
        raise ValueError(
            "Invalid place identity"
        )

    lat = float(
        document["y"]
    )

    lng = float(
        document["x"]
    )

    if (
        not math.isfinite(lat)
        or not math.isfinite(lng)
        or not -90 <= lat <= 90
        or not -180 <= lng <= 180
    ):
        raise ValueError(
            "Invalid coordinates"
        )

    labels = document.get(
        "category_name",
        "",
    )

    category = kakao_category(
        labels,
        document.get(
            "category_group_code",
            "",
        ),
    )

    keywords = list(
        dict.fromkeys(
            [category]
            + [
                label.strip()
                for label
                in labels.split(">")
                if label.strip()
            ]
        )
    )

    address = (
        document.get(
            "road_address_name"
        )
        or document.get(
            "address_name"
        )
        or ""
    )

    return {
        "place_id": place_id,
        "name": name,
        "category": category,
        "keywords": keywords,
        "lat": lat,
        "lng": lng,
        "address": address,
    }


def normalize_place_name(
    value: str,
) -> str:
    """
    장소명 비교용으로
    공백과 일부 구두점을 제거한다.

    예:
    '이리에 라멘'
    → '이리에라멘'
    """

    return re.sub(
        r"[\s·・'\"“”‘’()\[\]{}\-_/]+",
        "",
        value,
    ).casefold()


def normalize_branch_place_name(
    value: str,
) -> str:
    """
    Kakao 장소명의 지점 표현을 제거해
    AI 장소명과 비교하기 쉽게 만든다.

    예:
    담택 본점 -> 담택
    """

    normalized = (
        normalize_place_name(
            value
        )
    )

    suffixes = (
        "본점",
        "직영점",
        "본관",
    )

    for suffix in suffixes:
        if (
            normalized.endswith(
                suffix
            )
            and len(normalized)
            > len(suffix)
        ):
            return normalized[
                :-len(suffix)
            ]

    return normalized


def stable_place_db_id(
    place: dict,
) -> str:
    """
    Kakao provider ID를
    TripClip 내부 UUID로 안정적으로 변환한다.
    """

    source = place.get(
        "source",
        "kakao",
    )

    provider_id = place[
        "place_id"
    ]

    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            (
                f"tripclip:"
                f"{source}:"
                f"{provider_id}"
            ),
        )
    )


def verify_named_place(
    area: str | None,
    place_name: str,
) -> dict | None:
    """
    AI가 추출한 단일 장소명을
    Kakao Local API로 검증한다.

    검색 순서:
    1. 지역 + 장소명
    2. 장소명만

    매칭 순서:
    1. 정규화 후 정확히 같은 이름
    2. 본점/직영점/본관 제거 후 같은 이름
    3. 충분히 긴 이름의 부분 일치가 단 하나일 때만 허용

    검증 실패는 숏폼 저장 자체를 실패시키지 않는다.
    """

    api_key = os.getenv(
        "KAKAO_REST_API_KEY",
        "",
    ).strip()

    if not api_key:
        return None

    clean_name = (
        place_name.strip()
    )

    if not clean_name:
        return None

    target = (
        normalize_place_name(
            clean_name
        )
    )

    target_base = (
        normalize_branch_place_name(
            clean_name
        )
    )

    if not target:
        return None

    queries = []

    if (
        area
        and area.strip()
    ):
        queries.append(
            (
                f"{area.strip()} "
                f"{clean_name}"
            )
        )

    # 지역 정보가 잘못되었거나
    # 검색을 방해하는 경우를 위한 fallback
    queries.append(
        clean_name
    )

    # 중복 검색어 제거
    queries = list(
        dict.fromkeys(
            queries
        )
    )

    try:
        with httpx.Client(
            timeout=10.0,
            headers={
                "Authorization":
                    "KakaoAK "
                    + api_key
            },
        ) as client:

            for query in queries:
                response = client.get(
                    KAKAO_URL,
                    params={
                        "query": query,
                        "page": 1,
                        "size": 10,
                    },
                )

                response.raise_for_status()

                payload = (
                    response.json()
                )

                documents = (
                    payload.get(
                        "documents",
                        [],
                    )
                )

                if not isinstance(
                    documents,
                    list,
                ):
                    continue

                # ---------------------------------------------
                # 1. exact 또는 branch suffix 제거 후 정확 매칭
                # ---------------------------------------------

                for document in documents:

                    candidate_name = (
                        document.get(
                            "place_name",
                            "",
                        )
                    )

                    if not isinstance(
                        candidate_name,
                        str,
                    ):
                        continue

                    candidate = (
                        normalize_place_name(
                            candidate_name
                        )
                    )

                    candidate_base = (
                        normalize_branch_place_name(
                            candidate_name
                        )
                    )

                    matched = (
                        candidate
                        == target
                        or candidate_base
                        == target_base
                    )

                    if not matched:
                        continue

                    try:
                        place = (
                            normalize_kakao_place(
                                document
                            )
                        )

                    except (
                        ValueError,
                        KeyError,
                        TypeError,
                    ):
                        continue

                    place[
                        "source"
                    ] = "kakao"

                    return place

                # ---------------------------------------------
                # 2. 느슨한 부분 일치
                #
                # 너무 짧은 이름은 오탐 위험이 있으므로
                # 이 단계에서는 허용하지 않는다.
                # ---------------------------------------------

                loose_matches = []

                for document in documents:

                    candidate_name = (
                        document.get(
                            "place_name",
                            "",
                        )
                    )

                    if not isinstance(
                        candidate_name,
                        str,
                    ):
                        continue

                    candidate_base = (
                        normalize_branch_place_name(
                            candidate_name
                        )
                    )

                    if (
                        min(
                            len(
                                target_base
                            ),
                            len(
                                candidate_base
                            ),
                        )
                        < 4
                    ):
                        continue

                    if (
                        target_base
                        in candidate_base
                        or candidate_base
                        in target_base
                    ):
                        loose_matches.append(
                            document
                        )

                # 부분 일치 후보가 정확히 하나일 때만 채택
                if (
                    len(
                        loose_matches
                    )
                    == 1
                ):
                    try:
                        place = (
                            normalize_kakao_place(
                                loose_matches[
                                    0
                                ]
                            )
                        )

                    except (
                        ValueError,
                        KeyError,
                        TypeError,
                    ):
                        continue

                    place[
                        "source"
                    ] = "kakao"

                    return place

    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
    ):
        return None

    return None


def search_provider_places(
    region: str,
    profiles: list[dict],
) -> list[dict]:
    """
    Search at most four first pages.
    Provider errors never become mock results.
    """

    candidates = {}

    try:
        with httpx.Client(
            timeout=10.0,
            headers={
                "Authorization":
                    "KakaoAK "
                    + os.environ[
                        "KAKAO_REST_API_KEY"
                    ].strip()
            },
        ) as client:

            for query in (
                search_queries(
                    region,
                    profiles,
                )
            ):
                response = (
                    client.get(
                        KAKAO_URL,
                        params={
                            "query":
                                query,
                            "page":
                                1,
                            "size":
                                RESULTS_PER_QUERY,
                        },
                    )
                )

                if (
                    response.status_code
                    in (
                        429,
                        503,
                    )
                ):
                    raise ServiceError(
                        503,
                        (
                            "Kakao 장소 검색을 "
                            "일시적으로 사용할 수 없습니다."
                        ),
                    )

                response.raise_for_status()

                documents = (
                    response.json()[
                        "documents"
                    ]
                )

                if not isinstance(
                    documents,
                    list,
                ):
                    raise ValueError(
                        "Invalid documents"
                    )

                for document in (
                    documents[
                        :RESULTS_PER_QUERY
                    ]
                ):
                    if (
                        is_non_visitable_place(
                            document
                        )
                    ):
                        continue

                    place = (
                        normalize_kakao_place(
                            document
                        )
                    )

                    candidates.setdefault(
                        place[
                            "place_id"
                        ],
                        place,
                    )

                    if (
                        len(
                            candidates
                        )
                        >= MAX_CANDIDATES
                    ):
                        return list(
                            candidates.values()
                        )

    except ServiceError:
        raise

    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ):
        raise ServiceError(
            502,
            (
                "Kakao 장소 검색에 실패했습니다. "
                "연결 및 provider 설정을 확인해주세요."
            ),
        ) from None

    if not candidates:
        raise ServiceError(
            503,
            (
                "Kakao 검색 결과가 없습니다. "
                "지역 또는 취향 조건을 확인해주세요."
            ),
        )

    return list(
        candidates.values()
    )


def search_places(
    region: str,
    profiles: list[dict],
) -> list[dict]:
    """
    Kakao API key가 있으면 실제 provider를 사용하고,
    없으면 명시적으로 mock 데이터를 사용한다.
    """

    if (
        os.getenv(
            "KAKAO_REST_API_KEY",
            "",
        ).strip()
    ):
        places = (
            search_provider_places(
                region,
                profiles,
            )
        )

        source = "kakao"

    else:
        path = (
            Path(
                __file__
            )
            .resolve()
            .parents[2]
            / "ai"
            / "itinerary_planner"
            / "sample_places.json"
        )

        places = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        source = "mock"

    return [
        {
            **place,
            "category":
                normalize_category(
                    place[
                        "category"
                    ]
                ),
            "source":
                source,
        }
        for place in places
    ]