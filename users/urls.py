from django.urls import path
from users import views

urlpatterns = [
    path('login/',    views.LoginView.as_view(),    name='login'),
    path('logout/',   views.LogoutView.as_view(),   name='logout'),
    path('auth/refresh/',  views.TokenRefreshView.as_view(), name='token-refresh'),
]