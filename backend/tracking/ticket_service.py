from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from .redis_client import get_redis


@dataclass
class Ticket:
    ticket_number: int
    creation_time: float
    service_type: str | None
    status: str  # waiting | in_progress | completed

    def to_dict(self) -> dict:
        data = asdict(self)
        # Format convenience: add iso time
        data["creation_time_iso"] = datetime.fromtimestamp(self.creation_time, tz=timezone.utc).isoformat()
        return data


def _today_key() -> str:
    # UTC-based day boundary
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ttl_until_tomorrow() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(3600, int((tomorrow - now).total_seconds()))


def _keys(day: str) -> dict:
    base = f"tickets:{day}"
    return {
        "day": f"{base}:day",
        "counter": f"{base}:counter",
        "queue": f"{base}:queue",
        "current": f"{base}:current",
        "hash_prefix": f"{base}:ticket",  # full key: {hash_prefix}:{ticket_number}
        "logs": f"{base}:logs",
    }


def _ticket_hash_key(day: str, num: int) -> str:
    return f"{_keys(day)['hash_prefix']}:{num}"


def _ensure_day(r, day: str):
    k = _keys(day)
    ttl = _ttl_until_tomorrow()
    # set day marker + counter if absent
    r.set(k["day"], day, ex=ttl, nx=True)
    r.set(k["counter"], 0, ex=ttl, nx=True)
    # ensure TTL refreshed on queue/current too
    r.expire(k["queue"], ttl)
    r.expire(k["current"], ttl)
    r.expire(k["logs"], ttl)


def _append_log(r, day: str, message: str):
    k = _keys(day)
    now = datetime.now(timezone.utc).isoformat()
    r.lpush(k["logs"], f"{now}|{message}")
    r.ltrim(k["logs"], 0, 49)
    ttl = _ttl_until_tomorrow()
    r.expire(k["logs"], ttl)


def start_day():
    r = get_redis()
    day = _today_key()
    _ensure_day(r, day)
    _append_log(r, day, "start_day")
    return {"day": day, "open": True}


def end_day():
    r = get_redis()
    day = _today_key()
    k = _keys(day)
    # delete all per-day keys (queue, counter, current, marker, hashes)
    pipe = r.pipeline()
    # delete hashes by scan
    cursor = "0"
    pattern = f"{k['hash_prefix']}:*"
    while True:
        cursor, keys = r.scan(cursor=cursor, match=pattern, count=200)
        if keys:
            pipe.delete(*keys)
        if cursor == 0 or cursor == "0":
            break
    pipe.delete(k["queue"], k["counter"], k["current"], k["day"], k["logs"])
    pipe.execute()
    return {"day": day, "ended": True, "open": False}


def take_ticket(service_type: str | None = None) -> dict:
    r = get_redis()
    day = _today_key()
    k = _keys(day)
    # day must exist (set by start_day); do not auto-create
    if not r.exists(k["day"]):
        return {"closed": True, "message": "Service fermé, revenez demain"}
    # refresh TTL and structure
    _ensure_day(r, day)
    ttl = _ttl_until_tomorrow()
    queue_len_before = r.llen(k["queue"])
    ticket_number = r.incr(k["counter"])
    now_ts = datetime.now(timezone.utc).timestamp()
    ticket = Ticket(
        ticket_number=ticket_number,
        creation_time=now_ts,
        service_type=service_type,
        status="waiting",
    )
    pipe = r.pipeline()
    pipe.hset(_ticket_hash_key(day, ticket_number), mapping=ticket.to_dict())
    pipe.expire(_ticket_hash_key(day, ticket_number), ttl)
    pipe.rpush(k["queue"], ticket_number)
    pipe.expire(k["queue"], ttl)
    pipe.execute()

    waiting_before = max(queue_len_before, 0)
    _append_log(r, day, f"take_ticket:{ticket_number}")
    return {
        "day": day,
        "ticket": ticket.to_dict(),
        "waiting_before": waiting_before,
    }


def _get_ticket(day: str, num: int) -> dict | None:
    r = get_redis()
    data = r.hgetall(_ticket_hash_key(day, num))
    if not data:
        return None
    # hgetall returns strings; keep as is for frontend
    return data


