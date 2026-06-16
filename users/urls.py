from django.urls import path
from users import views

urlpatterns = [
    path('login/',           views.LoginView.as_view(),          name='login'),
    path('admin/login/',     views.AdminLoginView.as_view(),     name='admin-login'),
    path('admin/verify/',    views.AdminOTPVerifyView.as_view(), name='admin-otp-verify'),
    path('logout/',          views.LogoutView.as_view(),         name='logout'),
    path('refresh/',         views.TokenRefreshView.as_view(),   name='token-refresh'),
    path('admin/refresh/',   views.AdminTokenRefreshView.as_view(),   name='admin-token-refresh'),
    path('admin/logout/',    views.AdminLogoutView.as_view(),         name='admin-logout'),
    path('me/',              views.MeView.as_view(),                  name='me'),

    path('users/',                    views.UserListCreateView.as_view(), name='user-list-create'),
    path('users/<uuid:user_uuid>/',   views.UserDetailView.as_view(),     name='user-detail'),
    path('roles/',                    views.RoleListView.as_view(),       name='role-list'),

    # Public / Signup
    path('public-roles/',             views.PublicRoleListView.as_view(), name='public-role-list'),
    path('signup/',                   views.SignupView.as_view(),         name='signup'),
    path('signup/verify/',            views.VerifyOTPView.as_view(),      name='signup-verify'),

    # urls.py
    path('forgot-password/',        views.ForgotPasswordView.as_view()),
    path('verify-reset-otp/',       views.VerifyPasswordResetOTPView.as_view()),
    path('reset-password/',         views.ResetPasswordView.as_view()),
]