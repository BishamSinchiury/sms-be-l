from django.urls import path
from rbac.views import (
    ActivityLogListView,
    PermissionListCreateView,
    PermissionDetailView,
    RoleListCreateView,
    RoleDetailView,
    UserPermissionsView,
)

urlpatterns = [
    path('logs/', ActivityLogListView.as_view(), name='activity-log-list'),

    # Permissions
    path('permissions/',                 PermissionListCreateView.as_view(), name='permission-list-create'),
    path('permissions/<uuid:perm_uuid>/', PermissionDetailView.as_view(),    name='permission-detail'),

    # Roles
    path('roles/',                       RoleListCreateView.as_view(), name='role-list-create'),
    path('roles/<uuid:role_uuid>/',      RoleDetailView.as_view(),     name='role-detail'),

    # Per-user permission overrides
    path('users/<uuid:user_uuid>/permissions/', UserPermissionsView.as_view(), name='user-permissions'),
]