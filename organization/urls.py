from django.urls import path
from organization.views import OrganizationPublicView

urlpatterns = [
    path(
        "public/organization/",
        OrganizationPublicView.as_view(),
        name="public-organization",
    ),
]