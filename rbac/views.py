from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from rbac.models import Permission, Role, RolePermission, UserRole, UserPermissionOverride
from rbac.serializers import PermissionSerializer, RoleSerializer
from users.models import CustomUser
from rbac.utils import log_activity


from rbac.models import ActivityLog
from rbac.serializers import ActivityLogSerializer
from users.permissions import IsSysAdmin
from organization.views import get_org_from_token


class LogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ActivityLogListView(APIView):
    """
    Returns activity logs for the current org, newest first.
    Optional ?action=USER_CREATED filter.
    """
    permission_classes = [IsAuthenticated, IsSysAdmin]
    pagination_class = LogPagination

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        logs = ActivityLog.objects.filter(user__org=org).select_related('user', 'content_type')

        action = request.query_params.get('action')
        if action:
            logs = logs.filter(action=action)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(logs, request)
        serializer = ActivityLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    


# ─── Permissions CRUD ──────────────────────────────────────────────────────────

class PermissionListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        perms = Permission.objects.filter(org=org).order_by('name')
        return Response(PermissionSerializer(perms, many=True).data)

    def post(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PermissionSerializer(data=request.data, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        perm = serializer.save()
        return Response(PermissionSerializer(perm).data, status=status.HTTP_201_CREATED)


class PermissionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get_object(self, request, perm_uuid):
        org = get_org_from_token(request)
        if not org:
            return None, None
        try:
            return org, Permission.objects.get(org=org, uuid=perm_uuid)
        except Permission.DoesNotExist:
            return org, None

    def get(self, request, perm_uuid):
        org, perm = self.get_object(request, perm_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not perm:
            return Response({'detail': 'Permission not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PermissionSerializer(perm).data)

    def patch(self, request, perm_uuid):
        org, perm = self.get_object(request, perm_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not perm:
            return Response({'detail': 'Permission not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PermissionSerializer(perm, data=request.data, partial=True, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        perm = serializer.save()
        return Response(PermissionSerializer(perm).data)

    def delete(self, request, perm_uuid):
        org, perm = self.get_object(request, perm_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not perm:
            return Response({'detail': 'Permission not found.'}, status=status.HTTP_404_NOT_FOUND)

        perm.delete()  # cascades to RolePermission + UserPermissionOverride rows
        return Response({'detail': 'Permission deleted.'}, status=status.HTTP_204_NO_CONTENT)


# ─── Roles CRUD ─────────────────────────────────────────────────────────────────

class RoleListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        roles = Role.objects.filter(org=org).prefetch_related('permissions')
        
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            roles = roles.filter(name__icontains=search_query)
            
        roles = roles.order_by('name')
        return Response(RoleSerializer(roles, many=True, context={'org': org}).data)

    def post(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RoleSerializer(data=request.data, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        role = serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.ROLE_CREATED,
            request=request,
            target=role,
            metadata={'name': role.name}
        )

        return Response(RoleSerializer(role, context={'org': org}).data, status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get_object(self, request, role_uuid):
        org = get_org_from_token(request)
        if not org:
            return None, None
        try:
            return org, Role.objects.prefetch_related('permissions').get(org=org, uuid=role_uuid)
        except Role.DoesNotExist:
            return org, None

    def get(self, request, role_uuid):
        org, role = self.get_object(request, role_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(RoleSerializer(role, context={'org': org}).data)

    def patch(self, request, role_uuid):
        org, role = self.get_object(request, role_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RoleSerializer(role, data=request.data, partial=True, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        role = serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.ROLE_UPDATED,
            request=request,
            target=role,
            metadata={'fields': list(request.data.keys())}
        )

        return Response(RoleSerializer(role, context={'org': org}).data)

    def delete(self, request, role_uuid):
        org, role = self.get_object(request, role_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        if UserRole.objects.filter(role=role).exists():
            return Response(
                {'detail': 'Cannot delete a role that is assigned to users. Reassign those users first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        name = role.name
        log_activity(
            user=request.user,
            action=ActivityLog.Action.ROLE_DELETED,
            request=request,
            target=None,
            metadata={'name': name}
        )

        role.delete()
        return Response({'detail': 'Role deleted.'}, status=status.HTTP_204_NO_CONTENT)


# ─── Per-user permission overrides ──────────────────────────────────────────────

class UserPermissionsView(APIView):
    """
    GET  → returns every permission in the org, marked with:
           - from_role: does the user's role grant this?
           - override: 'granted' | 'revoked' | null
           - effective: final resolved value (role ⊕ override)

    PUT  → body: { "overrides": [{ "permission_uuid": "...", "granted": true|false|null }] }
           granted=null removes any existing override (falls back to role).
    """
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get_user(self, request, user_uuid):
        org = get_org_from_token(request)
        if not org:
            return None, None
        try:
            return org, CustomUser.objects.select_related('user_role', 'user_role__role').get(uuid=user_uuid, org=org)
        except CustomUser.DoesNotExist:
            return org, None

    def get(self, request, user_uuid):
        org, user = self.get_user(request, user_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(self._build_response(org, user))

    def put(self, request, user_uuid):
        org, user = self.get_user(request, user_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        overrides = request.data.get('overrides', [])
        if not isinstance(overrides, list):
            return Response({'detail': '"overrides" must be a list.'}, status=status.HTTP_400_BAD_REQUEST)

        applied = []
        for item in overrides:
            perm_uuid = item.get('permission_uuid')
            granted   = item.get('granted', None)

            try:
                perm = Permission.objects.get(org=org, uuid=perm_uuid)
            except (Permission.DoesNotExist, ValueError, TypeError):
                continue

            if granted is None:
                UserPermissionOverride.objects.filter(user=user, permission=perm).delete()
            else:
                UserPermissionOverride.objects.update_or_create(
                    user=user, permission=perm, defaults={'granted': bool(granted)}
                )
            applied.append({'codename': perm.codename, 'granted': granted})

        if applied:
            log_activity(
                user=request.user,
                action=ActivityLog.Action.PERMISSION_GRANTED,
                request=request,
                target=user,
                metadata={'overrides': applied}
            )

        return Response(self._build_response(org, user))

    def _build_response(self, org, user):
        user_role = getattr(user, 'user_role', None)

        role_perm_codenames = set()
        if user_role:
            role_perm_codenames = set(
                RolePermission.objects
                .filter(role=user_role.role)
                .values_list('permission__codename', flat=True)
            )

        overrides = UserPermissionOverride.objects.filter(user=user).select_related('permission')
        granted_codenames = {o.permission.codename for o in overrides if o.granted}
        revoked_codenames = {o.permission.codename for o in overrides if not o.granted}

        effective = (role_perm_codenames | granted_codenames) - revoked_codenames

        permissions = []
        for perm in Permission.objects.filter(org=org).order_by('name'):
            override = None
            if perm.codename in granted_codenames:
                override = 'granted'
            elif perm.codename in revoked_codenames:
                override = 'revoked'

            permissions.append({
                'uuid':      perm.uuid,
                'codename':  perm.codename,
                'name':      perm.name,
                'from_role': perm.codename in role_perm_codenames,
                'override':  override,
                'effective': perm.codename in effective,
            })

        return {
            'role': user_role.role.name if user_role else None,
            'permissions': permissions,
        }