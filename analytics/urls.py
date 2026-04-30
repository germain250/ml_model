from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Super Admin portal
    path('admin/overview/', views.super_admin_overview, name='super_admin_overview'),
    path('admin/schools/', views.super_admin_schools, name='super_admin_schools'),
    path('admin/schools/add/', views.super_admin_add_school, name='super_admin_add_school'),
    path('super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),  # legacy redirect

    # DOS portal
    path('dos/', views.dos_overview, name='dos_overview'),
    path('dos/students/', views.dos_students, name='dos_students'),
    path('dos/students/add/', views.dos_add_student, name='dos_add_student'),
    path('dos/settings/', views.dos_settings, name='dos_settings'),
    path('dos/dashboard/', views.dos_dashboard, name='dos_dashboard'),  # legacy redirect

    # APIs
    path('api/add-student/', views.api_add_student, name='api_add_student'),
    path('api/change-password/', views.api_change_password, name='api_change_password'),
    path('api/student/<int:student_id>/edit/', views.api_edit_student, name='api_edit_student'),
    path('api/student/<int:student_id>/delete/', views.api_delete_student, name='api_delete_student'),

    # Student report
    path('dos/students/<int:student_id>/report/', views.student_deliberate, name='student_deliberate'),
]
