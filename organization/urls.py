from django.urls import path
from organization.views import OrganizationPublicView
from organization.views import (
    OrgProfileCompletionView,
    OrgBasicInfoView,
    OrgContactView,
    OrgAddressView,
    OrgDocumentView,
    SubOrgListCreateView,
    SubOrgDetailView,
    SubOrgBasicView,
    SubOrgContactView,
    SubOrgAddressView,
    SubOrgPublicListView,
)



urlpatterns = [
    path(
        "public/organization/",
        OrganizationPublicView.as_view(),
        name="public-organization",
    ),
    path('profile/completion/', OrgProfileCompletionView.as_view(), name='org-profile-completion'),
    path('profile/basic/',      OrgBasicInfoView.as_view(),         name='org-basic-info'),
    path('profile/contact/',    OrgContactView.as_view(),           name='org-contact'),
    path('profile/address/',    OrgAddressView.as_view(),           name='org-address'),
    path('profile/documents/',  OrgDocumentView.as_view(),          name='org-documents'),
        path('suborgs/',                          SubOrgListCreateView.as_view(), name='suborg-list-create'),
    path('suborgs/<uuid:suborg_uuid>/',           SubOrgDetailView.as_view(),    name='suborg-detail'),
    path('suborgs/<uuid:suborg_uuid>/basic/',     SubOrgBasicView.as_view(),    name='suborg-basic'),
    path('suborgs/<uuid:suborg_uuid>/contact/',   SubOrgContactView.as_view(),  name='suborg-contact'),
    path('suborgs/<uuid:suborg_uuid>/address/',   SubOrgAddressView.as_view(),  name='suborg-address'),
    path('public/suborgs/',                        SubOrgPublicListView.as_view(), name='public-suborgs'),
]