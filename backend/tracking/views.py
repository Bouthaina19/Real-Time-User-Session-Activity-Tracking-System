import json
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import session_service


def _parse_body(request: HttpRequest) -> dict:
    if request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _bad_request(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


@csrf_exempt
@require_http_methods(["POST"])
def login_session(request: HttpRequest) -> JsonResponse:
    data = _parse_body(request)
    user_id = data.get("user_id")
    if not user_id:
        return _bad_request("user_id requis")
    session_data = session_service.create_session(str(user_id))
    return JsonResponse(session_data, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def touch_activity(request: HttpRequest) -> JsonResponse:
    data = _parse_body(request)
    session_id = data.get("session_id")
    if not session_id:
        return _bad_request("session_id requis")
    updated = session_service.update_activity(str(session_id))
    if not updated:
        return _bad_request("session introuvable", status=404)
    return JsonResponse(updated)


@csrf_exempt
@require_http_methods(["POST"])
def logout_session(request: HttpRequest) -> JsonResponse:
    data = _parse_body(request)
    session_id = data.get("session_id")
    if not session_id:
        return _bad_request("session_id requis")
    ended = session_service.end_session(str(session_id))
    if not ended:
        return _bad_request("session introuvable", status=404)
    return JsonResponse(ended)


@require_http_methods(["GET"])
def get_session_view(request: HttpRequest, session_id: str) -> JsonResponse:
    session = session_service.get_session(session_id)
    if not session:
        return _bad_request("session introuvable", status=404)
    return JsonResponse(session)


@require_http_methods(["GET"])
def dashboard_summary(request: HttpRequest) -> JsonResponse:
    summary = session_service.get_active_sessions_summary()
    return JsonResponse(summary)


@require_http_methods(["GET"])
def activity_leaderboard(request: HttpRequest) -> JsonResponse:
    limit_param = request.GET.get("limit")
    try:
        limit = int(limit_param) if limit_param else 50
    except ValueError:
        return _bad_request("limit doit être un entier")
    leaderboard = session_service.get_activity_leaderboard(limit=limit)
    return JsonResponse({"leaderboard": leaderboard})
