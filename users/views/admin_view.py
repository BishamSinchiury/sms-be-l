from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from users.serializers import UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken 
from rest_framework_simplejwt.exceptions import TokenError
from organization.utils import get_org_from_request
from users.otp import store_otp, verify_otp, send_otp_email, OTPEmailError
from users.serializers import AdminLoginSerializer, AdminOTPVerifySerializer
from users.models import CustomUser
from users.views import get_tokens_for_user, set_refresh_cookie
class AdminLoginView(APIView):
    """
    Step 1 of admin login.
    Validates credentials, sends OTP, returns nothing sensitive.
    
    We return the same response whether the email exists or not —
    prevents attackers from using this endpoint to enumerate
    which emails are registered admins.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        organization = get_org_from_request(request)

        serializer = AdminLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = serializer.validated_data['user']

        # Cross-tenant check — same as regular login
        if user.org != organization:
            return Response(
                {'detail': 'You do not have access to this organization.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            otp = store_otp(user.email, 'login')
            send_otp_email(user.email, otp, 'login')
        except OTPEmailError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            {'detail': 'OTP sent to your email address.'},
            status=status.HTTP_200_OK
        )


class AdminOTPVerifyView(APIView):
    """
    Step 2 of admin login.
    Validates OTP and issues scoped JWT token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        organization = get_org_from_request(request)

        serializer = AdminOTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        # Verify OTP — returns False if wrong, expired, or already used
        if not verify_otp(email, 'login', otp):
            return Response(
                {'detail': 'Invalid or expired OTP.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # OTP valid — fetch user and issue token
        try:
            user = CustomUser.objects.get(email=email, org=organization)
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Final safety check — confirm they're still admin
        # (role could have changed between step 1 and step 2)
        if not user.is_staff and not user.is_sysadmin:
            return Response(
                {'detail': 'Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        tokens = get_tokens_for_user(user, organization)
        response = Response({
            'user': UserSerializer(user).data,
            'access': tokens['access'],       # access token goes to frontend memory
        })
        set_refresh_cookie(response, tokens['refresh'], 'admin_refresh')
        return response
    

class AdminTokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Reads from admin_refresh cookie instead
        refresh_token = request.COOKIES.get('admin_refresh')

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
            set_refresh_cookie(response, new_refresh, 'admin_refresh')
            return response

        except TokenError:
            return Response(
                {'detail': 'Invalid or expired refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
class AdminLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get('admin_refresh')

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response({'detail': 'Logged out successfully.'})
        response.delete_cookie(
            'admin_refresh',
            samesite='Lax'
        )
        return response