from rest_framework.permissions import BasePermission

class IsGetOnly(BasePermission):
    """
    Custom permission class that only allows GET requests.

    This permission class checks the request method and grants
    permission only if the method is GET.
    """

    def has_permission(self, request, view):
        """
        Check if the request method is GET.

        Args:
            request: The HTTP request object.
            view: The view that is being accessed.

        Returns:
            bool: True if the request method is GET, False otherwise.
        """
        return request.method == 'GET'
