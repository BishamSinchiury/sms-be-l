from django.http import JsonResponse
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from organization.utils import get_org_from_request


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _get_token_from_request(self, request):
        """
        Extracts and decodes the Bearer token from the Authorization header.
        Returns the decoded token or None if no token is present.
        """
        auth_header = request.headers.get('Authorization', '')

        # Header format: "Bearer <token>"
        if not auth_header.startswith('Bearer '):
            return None

        raw_token = auth_header.split(' ')[1]

        try:
            return AccessToken(raw_token)   # decodes and validates signature + expiry
        except (TokenError, InvalidToken):
            return None     # invalid/expired token — let DRF handle the 401

    def __call__(self, request):
        token = self._get_token_from_request(request)

        # No token → public endpoint, let through
        if token is None:
            return self.get_response(request)

        try:
            org_id_in_token = str(token.get('org_id'))

            print(org_id_in_token)

            organization = get_org_from_request(request)
            print(organization)
            org_id_from_hostname = str(organization.id)

            if org_id_in_token != org_id_from_hostname:
                return JsonResponse(
                    {'detail': 'Token does not belong to this organization.'},
                    status=403
                )

        except Exception:
            return JsonResponse(
                {'detail': 'No organization found for this domain.'},
                status=404
            )

        return self.get_response(request)