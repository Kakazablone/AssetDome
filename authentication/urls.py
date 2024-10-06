from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterViewSet, LoginViewSet, LogoutViewSet, ChangePasswordViewSet,
    ResetPasswordViewSet, UserViewSet, TokenRefreshViewSet, ResetPasswordConfirmViewSet
)
from django.conf import settings
from django.conf.urls.static import static

# Initialize the default router
router = DefaultRouter()
# Register API viewsets with their respective base names
router.register('register', RegisterViewSet, basename='register')
router.register('login', LoginViewSet, basename='login')
router.register('logout', LogoutViewSet, basename='logout')
router.register('reset_password', ResetPasswordViewSet, basename='reset_password')
router.register('users', UserViewSet, basename='users')
router.register('token_refresh', TokenRefreshViewSet, basename='token_refresh')

urlpatterns = [
    path('', include(router.urls)),  # Include the registered router URLs
    path('change_password/', ChangePasswordViewSet.as_view({'put': 'update'}), name='change_password'),
    path('reset_password_confirm/<uidb64>/<token>/', ResetPasswordConfirmViewSet.as_view({'post': 'create'}), name='reset-password-confirm')
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
