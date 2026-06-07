from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from organization.models import Organization
from organization.serializers import OrganizationPublicSerializer


class OrganizationPublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        domain_name = request.query_params.get("domain_name")
        

        if not domain_name:
            return Response(
                {"message": "Domain_name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        domain_name = f"https://{domain_name}"
        try:
            org = Organization.objects.get(domain_name=domain_name)
        except Organization.DoesNotExist:
            return Response(
                {
                    "message": f"Organization with domain '{domain_name}' does not exist."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrganizationPublicSerializer(org, context={"request":request})

        return Response(
            {
                "message": "Organization retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )