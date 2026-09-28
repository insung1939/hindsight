"""YouTube Data API v3 어댑터. 출처: https://developers.google.com/youtube/v3 (수업 제공 자료).
쿼터: 하루 10,000 유닛. 여기서 쓰는 호출은 전부 1 유닛(channels.list · playlistItems.list · videos.list)이고
search.list(100 유닛)는 쓰지 않는다. 채널 20개 × 1년 백필 ≈ 수백 유닛."""
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from hs_common.settings import env

BASE = "https://www.googleapis.com/youtube/v3"


def _key() -> str:
    key = env("YOUTUBE_API_KEY")
    if not key:
        raise HTTPException(409, "YOUTUBE_API_KEY 가 없습니다. services/youtube/.env 에 넣으세요")
    return key


def _get(path: str, **params) -> dict:
    key = _key()
    r = httpx.get(f"{BASE}/{path}", params={**params, "key": key}, timeout=20)
    if r.status_code >= 400:
        # 오류 메시지·URL 에 키가 섞여 나가지 않게 가린다
        try:
            err = r.json().get("error", {})
            reason = ", ".join(d.get("reason", "") for d in err.get("errors", [])) or err.get("status", "")
            msg = f"{err.get('message', '')} ({reason})"
        except Exception:
            msg = r.text[:200]
        raise HTTPException(502 if r.status_code in (403, 429) else 400,
                            f"YouTube API {r.status_code}: {msg.replace(key, '***')}")
    return r.json()


def channel_by_handle(handle: str) -> dict:
    """@핸들 → 채널 id·제목·업로드 재생목록·구독자 수. 1 유닛."""
    h = handle if handle.startswith("@") else "@" + handle
    data = _get("channels", part="snippet,contentDetails,statistics", forHandle=h)
    items = data.get("items") or []
    if not items:
        raise HTTPException(404, f"채널 {h} 을 찾을 수 없습니다")
    c = items[0]
    return {"channel_id": c["id"], "handle": h, "title": c["snippet"]["title"],
            "uploads_playlist_id": c["contentDetails"]["relatedPlaylists"]["uploads"],
            "subscriber_count": int(c["statistics"].get("subscriberCount", 0) or 0)}


def uploads_since(playlist_id: str, since: datetime, max_pages: int = 40) -> list[dict]:
    """업로드 재생목록을 최신순으로 넘기며 since 이전 영상이 나오면 멈춘다. 페이지당 1 유닛(50개)."""
    out, token, pages = [], None, 0
    while pages < max_pages:
        params = {"part": "snippet,contentDetails", "playlistId": playlist_id, "maxResults": 50}
        if token:
            params["pageToken"] = token
        data = _get("playlistItems", **params)
        pages += 1
        stop = False
        for it in data.get("items", []):
            sn = it["snippet"]
            published = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
            if published < since:
                stop = True
                break
            out.append({"video_id": it["contentDetails"]["videoId"], "title": sn["title"],
                        "description": sn.get("description", "")[:2000], "published_at": published})
        token = data.get("nextPageToken")
        if stop or not token:
            break
    return out


def view_counts(video_ids: list[str]) -> dict[str, int]:
    """조회수. 50개당 1 유닛."""
    out = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        data = _get("videos", part="statistics", id=",".join(chunk))
        for v in data.get("items", []):
            out[v["id"]] = int(v["statistics"].get("viewCount", 0) or 0)
    return out
