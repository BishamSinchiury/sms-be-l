from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/csrf/", get_csrf_token),
    path("api/org/", include("organization.urls")),
    path("api/auth/", include("users.urls")),
    path("api/rbac/", include("rbac.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )