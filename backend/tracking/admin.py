from datetime import datetime, timezone

from django.contrib import admin
from django.shortcuts import render
from django.urls import path

from . import session_service


def _ts_to_dt(ts: str | int | None):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except Exception:
        return None


def redis_dashboard(request):
    summary = session_service.get_active_sessions_summary()
    leaderboard = session_service.get_activity_leaderboard(limit=50)

    sessions = []
    for s in summary.get("sessions", []):
        sessions.append(
            {
                **s,
                "login_time_dt": _ts_to_dt(s.get("login_time")),
                "last_activity_dt": _ts_to_dt(s.get("last_activity")),
            }
        )

    context = {
        **admin.site.each_context(request),
        "total_active_sessions": summary.get("total_active_sessions", 0),
        "online_users": summary.get("online_users", []),
        "last_activity_per_user": summary.get("last_activity_per_user", {}),
        "sessions": sessions,
        "leaderboard": leaderboard,
        "title": "Tableau de bord Redis (sessions en temps réel)",
    }
    return render(request, "admin/redis_dashboard.html", context)


def _get_custom_admin_urls(original_get_urls):
    def get_urls():
        urls = original_get_urls()
        custom = [
            path("redis-dashboard/", admin.site.admin_view(redis_dashboard), name="redis-dashboard"),
        ]
        return custom + urls

    return get_urls


# Inject the custom route into the default admin site
admin.site.get_urls = _get_custom_admin_urls(admin.site.get_urls)
