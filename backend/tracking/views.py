import json
from django.http import JsonResponse, HttpRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import ticket_service


def _parse_body(request: HttpRequest) -> dict:
    if request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


@require_http_methods(["GET"])
def realtime_dashboard_page(request: HttpRequest):
    """
    Page autonome pour le suivi temps réel des tickets.
    """
    return render(request, "dashboard.html", {})


# --------------------------
# Ticketing (Redis queue)
# --------------------------


@require_http_methods(["GET"])
def ticket_public_page(request: HttpRequest):
    return render(request, "ticket_public.html")


@require_http_methods(["GET"])
def ticket_staff_page(request: HttpRequest):
    return render(request, "ticket_staff.html")


@csrf_exempt
@require_http_methods(["POST"])
def ticket_start_day(request: HttpRequest) -> JsonResponse:
    return JsonResponse(ticket_service.start_day())


@csrf_exempt
@require_http_methods(["POST"])
def ticket_end_day(request: HttpRequest) -> JsonResponse:
    return JsonResponse(ticket_service.end_day())


@csrf_exempt
@require_http_methods(["POST"])
def ticket_take(request: HttpRequest) -> JsonResponse:
    data = _parse_body(request)
    # Limitation au service "poste" (fixé côté backend)
    return JsonResponse(ticket_service.take_ticket(service_type="poste"), status=201)


@require_http_methods(["GET"])
def ticket_status(request: HttpRequest) -> JsonResponse:
    return JsonResponse(ticket_service.get_status())


@csrf_exempt
@require_http_methods(["POST"])
def ticket_call_next(request: HttpRequest) -> JsonResponse:
    return JsonResponse(ticket_service.call_next())


@csrf_exempt
@require_http_methods(["POST"])
def ticket_finish_current(request: HttpRequest) -> JsonResponse:
    return JsonResponse(ticket_service.finish_current())


@require_http_methods(["GET"])
def ticket_snapshot(request: HttpRequest) -> JsonResponse:
    return JsonResponse(ticket_service.snapshot())
