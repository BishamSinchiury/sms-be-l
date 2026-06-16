from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from organization.utils import get_org_from_request
from rbac.models import Role
from users.serializers.user_serializer import RoleMiniSerializer, UserCreateSerializer, ResetPasswordSerializer
from users.serializers.public_serializer import VerifyOTPSerializer
from users.models import CustomUser
from users.otp import store_otp, send_otp_email, verify_otp

class PublicRoleListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            org = get_org_from_request(request)
        except Exception:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)
        roles = Role.objects.filter(org=org).order_by('name')
        return Response(RoleMiniSerializer(roles, many=True).data)

class SignupView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            org = get_org_from_request(request)
        except Exception:
            return Response({'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserCreateSerializer(data=request.data, context={'org': org})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        user.is_verified = False
        user.status = CustomUser.Status.PENDING
        user.save(update_fields=['is_verified', 'status'])

        otp = store_otp(user.email, purpose='register')
        send_otp_email(user.email, otp, purpose='register')

        return Response({'detail': 'OTP sent to email.', 'email': user.email}, status=status.HTTP_201_CREATED)

class VerifyOTPView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        if not verify_otp(email, 'register', otp):
            return Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
            # OTP is verified, but admin approval is still required.
            user.status = CustomUser.Status.PENDING
            user.save(update_fields=['status'])
            return Response({'detail': 'Email verified. Pending admin approval.'}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


class ForgotPasswordView(APIView):
    """Step 1 — Request a password-reset OTP."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response(
                {'detail': 'Email is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Always return 200 so we don't leak whether the email exists
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'If that email is registered, an OTP has been sent.'},
                status=status.HTTP_200_OK
            )

        # Optionally block inactive / unverified accounts
        if not user.is_active:
            return Response(
                {'detail': 'If that email is registered, an OTP has been sent.'},
                status=status.HTTP_200_OK
            )

        otp = store_otp(user.email, purpose='reset_password')
        send_otp_email(user.email, otp, purpose='reset_password')

        return Response(
            {'detail': 'If that email is registered, an OTP has been sent.'},
            status=status.HTTP_200_OK
        )


class VerifyPasswordResetOTPView(APIView):
    """Step 2 — Verify OTP and receive a short-lived reset token."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        otp   = serializer.validated_data['otp']

        if not verify_otp(email, 'reset_password', otp):
            return Response(
                {'detail': 'Invalid or expired OTP.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Issue a short-lived, single-use token the client sends in step 3.
        # We reuse your OTP store so no extra model is needed.
        reset_token = store_otp(email, purpose='reset_password_token')

        return Response(
            {
                'detail': 'OTP verified.',
                'reset_token': reset_token,   # frontend holds this for step 3
            },
            status=status.HTTP_200_OK
        )


class ResetPasswordView(APIView):
    """Step 3 — Submit new password using the token from step 2."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email       = serializer.validated_data['email']
        reset_token = serializer.validated_data['reset_token']
        new_password = serializer.validated_data['new_password']

        # Validate the reset token (reuses the OTP verify logic)
        if not verify_otp(email, 'reset_password_token', reset_token):
            return Response(
                {'detail': 'Reset token is invalid or has expired. Please restart the process.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return Response({'detail': 'Password reset successful.'}, status=status.HTTP_200_OK)