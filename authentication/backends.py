from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from typing import Optional

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email address
    instead of a username.

    This backend overrides the default authentication method to retrieve the user using their
    email address and checks the provided password against the stored password.
    """

    def authenticate(self, request: Optional[object], username: Optional[str] = None,
                    password: Optional[str] = None, **kwargs) -> Optional[object]:
        """
        Authenticate a user based on the provided email and password.

        Args:
            request (Optional[object]): The request object.
            username (Optional[str]): The email address of the user.
            password (Optional[str]): The password of the user.
            **kwargs: Additional keyword arguments.

        Returns:
            Optional[object]: The authenticated user instance if successful, None otherwise.
        """
        UserModel = get_user_model()

        try:
            # Use email instead of username for authentication
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None

        # Check if the password matches
        if user.check_password(password):
            return user
        return None
