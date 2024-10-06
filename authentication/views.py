from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import authenticate
from .models import CustomUser
from .serializers import RegisterSerializer, LoginSerializer, ChangePasswordSerializer, ResetPasswordEmailSerializer, ResetPasswordSerializer
from django.core.mail import send_mail
import logging

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .models import CustomUser
from .serializers import UserSerializer
import os
from datetime import timedelta
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth import get_user_model
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.exceptions import ValidationError



User = get_user_model()
logger = logging.getLogger(__name__)

class RegisterViewSet(viewsets.GenericViewSet):
    """
    A viewset for registering new users.

    This viewset provides a `create` action for user registration.

    Attributes:
        serializer_class (RegisterSerializer): The serializer class used for validating user registration data.
        permission_classes (list): The list of permission classes to allow any user to access the registration endpoint.
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request) -> Response:
        """
        Create a new user.

        This method handles the user registration process, validating the
        provided data and saving the new user to the database.

        Args:
            request: The HTTP request containing user registration data.

        Returns:
            Response: A response indicating the registration status.

        Raises:
            ValidationError: If the provided data is invalid.
        """
        logger.info("Received a registration request from %s.", request.data.get('email', 'unknown'))

        # Initialize the serializer with the provided data
        serializer = self.get_serializer(data=request.data)

        # Validate the data and raise an exception if invalid
        try:
            serializer.is_valid(raise_exception=True)
            logger.info("User registration data is valid.")
        except ValidationError as e:
            logger.error("User registration failed: %s", e)
            return Response({"errors": e.detail}, status=status.HTTP_400_BAD_REQUEST)

        # Save the new user to the database
        user = serializer.save()
        logger.info("User registered successfully: %s", user.email)

        # Return a success response
        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)

class LoginViewSet(viewsets.GenericViewSet):
    """
    A viewset for user login.

    This viewset provides a `create` action for user authentication.

    Attributes:
        serializer_class (LoginSerializer): The serializer class used for validating user login data.
        permission_classes (list): The list of permission classes to allow any user to access the login endpoint.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def create(self, request) -> Response:
        """
        Log a user in and issue access and refresh tokens.

        This method authenticates the user using the provided login credentials,
        generates access and refresh tokens, and stores them in HttpOnly cookies
        for security.

        Args:
            request: The HTTP request containing user login credentials.

        Returns:
            Response: A response containing the status of the login attempt,
                      including access and refresh tokens stored in cookies on success.

        Raises:
            ValidationError: If the provided login credentials are invalid.
        """
        logger.info("Login attempt received for email: %s", request.data.get('email', 'unknown'))

        # Initialize the serializer with the provided data
        serializer = self.get_serializer(data=request.data)

        # Validate the data and raise an exception if invalid
        serializer.is_valid(raise_exception=True)
        logger.info("User login data is valid.")

        # Extract validated data
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')
        remember_me = serializer.validated_data.get('remember_me')

        # Authenticate the user using the provided email and password
        user = authenticate(username=email, password=password)

        if user is not None:
            logger.info("User %s authenticated successfully.", email)

            # Determine access and refresh token lifetimes based on 'remember_me' flag
            access_token_lifetime = (
                settings.SIMPLE_JWT['REMEMBER_ME_ACCESS_TOKEN_LIFETIME']
                if remember_me else settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
            )
            refresh_token_lifetime = (
                settings.SIMPLE_JWT['REMEMBER_ME_REFRESH_TOKEN_LIFETIME']
                if remember_me else settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
            )

            # Create access and refresh tokens
            access_token = AccessToken.for_user(user)
            access_token.set_exp(lifetime=access_token_lifetime)

            refresh_token = RefreshToken.for_user(user)
            refresh_token['remember_me'] = remember_me  # Store remember_me in the refresh token
            refresh_token.set_exp(lifetime=refresh_token_lifetime)

            # Prepare response with a success message
            response = Response({'message': 'Login successful'})

            # Store the tokens in HttpOnly cookies for security
            response.set_cookie(
                key='access_token',
                value=str(access_token),
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=access_token_lifetime.total_seconds(),
            )
            response.set_cookie(
                key='refresh_token',
                value=str(refresh_token),
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=refresh_token_lifetime.total_seconds(),
            )

            logger.info("Access and refresh tokens set for user %s.", email)
            return response
        else:
            logger.warning("Invalid login attempt for email: %s", email)
            # Return an error response if authentication fails
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutViewSet(viewsets.GenericViewSet):
    """
    A viewset for user logout.

    This viewset provides a `create` action for logging out the user
    by blacklisting the refresh token and removing it from cookies.

    Attributes:
        permission_classes (list): The list of permission classes to restrict access to authenticated users only.
    """
    # Only authenticated users can access this view
    permission_classes = [IsAuthenticated]

    def create(self, request) -> Response:
        """
        Log a user out by blacklisting their refresh token.

        This method retrieves the refresh token from the user's cookies,
        blacklists it to prevent further use, and deletes both access and
        refresh tokens from the cookies.

        Args:
            request: The HTTP request containing the refresh token in cookies.

        Returns:
            Response: A response indicating the status of the logout attempt,
                      including success or error messages.

        Raises:
            Exception: If there is an issue with blacklisting the token or deleting cookies.
        """
        # Retrieve the refresh token from cookies
        refresh_token = request.COOKIES.get('refresh_token')

        logger.info("Logout attempt received. Refresh token: %s", refresh_token)

        # Check if the refresh token exists
        if not refresh_token:
            logger.warning("Logout failed: 'refresh' token is required.")
            return Response({"error": "'refresh' token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create a RefreshToken object using the retrieved token
            token = RefreshToken(refresh_token)

            # Blacklist the refresh token to prevent further use
            token.blacklist()
            logger.info("Refresh token blacklisted successfully.")

            # Prepare a response indicating successful logout
            response = Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

            # Remove the access and refresh tokens from cookies
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            logger.info("Access and refresh tokens removed from cookies.")

            return response
        except Exception as e:
            logger.error("Logout failed: %s", str(e))
            # Handle any exceptions that occur and return an error response
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
class ChangePasswordViewSet(viewsets.GenericViewSet):
    """
    A viewset for changing user passwords.

    This viewset provides an `update` action for authenticated users
    to change their password by validating the old password and setting a new one.

    Attributes:
        permission_classes (list): The list of permission classes to restrict access to authenticated users only.
        serializer_class (serializer): The serializer class used for validating password change data.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def update(self, request, *args, **kwargs) -> Response:
        """
        Enable a user to change their password when they need to.

        This method validates the old password and updates it with a new password
        if the old password is correct. Logs relevant events during the process.

        Args:
            request: The HTTP request containing the old and new password.

        Returns:
            Response: A response indicating the status of the password change attempt.

        Raises:
            serializers.ValidationError: If the old password is incorrect or new password is invalid.
        """
        user = request.user
        serializer = self.get_serializer(data=request.data)

        # Validate the data and raise an exception if invalid
        serializer.is_valid(raise_exception=True)
        logger.info("User %s is attempting to change their password.", user.username)

        # Check if the old password is correct
        if not user.check_password(serializer.data['old_password']):
            logger.warning("Password change failed for user %s: old password is incorrect.", user.username)
            return Response({"old_password": "Wrong password."}, status=status.HTTP_400_BAD_REQUEST)

        # Set the new password and save the user
        user.set_password(serializer.data['new_password'])
        user.save()
        logger.info("User %s successfully changed their password.", user.username)

        return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)

class ResetPasswordViewSet(viewsets.GenericViewSet):
    """
    A viewset for handling password reset requests.

    This viewset allows users to request a password reset link by providing
    their registered email address. If the email is valid, an email with
    a reset link is sent to the user.
    """
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordEmailSerializer

    def create(self, request) -> Response:
        """
        Handle password reset link requests.

        This method validates the input email address, checks if a user with
        that email exists, and sends a password reset link if so.

        Args:
            request: The HTTP request containing the email address.

        Returns:
            Response: A response indicating the result of the password reset link request.

        Raises:
            serializers.ValidationError: If the input email is invalid.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.data['email']

        # Check if the user exists with the provided email
        user = CustomUser.objects.filter(email=email).first()
        if user:
            # Generate uidb64 and token for the reset link
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))  # Removed .decode()
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(f'/auth/reset_password_confirm/{uidb64}/{token}/')

            # Render the email template with context
            context = {
                'user': user,
                'reset_link': reset_link
            }
            email_body = render_to_string('password_reset_email.html', context)

            # Create and send the email
            email_message = EmailMessage(
                subject="Password Reset Request",
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email_message.content_subtype = 'html'  # Ensure the email is sent as HTML
            email_message.send()

            # Log the password reset request
            logger.info("Password reset link sent to %s", user.email)

            return Response({"message": "Password reset link sent"}, status=status.HTTP_200_OK)

        # Log the attempt for a non-existent email
        logger.warning("Password reset request for non-existent email: %s", email)
        return Response({"error": "User with this email not found"}, status=status.HTTP_404_NOT_FOUND)
class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing CustomUser model instances.

    This viewset provides the ability to perform CRUD operations on users,
    including updating profile images. When a user updates their profile
    image, the old image is deleted from the server to free up space.
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs) -> Response:
        """
        Update an existing user instance, including the profile image.

        If a new profile image is uploaded, the old image is deleted from the
        server. The method first stores the path of the old profile image,
        calls the parent class's update method to handle the update, and
        finally, if the profile image has changed, the old image file is
        deleted from the filesystem.

        Args:
            request (HttpRequest): The HTTP request object containing the new user data.
            *args: Variable length argument list for additional positional arguments.
            **kwargs: Arbitrary keyword arguments for additional named parameters.

        Returns:
            Response: The response object with the updated user data.

        Raises:
            OSError: If an error occurs while deleting the old profile image.
        """
        instance = self.get_object()
        old_image = instance.profile_image.path if instance.profile_image else None

        # Call the parent class's update method to handle the update
        response = super().update(request, *args, **kwargs)

        # Check if the profile image has changed
        new_image = instance.profile_image.path if instance.profile_image else None
        if old_image and new_image and old_image != new_image:
            try:
                if os.path.isfile(old_image):  # Check if the file exists before attempting to delete
                    os.remove(old_image)
                    logger.info("Old profile image deleted: %s", old_image)
                else:
                    logger.warning("Old profile image not found: %s", old_image)
            except OSError as e:
                logger.error("Error deleting old profile image: %s", e)

        return response


