from django.urls import path

from . import views

urlpatterns = [
    path("dashboard", views.realtime_dashboard_page, name="realtime_dashboard_page"),
    path("tickets/public", views.ticket_public_page, name="ticket_public_page"),
    path("tickets/staff", views.ticket_staff_page, name="ticket_staff_page"),
    path("tickets/start-day", views.ticket_start_day, name="ticket_start_day"),
    path("tickets/end-day", views.ticket_end_day, name="ticket_end_day"),
    path("tickets/take", views.ticket_take, name="ticket_take"),
    path("tickets/status", views.ticket_status, name="ticket_status"),
    path("tickets/call-next", views.ticket_call_next, name="ticket_call_next"),
    path("tickets/finish-current", views.ticket_finish_current, name="ticket_finish_current"),
    path("tickets/snapshot", views.ticket_snapshot, name="ticket_snapshot"),
]
 