def get_status():
    r = get_redis()
    day = _today_key()
    k = _keys(day)
    open_flag = r.exists(k["day"]) == 1
    queue_len = r.llen(k["queue"]) if open_flag else 0
    current = r.get(k["current"]) if open_flag else None
    next_ticket = r.lindex(k["queue"], 0) if open_flag else None
    return {
        "day": day,
        "open": bool(open_flag),
        "queue_length": queue_len,
        "current_ticket": current,
        "next_ticket": next_ticket,
        "waiting_tickets": max(queue_len, 0),
    }


def call_next():
    r = get_redis()
    day = _today_key()
    k = _keys(day)
    ttl = _ttl_until_tomorrow()
    ticket_num = r.lpop(k["queue"])
    if ticket_num is None:
        return {"message": "Aucun ticket en attente", "current_ticket": None}
    pipe = r.pipeline()
    pipe.set(k["current"], ticket_num, ex=ttl)
    pipe.hset(_ticket_hash_key(day, int(ticket_num)), mapping={"status": "in_progress"})
    pipe.expire(_ticket_hash_key(day, int(ticket_num)), ttl)
    pipe.execute()
    _append_log(r, day, f"call_next:{ticket_num}")
    return {
        "current_ticket": ticket_num,
        "waiting_tickets": max(r.llen(k["queue"]), 0),
    }


def finish_current():
    r = get_redis()
    day = _today_key()
    k = _keys(day)
    ticket_num = r.get(k["current"])
    if ticket_num is None:
        return {"message": "Aucun ticket en cours"}
    pipe = r.pipeline()
    pipe.hset(_ticket_hash_key(day, int(ticket_num)), mapping={"status": "completed"})
    pipe.delete(k["current"])
    pipe.execute()
    _append_log(r, day, f"finish_current:{ticket_num}")
    return {"finished_ticket": ticket_num}


def snapshot():
    """Return a richer snapshot for dashboards."""
    r = get_redis()
    day = _today_key()
    k = _keys(day)
    open_flag = r.exists(k["day"]) == 1
    queue_len = r.llen(k["queue"]) if open_flag else 0
    current = r.get(k["current"]) if open_flag else None
    next_ticket = r.lindex(k["queue"], 0) if open_flag else None

    # fetch waiting tickets (cap to avoid huge payload)
    waiting_list = r.lrange(k["queue"], 0, 49) if open_flag else []  # top 50 for UI
    waiting_details = []
    for num in waiting_list:
        data = _get_ticket(day, int(num)) or {}
        waiting_details.append({"ticket_number": num, **data})

    current_data = _get_ticket(day, int(current)) if current else None
    logs = r.lrange(k["logs"], 0, 19)

    # Compute average waiting time (seconds) for items we have
    avg_wait_seconds = None
    if open_flag and waiting_details:
        now = datetime.now(timezone.utc).timestamp()
        deltas = []
        for item in waiting_details:
            try:
                ct = float(item.get("creation_time"))
                deltas.append(now - ct)
            except (TypeError, ValueError):
                continue
        if deltas:
            avg_wait_seconds = sum(deltas) / len(deltas)

    key_count = 0
    hash_count = 0
    ttl_seconds = _ttl_until_tomorrow() if open_flag else None
    if open_flag:
        cursor = 0
        pattern_base = f"{k['day'].split(':day')[0]}"
        while True:
            cursor, keys = r.scan(cursor=cursor, match=f"{pattern_base}*", count=200)
            key_count += len(keys)
            if cursor == 0 or cursor == "0":
                break
        # count ticket hashes only
        cursor = 0
        hash_pattern = f"{k['hash_prefix']}:*"
        while True:
            cursor, keys = r.scan(cursor=cursor, match=hash_pattern, count=200)
            hash_count += len(keys)
            if cursor == 0 or cursor == "0":
                break

    return {
        "day": day,
        "open": bool(open_flag),
        "queue_length": queue_len,
        "current_ticket": current,
        "current_ticket_data": current_data,
        "next_ticket": next_ticket,
        "waiting_tickets": max(queue_len, 0),
        "waiting_list": waiting_details,
        "logs": logs,
        "total_tickets": int(r.get(k["counter"]) or 0) if open_flag else 0,
        "avg_wait_seconds": avg_wait_seconds,
        "key_count": key_count,
        "hash_count": hash_count,
        "ttl_seconds": ttl_seconds,
    }