class TokenRefreshViewSet(viewsets.GenericViewSet):
    """
    A viewset that handles the creation of a new access token from a refresh token.

    This viewset is responsible for accepting a refresh token from cookies
    and issuing a new access token. It handles scenarios where the token
    is missing, invalid, or expired. The token expiration depends on whether
    the "remember me" feature is set during login.
    """
    permission_classes = [AllowAny]

    def create(self, request) -> Response:
        """
        Create a new access token from a refresh token.

        This method retrieves the refresh token from the request cookies,
        validates it, and issues a new access token. If the refresh token is
        associated with the "remember me" option, the access token lifetime
        will be extended accordingly.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: A response containing the new access token if the refresh
            token is valid, or an error message if the refresh token is missing
            or invalid.
        """
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            logger.warning("Refresh token is missing from the cookies.")
            return Response({"error": "'refresh' token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create a new RefreshToken object from the refresh token
            token = RefreshToken(refresh_token)
            remember_me = token.get('remember_me', False)  # Get remember_me from the refresh token

            # Retrieve the user instance
            user_id = token['user_id']
            user = CustomUser.objects.get(id=user_id)  # Fetch the user instance

            # Set the access token lifetime based on remember_me
            access_token_lifetime = (
                settings.SIMPLE_JWT['REMEMBER_ME_ACCESS_TOKEN_LIFETIME']
                if remember_me else settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
            )

            # Create a new access token with the specified lifetime
            new_access_token = AccessToken.for_user(user)
            new_access_token.set_exp(lifetime=access_token_lifetime)

            # Prepare response with new access token
            response = Response({'access': str(new_access_token)}, status=status.HTTP_200_OK)
            response.set_cookie(
                key='access_token',
                value=str(new_access_token),
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=access_token_lifetime.total_seconds()
            )

            logger.info(f"New access token issued for user: {user.email}")
            return response

        except TokenError as e:
            logger.error(f"Token error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            logger.error(f"User with id {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResetPasswordConfirmViewSet(viewsets.GenericViewSet):
    """
    A viewset for confirming password reset and updating the new password.

    This viewset handles the process of verifying a password reset token
    and updating the user's password. It validates the incoming request data
    and checks the token's validity before saving the new password.
    """
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    def create(self, request, uidb64, token) -> Response:
        """
        Confirm the password reset and update the user's password.

        This method decodes the user ID from the provided base64 string,
        checks the validity of the reset token, and updates the user's password
        if the token is valid.

        Args:
            request (HttpRequest): The HTTP request containing the new password.
            uidb64 (str): The base64 encoded user ID.
            token (str): The password reset token.

        Returns:
            Response: A response indicating the status of the password reset attempt.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            logger.warning(f"Invalid uidb64 provided: {uidb64}")
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            # Set the new password and save the user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            logger.info(f"Password has been reset successfully for user: {user.email}")
            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)

        logger.warning(f"Invalid token or user ID for uid: {uid} with token: {token}")
        return Response({"error": "Invalid token or user ID."}, status=status.HTTP_400_BAD_REQUEST)
