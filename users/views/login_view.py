from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from users.serializers import LoginSerializer, UserSerializer
from organization.utils import get_org_from_request
from django.conf import settings


# users/views.py
def get_tokens_for_user(user, organization):
    refresh = RefreshToken.for_user(user)
    refresh['org_id'] = str(organization.id)
    refresh['is_admin'] = user.is_staff
    refresh['is_sysadmin'] = user.is_sysadmin
    refresh['email'] = user.email
    refresh['username'] = user.username
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def set_refresh_cookie(response, refresh_token, cookie_name='user_refresh'):
    """
    Attaches the refresh token as an httpOnly cookie to the response.
    The frontend never sees the refresh token value — browser handles it.
    """
    response.set_cookie(
        key=cookie_name,
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        max_age=7 * 24 * 60 * 60,   # 7 days, matches SIMPLE_JWT REFRESH_TOKEN_LIFETIME
    )
    return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        organization = get_org_from_request(request)
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data['user']
        
        if user.org != organization:
            return Response(
                {'detail': 'You do not have access to this organization.'},
                status=status.HTTP_403_FORBIDDEN
            )

        tokens = get_tokens_for_user(user, organization)
        response = Response({
            'user': UserSerializer(user).data,
            'access': tokens['access'],
        })
        set_refresh_cookie(response, tokens['refresh'], 'user_refresh')  # ← correct indentation
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get('user_refresh')  # ← read from cookie
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response(
            {'detail': 'Logged out successfully.'},
            status=status.HTTP_205_RESET_CONTENT
        )
        response.delete_cookie('user_refresh', samesite='Lax')
        return response


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('user_refresh')  # ← read from cookie

        if not refresh_token:
            return Response(
                {'detail': 'Refresh token not found.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)
            new_refresh = str(refresh)

            response = Response({'access': new_access})
            set_refresh_cookie(response, new_refresh, 'user_refresh')  # ← rotate cookie
            return response

        except TokenError:
            return Response(
                {'detail': 'Invalid or expired refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED
            )