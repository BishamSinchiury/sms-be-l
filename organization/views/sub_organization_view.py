from organization.models import SubOrganization
from organization.serializers import SubOrganizationSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from users.permissions import IsSysAdmin
from organization.views import get_org_from_token

from rbac.utils import log_activity
from rbac.models import ActivityLog

from organization.models import Organization
from organization.serializers import OrganizationPublicSerializer


class SubOrgListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        suborgs = org.suborgs.all().order_by('name')
        return Response(SubOrganizationSerializer(suborgs, many=True).data)

    def post(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubOrganizationSerializer(data=request.data, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        suborg = serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.SUBORG_CREATED,
            request=request,
            target=suborg,
            metadata={'name': suborg.name}
        )

        return Response(SubOrganizationSerializer(suborg).data, status=status.HTTP_201_CREATED)


class SubOrgDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get_object(self, request, suborg_uuid):
        org = get_org_from_token(request)
        if not org:
            return None, None
        try:
            return org, org.suborgs.get(uuid=suborg_uuid)
        except SubOrganization.DoesNotExist:
            return org, None

    def get(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not suborg:
            return Response({'detail': 'Sub-organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SubOrganizationSerializer(suborg).data)

    def patch(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not suborg:
            return Response({'detail': 'Sub-organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubOrganizationSerializer(suborg, data=request.data, partial=True, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        suborg = serializer.save()

        log_activity(
            user=request.user,
            action=ActivityLog.Action.SUBORG_UPDATED,
            request=request,
            target=suborg,
            metadata={'section': 'suborg', 'fields': list(request.data.keys())}
        )

        return Response(SubOrganizationSerializer(suborg).data)

    def delete(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not suborg:
            return Response({'detail': 'Sub-organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        name = suborg.name
        suborg_uuid_str = str(suborg.uuid)

        log_activity(
            user=request.user,
            action=ActivityLog.Action.SUBORG_DELETED,
            request=request,
            target=None,
            metadata={'name': name, 'uuid': suborg_uuid_str}
        )

        suborg.delete()
        return Response({'detail': 'Sub-organization deleted.'}, status=status.HTTP_204_NO_CONTENT)