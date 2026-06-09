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

    refresh['org_id'] = str(organization.uuid)
    refresh['is_sysadmin'] = user.is_sysadmin

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
        
        if serializer.is_valid():
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
        set_refresh_cookie(response, tokens['refresh'], 'user_refresh')
        return response
                
       


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_205_RESET_CONTENT)
        except KeyError:
            return Response({'detail': 'Refresh token required.'}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError:
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
        
class TokenRefreshView(APIView):
    """Thin wrapper — you can also use simplejwt's built-in directly."""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh = RefreshToken(request.data['refresh'])
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),   # rotated token
            })
        except (KeyError, TokenError):
            return Response({'detail': 'Invalid or expired refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)



