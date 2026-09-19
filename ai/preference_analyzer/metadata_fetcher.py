"""YouTube Data API 또는 oEmbed로 공개 메타데이터만 수집한다."""

import os
import re
from urllib.parse import parse_qs, urlsplit

import httpx
from pydantic import ValidationError

if __package__:
    from .schemas import YouTubeMetadata
else:
    from schemas import YouTubeMetadata


class MetadataError(ValueError):
    """호출자에게 안전하게 표시할 수 있는 URL/메타데이터 오류."""


def extract_youtube_video_id(url: str) -> str:
    """허용한 YouTube 호스트와 경로에서 11자리 영상 ID를 추출한다."""
    try:
        parsed = urlsplit(url.strip())
        if (parsed.scheme not in ("http", "https") or parsed.username or parsed.password
                or parsed.port not in (None, 80, 443)):
            raise ValueError
        host = parsed.hostname
        path = parsed.path.rstrip("/")
        if host == "youtu.be":
            video_id = path.removeprefix("/")
        elif host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if path.startswith("/shorts/"):
                video_id = path[len("/shorts/"):]
            elif path == "/watch":
                values = parse_qs(parsed.query, keep_blank_values=True).get("v", [])
                if len(values) != 1:
                    raise ValueError
                video_id = values[0]
            else:
                raise ValueError
        else:
            raise ValueError
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError
        return video_id
    except (ValueError, AttributeError, TypeError):
        raise MetadataError("유효한 YouTube shorts, watch?v= 또는 youtu.be URL을 입력해주세요.") from None


def fetch_youtube_metadata(url: str) -> YouTubeMetadata:
    """키가 있으면 Data API, 없으면 oEmbed를 호출한다. 실패 시 MetadataError."""
    video_id = extract_youtube_video_id(url)
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    provider = "YouTube Data API" if api_key else "YouTube oEmbed"
    endpoint = "https://www.googleapis.com/youtube/v3/videos" if api_key else "https://www.youtube.com/oembed"
    params = {"part": "snippet", "id": video_id, "key": api_key} if api_key else {"url": canonical_url, "format": "json"}
    try:
        response = httpx.get(endpoint, params=params, timeout=10.0, follow_redirects=False)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError
        if api_key:
            items = data.get("items", [])
            if not items:
                raise MetadataError("영상을 찾을 수 없습니다. 삭제·비공개 여부와 URL을 확인해주세요.")
            snippet = items[0]["snippet"]
            thumbnails = snippet.get("thumbnails") or {}
            thumbnail = next((thumbnails[size].get("url") for size in
                              ("maxres", "standard", "high", "medium", "default")
                              if thumbnails.get(size, {}).get("url")), None)
            fields = {
                "title": snippet.get("title") or "",
                "description": snippet.get("description") or "",
                "tags": snippet.get("tags") or [],
                "channel_title": snippet.get("channelTitle"), "thumbnail_url": thumbnail,
            }
        else:
            fields = {"title": data.get("title") or "", "channel_title": data.get("author_name"),
                      "thumbnail_url": data.get("thumbnail_url")}
        if not isinstance(fields["title"], str) or not fields["title"].strip():
            raise MetadataError("영상 제목을 얻을 수 없어 분석을 진행할 수 없습니다.")
        return YouTubeMetadata(url=url.strip(), video_id=video_id, **fields)
    except MetadataError:
        raise
    except httpx.TimeoutException:
        raise MetadataError(f"{provider} 요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.") from None
    except httpx.HTTPStatusError as exc:
        raise MetadataError(f"{provider} 요청 실패 (HTTP {exc.response.status_code}). 공개 여부와 API 키·할당량을 확인해주세요.") from None
    except httpx.RequestError:
        raise MetadataError(f"{provider}에 연결할 수 없습니다. 네트워크를 확인해주세요.") from None
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, ValidationError):
        raise MetadataError(f"{provider} 메타데이터 응답 형식이 올바르지 않습니다.") from None
