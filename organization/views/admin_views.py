import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from organization.models import Organization
from organization.serializers import (
    OrgBasicInfoSerializer,
    OrgContactSerializer,
    OrgAddressSerializer,
    OrgDocumentSerializer,
    OrgProfileCompletionSerializer,
)
from users.permissions import IsSysAdmin
from rest_framework.permissions import IsAuthenticated
from rbac.utils import log_activity
from rbac.models import ActivityLog

logger = logging.getLogger(__name__)

def get_org_from_token(request):
    """
    Extracts the organization from the JWT token claims.
    Every admin view uses this instead of get_org_from_request()
    because admin requests are already authenticated —
    the org is already in the token, no need to re-resolve from hostname.
    """
    org_id = request.auth.get('org_id')
    try:
        return Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return None
    

class OrgProfileCompletionView(APIView):
    """
    Returns completion status of org profile.
    Called on every admin login to decide whether to show the modal.
    Both sysadmin check and IsAuthenticated combined in one
    permission class — IsSysAdmin already handles both.
    """
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            logger.warning(
                f"OrgProfileCompletionView: org not found for token "
                f"user={request.user.email}"
            )
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrgProfileCompletionSerializer(org)
        return Response(serializer.data)

class OrgBasicInfoView(APIView):
    """
    GET  → returns current basic info
    PATCH → updates basic info (draft save — other sections not required)
    
    MultiPartParser + FormParser needed for file uploads (logo, cover_picture)
    JSONParser for regular JSON requests
    """
    permission_classes = [IsAuthenticated, IsSysAdmin]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrgBasicInfoSerializer(org)
        return Response(serializer.data)

    def patch(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # partial=True → only validate fields that are sent
        # allows saving one field without sending all fields
        serializer = OrgBasicInfoSerializer(org, data=request.data, partial=True)

        if not serializer.is_valid():
            logger.warning(
                f"OrgBasicInfoView: validation failed "
                f"user={request.user.email} errors={serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.ORG_UPDATED,
            request=request,
            target=org,
            metadata={'section': 'basic_info', 'fields': list(request.data.keys())}
        )

        logger.info(f"OrgBasicInfoView: updated by user={request.user.email}")

        return Response(serializer.data)
    
class OrgContactView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrgContactSerializer(org)
        return Response(serializer.data)

    def patch(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrgContactSerializer(org, data=request.data, partial=True)

        if not serializer.is_valid():
            logger.warning(
                f"OrgContactView: validation failed "
                f"user={request.user.email} errors={serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.ORG_UPDATED,
            request=request,
            target=org,
            metadata={'section': 'contact', 'fields': list(request.data.keys())}
        )

        logger.info(f"OrgContactView: updated by user={request.user.email}")

        return Response(serializer.data)
    
class OrgAddressView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrgAddressSerializer(org)
        return Response(serializer.data)

    def patch(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrgAddressSerializer(org, data=request.data, partial=True)

        if not serializer.is_valid():
            logger.warning(
                f"OrgAddressView: validation failed "
                f"user={request.user.email} errors={serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.ORG_UPDATED,
            request=request,
            target=org,
            metadata={'section': 'address', 'fields': list(request.data.keys())}
        )

        logger.info(f"OrgAddressView: updated by user={request.user.email}")

        return Response(serializer.data)

class OrgDocumentView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrgDocumentSerializer(org)
        return Response(serializer.data)

    def patch(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response(
                {'detail': 'Organization not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrgDocumentSerializer(org, data=request.data, partial=True)

        if not serializer.is_valid():
            logger.warning(
                f"OrgDocumentView: validation failed "
                f"user={request.user.email} errors={serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.ORG_UPDATED,
            request=request,
            target=org,
            metadata={'section': 'documents', 'fields': list(request.data.keys())}
        )

        logger.info(f"OrgDocumentView: updated by user={request.user.email}")

        return Response(serializer.data)