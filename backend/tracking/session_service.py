import time
import uuid
from typing import Dict, List, Optional

from django.conf import settings
from django.utils import timezone

from .redis_client import get_redis

SESSION_KEY_PREFIX = "session:"
ONLINE_USERS_KEY = "online_users"
ACTIVITY_SCORE_KEY = "user_activity_score"
SESSION_EXPIRE_SUFFIX = ":expire"


def _session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def _expire_key(session_id: str) -> str:
    return f"{_session_key(session_id)}{SESSION_EXPIRE_SUFFIX}"


def _now_ts() -> int:
    return int(timezone.now().timestamp())


def create_session(user_id: str) -> Dict:
    r = get_redis()
    session_id = str(uuid.uuid4())
    ts = _now_ts()
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "login_time": ts,
        "last_activity": ts,
        "status": "active",
    }
    session_key = _session_key(session_id)
    expire_key = _expire_key(session_id)

    r.hset(session_key, mapping=session_data)
    r.expire(session_key, settings.SESSION_TTL_SECONDS)
    r.set(expire_key, 1, ex=settings.SESSION_TTL_SECONDS)
    r.sadd(ONLINE_USERS_KEY, user_id)

    if settings.ACTIVITY_SCORE_ENABLED:
        # initialize score with a baseline (login counts as 1 action)
        r.zadd(ACTIVITY_SCORE_KEY, {user_id: 1})
    return session_data


def refresh_session(session_id: str) -> None:
    r = get_redis()
    session_key = _session_key(session_id)
    expire_key = _expire_key(session_id)
    ttl = settings.SESSION_TTL_SECONDS
    r.expire(session_key, ttl)
    r.set(expire_key, 1, ex=ttl)


def update_activity(session_id: str) -> Optional[Dict]:
    r = get_redis()
    session_key = _session_key(session_id)
    if not r.exists(session_key):
        return None

    ts = _now_ts()
    r.hset(session_key, "last_activity", ts)
    refresh_session(session_id)

    user_id = r.hget(session_key, "user_id")
    if user_id:
        r.sadd(ONLINE_USERS_KEY, user_id)
        if settings.ACTIVITY_SCORE_ENABLED:
            # increment score by 1 to track engagement
            r.zincrby(ACTIVITY_SCORE_KEY, 1, user_id)
    return r.hgetall(session_key)


def end_session(session_id: str) -> Optional[Dict]:
    r = get_redis()
    session_key = _session_key(session_id)
    expire_key = _expire_key(session_id)
    if not r.exists(session_key):
        return None
    data = r.hgetall(session_key)
    user_id = data.get("user_id")
    r.delete(session_key)
    r.delete(expire_key)
    if user_id:
        r.srem(ONLINE_USERS_KEY, user_id)
    return data


def get_session(session_id: str) -> Optional[Dict]:
    r = get_redis()
    session_key = _session_key(session_id)
    if not r.exists(session_key):
        return None
    return r.hgetall(session_key)


def get_online_users() -> List[str]:
    r = get_redis()
    online = set(r.smembers(ONLINE_USERS_KEY))
    active_sessions = get_active_sessions()
    active_users = {s.get("user_id") for s in active_sessions if s.get("user_id")}
    stale = online - active_users
    if stale:
        r.srem(ONLINE_USERS_KEY, *stale)
    return list(active_users)


def _is_session_key(key: str) -> bool:
    return key.startswith(SESSION_KEY_PREFIX) and not key.endswith(SESSION_EXPIRE_SUFFIX)


def get_active_sessions() -> List[Dict]:
    r = get_redis()
    sessions: List[Dict] = []
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match=f"{SESSION_KEY_PREFIX}*")
        for key in keys:
            if not _is_session_key(key):
                continue
            data = r.hgetall(key)
            if data:
                sessions.append(data)
        if cursor == 0:
            break
    return sessions


def get_active_sessions_summary() -> Dict:
    sessions = get_active_sessions()
    online_users = get_online_users()
    last_activity_per_user: Dict[str, int] = {}
    for session in sessions:
        user_id = session.get("user_id")
        try:
            last_activity = int(session.get("last_activity", 0))
        except (TypeError, ValueError):
            last_activity = 0
        if user_id:
            last_activity_per_user[user_id] = max(last_activity_per_user.get(user_id, 0), last_activity)
    summary = {
        "total_active_sessions": len(sessions),
        "online_users": online_users,
        "last_activity_per_user": last_activity_per_user,
        "sessions": sessions,
    }
    return summary


def get_activity_leaderboard(limit: int = 50) -> List[Dict]:
    if not settings.ACTIVITY_SCORE_ENABLED:
        return []
    r = get_redis()
    leaderboard = r.zrevrange(ACTIVITY_SCORE_KEY, 0, limit - 1, withscores=True)
    return [
        {"user_id": user_id, "score": score}
        for user_id, score in leaderboard
    ]
