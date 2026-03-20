from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from cloud import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('', views.index, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout, name='logout'),
    path('register/', views.register, name='register'),

    # Dashboard & Cloud
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_files, name='upload'),
    path('download/<int:pk>/', views.download_file, name='download'),
    path('delete/<int:pk>/', views.delete_file, name='delete'),
    path('folder/new/', views.create_folder, name='create_folder'),
    path('folder/<int:pk>/delete/', views.delete_folder, name='delete_folder'),
    path('folder/<int:pk>/', views.folder_view, name='folder'),
    path('share/<int:pk>/toggle/', views.toggle_share, name='toggle_share'),
    path('public/<str:token>/', views.public_download, name='public_download'),
    path('search/', views.search, name='search'),

    # API endpoint (eigene JSON-Antworten, kein DRF)
    path('api/upload/', views.api_upload, name='api_upload'),
    path('api/files/', views.api_files, name='api_files'),
    path('api/delete/<int:pk>/', views.api_delete, name='api_delete'),

    # ── Token-API v1 (für externe Projekte wie JDS-Verein) ──────────────────
    path('api/v1/upload/',          views.api_token_upload, name='api_v1_upload'),
    path('api/v1/files/',           views.api_token_files,  name='api_v1_files'),
    path('api/v1/files/<int:pk>/',  views.api_token_delete, name='api_v1_delete'),
    path('api/v1/info/',            views.api_token_info,   name='api_v1_info'),

    # ── Token-Verwaltungs-Dashboard ──────────────────────────────────────────
    path('tokens/', views.token_verwaltung, name='token_verwaltung'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
