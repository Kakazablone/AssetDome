from typing import Callable, Dict, Any

class JWTAuthMiddleware:
    """
    Middleware to handle JWT authentication by extracting the access token
    from cookies and adding it to the Authorization header of the request.

    This middleware allows the application to authenticate users using JWTs stored
    in cookies, making it easier to work with token-based authentication.
    """

    def __init__(self, get_response: Callable[[Any], Any]) -> None:
        """
        Initialize the JWTAuthMiddleware.

        Args:
            get_response (Callable[[Any], Any]): The next middleware or view in the
            processing chain.
        """
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """
        Process the request and inject the JWT access token into the Authorization header.

        Args:
            request (Any): The incoming HTTP request object.

        Returns:
            Any: The HTTP response object after processing the request.
        """
        # Check for JWT access token in cookies
        access_token = request.COOKIES.get('access_token')
        if access_token:
            # Add the access token to the Authorization header
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'

        # Call the next middleware or view in the chain
        response = self.get_response(request)
        return response
