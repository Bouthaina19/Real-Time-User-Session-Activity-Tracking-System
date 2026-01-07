from django.urls import path

from . import views

urlpatterns = [
    path("sessions/login", views.login_session, name="login_session"),
    path("sessions/activity", views.touch_activity, name="touch_activity"),
    path("sessions/logout", views.logout_session, name="logout_session"),
    path("sessions/<str:session_id>", views.get_session_view, name="get_session"),
    path("dashboard/summary", views.dashboard_summary, name="dashboard_summary"),
    path("dashboard/leaderboard", views.activity_leaderboard, name="activity_leaderboard"),
]
