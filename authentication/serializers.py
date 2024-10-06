from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from django.core.exceptions import ValidationError
import imghdr
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from rest_framework.fields import ImageField


import logging

logger = logging.getLogger(__name__)
class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    This serializer handles the validation and creation of a new user.

    Attributes:
        password (CharField): The user's password, which is required and write-only.
        confirm_password (CharField): A confirmation of the user's password, required and write-only.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'confirm_password')

    def validate(self, attrs: dict) -> dict:
        """
        Validates the input data.

        Checks that the password and confirm_password fields match.

        Args:
            attrs (dict): The validated attributes containing user input.

        Returns:
            dict: The validated attributes.

        Raises:
            ValidationError: If the password and confirm_password fields do not match.
        """
        if attrs['password'] != attrs['confirm_password']:
            logger.error("Password and confirm_password fields do not match.")
            raise serializers.ValidationError({"password": ("Password fields didn't match.")})
        logger.info("User registration validation passed.")
        return attrs

    def create(self, validated_data: dict) -> CustomUser:
        """
        Creates a new user instance.

        Removes the confirm_password field and creates a user with the provided details.

        Args:
            validated_data (dict): The validated user data.

        Returns:
            CustomUser: The created user instance.
        """
        validated_data.pop('confirm_password')

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']  # This automatically hashes the password
        )
        logger.info(f"User {user.username} registered successfully.")
        return user
class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.

    This serializer validates the login credentials of a user.

    Attributes:
        email (EmailField): The user's email address, required for authentication.
        password (CharField): The user's password, write-only and required.
        remember_me (BooleanField): Optional flag indicating whether to remember the user session.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    remember_me = serializers.BooleanField(default=False)

    def validate(self, attrs: dict) -> dict:
        """
        Validates the login credentials.

        Checks that the email and password fields are present.

        Args:
            attrs (dict): The validated attributes containing user input.

        Returns:
            dict: The validated attributes.

        Raises:
            ValidationError: If the email or password fields are missing.
        """
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            logger.error("Validation failed: Missing email or password.")
            raise serializers.ValidationError({"error": "Email and password are required."})

        logger.info(f"Validation successful for email: {email}.")
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing user passwords.

    This serializer validates the old password and the new password for a user.

    Attributes:
        old_password (CharField): The user's current password, required for validation.
        new_password (CharField): The user's new password, required for the update.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, attrs: dict) -> dict:
        """
        Validates the old and new password.

        Ensures that both old and new passwords are provided and checks
        that the new password is different from the old password.

        Args:
            attrs (dict): The validated attributes containing user input.

        Returns:
            dict: The validated attributes.

        Raises:
            ValidationError: If the old password is the same as the new password.
        """
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')

        if old_password == new_password:
            logger.error("Validation failed: Old password and new password must be different.")
            raise serializers.ValidationError({"new_password": "New password cannot be the same as the old password."})

        logger.info("Password validation successful.")
        return attrs


class ResetPasswordEmailSerializer(serializers.Serializer):
    """
    Serializer for sending password reset emails.

    This serializer validates the email address provided for sending a password reset link.

    Attributes:
        email (EmailField): The user's email address, required for sending the reset link.
    """
    email = serializers.EmailField(required=True)
class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data.

    This serializer handles the serialization and deserialization of user
    information, including the profile image.

    Attributes:
        profile_image (ImageField): Optional image field for user profile pictures.
    """
    profile_image = serializers.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
            'profile_image'
        )

    def validate_profile_image(self, value: UploadedFile) -> UploadedFile:
        """
        Validates the uploaded profile image.

        This method checks that the uploaded image meets specific criteria:
        - File size must not exceed 2MB.
        - Dimensions must be within 1920x1080 pixels.

        Args:
            value (UploadedFile): The uploaded image file.

        Returns:
            UploadedFile: The validated image file.

        Raises:
            serializers.ValidationError: If the file size or dimensions are invalid.
        """
        logger.info("Validating profile image.")

        if isinstance(value, UploadedFile):
            # Check if the file size exceeds the limit (e.g., 2MB)
            max_size_mb = 2
            max_size_bytes = max_size_mb * 1024 * 1024
            if value.size > max_size_bytes:
                logger.error(f"Validation failed: Image file size ({value.size / (1024 * 1024):.2f} MB) exceeds {max_size_mb} MB.")
                raise serializers.ValidationError(f"Image file size must not exceed {max_size_mb} MB.")

            # Open the image file using PIL
            try:
                image = Image.open(value)
                # Check image dimensions (optional)
                max_width, max_height = 1920, 1080
                if image.width > max_width or image.height > max_height:
                    logger.error(f"Validation failed: Image dimensions ({image.width}x{image.height}) exceed {max_width}x{max_height} pixels.")
                    raise serializers.ValidationError(f"Image dimensions must be within {max_width}x{max_height} pixels.")
                logger.info("Profile image validated successfully.")
            except Exception as e:
                logger.exception("An error occurred while validating the image.")
                raise serializers.ValidationError("Invalid image file.")

        return value

class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for resetting the password.

    This serializer validates the new password and ensures
    that the new password matches the confirmed password.

    Attributes:
        new_password (str): The new password provided by the user, required for resetting.
        confirm_password (str): The confirmation of the new password, required for resetting.
    """
    new_password: str = serializers.CharField(required=True, write_only=True)
    confirm_password: str = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs: dict) -> dict:
        """
        Validate that the new password and confirm password match.

        Args:
            attrs (dict): A dictionary containing the input values.

        Raises:
            serializers.ValidationError: If the passwords do not match.

        Returns:
            dict: The validated attributes.
        """
        logger.info("Validating that the new password and confirm password match.")

        if attrs['new_password'] != attrs['confirm_password']:
            logger.error("Password validation failed: Passwords do not match.")
            raise serializers.ValidationError("Passwords do not match.")

        logger.info("Password validation successful: Passwords match.")
        return attrs

    def validate_new_password(self, value: str) -> str:
        """
        Validate the new password for minimum length.

        Args:
            value (str): The new password provided by the user.

        Raises:
            serializers.ValidationError: If the password is less than 8 characters.

        Returns:
            str: The validated new password.
        """
        logger.info("Validating the new password length.")

        if len(value) < 8:
            logger.error("Password validation failed: Password must be at least 8 characters long.")
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        logger.info("New password validation successful: Password meets length requirement.")
        return value
