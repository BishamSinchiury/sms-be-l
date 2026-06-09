from django.urls import path
from users import views

urlpatterns = [
    path('login/',           views.LoginView.as_view(),          name='login'),
    path('admin/login/',     views.AdminLoginView.as_view(),     name='admin-login'),
    path('admin/verify/',    views.AdminOTPVerifyView.as_view(), name='admin-otp-verify'),
    path('logout/',          views.LogoutView.as_view(),         name='logout'),
    path('refresh/',         views.TokenRefreshView.as_view(),   name='token-refresh'),
    path('admin/refresh/',   views.AdminTokenRefreshView.as_view(),   name='admin-token-refresh'),
    path('auth/admin/logout/',    views.AdminLogoutView.as_view(), name='admin-logut'),
]