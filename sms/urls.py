from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from .views import demo_no_csrf

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/org/", include("organization.urls")),
    path("api/demo-no-csrf/", demo_no_csrf),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )