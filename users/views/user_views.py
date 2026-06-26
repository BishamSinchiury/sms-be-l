from django.db import models
from users.models import CustomUser
from users.permissions import IsSysAdmin
from users.serializers import (
    UserListSerializer,
    UserDetailSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    RoleMiniSerializer,
)
from organization.views import get_org_from_token
from rbac.utils import log_activity
from rbac.models import ActivityLog, Role

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status



class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Start with all users in this org
        queryset = (
            CustomUser.objects
            .filter(org=org)
            .select_related('profile__personal', 'profile__contact', 'user_role', 'user_role__role')
            .order_by('-created_at')
        )

        # ── Filters ─────────────────────────────────────────────────────
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                models.Q(email__icontains=search) |
                models.Q(username__icontains=search) |
                models.Q(profile__personal__first_name__icontains=search) |
                models.Q(profile__personal__last_name__icontains=search)
            )

        role = request.query_params.get('role', '').strip()
        if role:
            queryset = queryset.filter(user_role__role__name__iexact=role)

        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        is_active = request.query_params.get('is_active', '').strip()
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        is_staff = request.query_params.get('is_staff', '').strip()
        if is_staff == 'true':
            queryset = queryset.filter(is_staff=True)
        elif is_staff == 'false':
            queryset = queryset.filter(is_staff=False)

        is_verified = request.query_params.get('is_verified', '').strip()
        if is_verified == 'true':
            queryset = queryset.filter(is_verified=True)
        elif is_verified == 'false':
            queryset = queryset.filter(is_verified=False)

        return Response(UserListSerializer(queryset, many=True).data)

    def post(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserCreateSerializer(data=request.data, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.USER_CREATED,
            request=request,
            target=user,
            metadata={'email': user.email}
        )

        return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    """Returns the details of the currently authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = CustomUser.objects.select_related(
            'profile__personal', 'profile__contact', 'profile__address', 'user_role', 'user_role__role'
        ).get(uuid=request.user.uuid)
        return Response(UserDetailSerializer(user).data)

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get_object(self, request, user_uuid):
        org = get_org_from_token(request)
        if not org:
            return None, None
        try:
            user = CustomUser.objects.select_related(
                'profile__personal', 'profile__contact', 'profile__address', 'user_role', 'user_role__role'
            ).get(uuid=user_uuid, org=org)
            return org, user
        except CustomUser.DoesNotExist:
            return org, None

    def get(self, request, user_uuid):
        org, user = self.get_object(request, user_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserDetailSerializer(user).data)

    def patch(self, request, user_uuid):
        org, user = self.get_object(request, user_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Prevent a sysadmin from locking themselves out
        if str(user.uuid) == str(request.user.uuid) and 'is_active' in request.data and not request.data.get('is_active'):
            return Response({'detail': 'You cannot deactivate your own account.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserUpdateSerializer(user, data=request.data, partial=True, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        action = ActivityLog.Action.USER_UPDATED
        if 'is_active' in request.data:
            action = ActivityLog.Action.USER_ACTIVATED if request.data.get('is_active') else ActivityLog.Action.USER_DEACTIVATED
        elif 'role_uuid' in request.data:
            action = ActivityLog.Action.ROLE_ASSIGNED

        log_activity(
            user=request.user,
            action=action,
            request=request,
            target=user,
            metadata={'fields': list(request.data.keys())}
        )

        return Response(UserDetailSerializer(user).data)

    def delete(self, request, user_uuid):
        org, user = self.get_object(request, user_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if str(user.uuid) == str(request.user.uuid):
            return Response({'detail': 'You cannot delete your own account.'}, status=status.HTTP_400_BAD_REQUEST)

        email = user.email

        log_activity(
            user=request.user,
            action=ActivityLog.Action.USER_DELETED,
            request=request,
            target=None,
            metadata={'email': email}
        )

        user.delete()
        return Response({'detail': 'User deleted.'}, status=status.HTTP_204_NO_CONTENT)


class RoleListView(APIView):
    """Simple list of roles in the org — used to populate role dropdowns."""
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        roles = Role.objects.filter(org=org).order_by('name')
        return Response(RoleMiniSerializer(roles, many=True).data)