from organization.models import SubOrganization, Organization
from organization.serializers import SubOrganizationSerializer, SubOrganizationListSerializer
from organization.serializers import SubOrgBasicSerializer, SubOrgContactSerializer, SubOrgAddressSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from users.permissions import IsSysAdmin
from organization.views import get_org_from_token

from rbac.utils import log_activity
from rbac.models import ActivityLog


class SubOrgScopedView(APIView):
    """
    Shared get_object for any view that operates on a single SubOrganization
    scoped to the requesting user's org. Replaces 4 copies of the same
    method across SubOrgDetailView / SubOrgBasicView / SubOrgContactView /
    SubOrgAddressView.
    """
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get_object(self, request, suborg_uuid):
        org = get_org_from_token(request)
        if not org:
            return None, None
        try:
            return org, org.suborgs.get(uuid=suborg_uuid)
        except SubOrganization.DoesNotExist:
            return org, None

    def not_found_response(self, org, suborg):
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not suborg:
            return Response({'detail': 'Sub-organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        return None


class SubOrgListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        suborgs = org.suborgs.all().order_by('name')
        return Response(SubOrganizationListSerializer(suborgs, many=True).data)

    def post(self, request):
        org = get_org_from_token(request)
        if not org:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        # org is derived from the authenticated user's token — never client-supplied
        serializer = SubOrganizationSerializer(data=request.data, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        suborg = serializer.save()  # create() pulls org from context

        log_activity(
            user=request.user,
            verb=ActivityLog.Verb.CREATED,
            request=request,
            target=suborg,
            metadata={'name': suborg.name}
        )

        return Response(SubOrganizationSerializer(suborg).data, status=status.HTTP_201_CREATED)


class SubOrgDetailView(SubOrgScopedView):

    def get(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err
        return Response(SubOrganizationSerializer(suborg).data)

    def patch(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err

        serializer = SubOrganizationSerializer(suborg, data=request.data, partial=True, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        suborg = serializer.save()

        log_activity(
            user=request.user,
            verb=ActivityLog.Verb.UPDATED,
            request=request,
            target=suborg,
            metadata={'section': 'suborg', 'fields': list(request.data.keys())}
        )

        return Response(SubOrganizationSerializer(suborg).data)

    def delete(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err

        name = suborg.name
        suborg_uuid_str = str(suborg.uuid)

        suborg.delete()

        # Logged after delete with an explicit target_repr/metadata since
        # the instance no longer exists to derive a representation from.
        log_activity(
            user=request.user,
            verb=ActivityLog.Verb.DELETED,
            request=request,
            target=None,
            target_repr=name,
            metadata={'name': name, 'uuid': suborg_uuid_str}
        )

        return Response({'detail': 'Sub-organization deleted.'}, status=status.HTTP_204_NO_CONTENT)


# ─── SubOrg Section: Basic Info (name, description) ─────────────────────────────

class SubOrgBasicView(SubOrgScopedView):

    def get(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err
        return Response(SubOrgBasicSerializer(suborg).data)

    def patch(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err

        serializer = SubOrgBasicSerializer(suborg, data=request.data, partial=True, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        log_activity(
            user=request.user,
            verb=ActivityLog.Verb.UPDATED,
            request=request,
            target=suborg,
            metadata={'section': 'basic_info', 'fields': list(request.data.keys())}
        )

        return Response(serializer.data)


# ─── SubOrg Section: Contact ────────────────────────────────────────────────────

class SubOrgContactView(SubOrgScopedView):

    def get(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err
        return Response(SubOrgContactSerializer(suborg).data)

    def patch(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err

        serializer = SubOrgContactSerializer(suborg, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        log_activity(
            user=request.user,
            verb=ActivityLog.Verb.UPDATED,
            request=request,
            target=suborg,
            metadata={'section': 'contact', 'fields': list(request.data.keys())}
        )

        return Response(serializer.data)


# ─── SubOrg Section: Address ────────────────────────────────────────────────────

class SubOrgAddressView(SubOrgScopedView):

    def get(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err
        return Response(SubOrgAddressSerializer(suborg).data)

    def patch(self, request, suborg_uuid):
        org, suborg = self.get_object(request, suborg_uuid)
        err = self.not_found_response(org, suborg)
        if err:
            return err

        serializer = SubOrgAddressSerializer(suborg, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        log_activity(
            user=request.user,
            verb=ActivityLog.Verb.UPDATED,
            request=request,
            target=suborg,
            metadata={'section': 'address', 'fields': list(request.data.keys())}
        )

        return Response(serializer.data)


# ─── Public: SubOrg list (no auth required) ──────────────────────────────────────

class SubOrgPublicListView(APIView):
    """
    Public endpoint to list sub-organizations for an organization.
    Requires ?domain_name=<domain> query parameter (same pattern as OrganizationPublicView).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        domain_name = request.query_params.get("domain_name")
        if not domain_name:
            return Response(
                {"message": "domain_name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            org = Organization.objects.get(domain_name=domain_name)
        except Organization.DoesNotExist:
            return Response(
                {"message": f"Organization with domain '{domain_name}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        suborgs = org.suborgs.all().order_by('name')
        serializer = SubOrganizationListSerializer(suborgs, many=True)

        return Response({
            "message": "Sub-organizations retrieved successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)