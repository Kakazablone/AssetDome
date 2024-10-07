import logging
import re
from typing import Optional, List, Callable
from django.http import JsonResponse
from rest_framework.request import Request

logger = logging.getLogger(__name__)

class UserActivityTrackingMiddleware:
    """
    Middleware to track user activity by logging their recent asset views.
    Stores recent asset views in cookies and ensures that the list is limited
    to the last 5 unique assets.
    """

    def __init__(self, get_response: Callable):
        """
        Initializes the middleware with the next middleware or view in the chain.

        Args:
            get_response (Callable): The next middleware or view in the chain.
        """
        self.get_response = get_response

    def __call__(self, request: Request) -> JsonResponse:
        """
        Adds the current asset to the user's recent activity list stored in cookies,
        limiting the list to the 5 most recent unique assets.

        Args:
            request (Request): The incoming HTTP request object.

        Returns:
            JsonResponse: The HTTP response with updated cookies if necessary.
        """
        response = self.get_response(request)

        if request.user.is_authenticated:
            current_asset_id = self.get_asset_id_from_url(request.path)

            if current_asset_id:
                recent_activity = self.get_recent_activity(request.COOKIES.get('recent_activity', ''))
                asset_activity = f"asset:{current_asset_id}"
                recent_activity = self.update_recent_activity(recent_activity, asset_activity)

                # Update the cookie with recent activity
                response.set_cookie('recent_activity', '|'.join(recent_activity), max_age=60 * 60 * 24)  # 1 day
                logger.info(f"Updated recent activity for user {request.user.username}: {recent_activity}")

        return response

    def get_recent_activity(self, recent_activity_str: str) -> List[str]:
        """
        Converts the recent activity cookie string into a list of activities.

        Args:
            recent_activity_str (str): The string from the recent activity cookie.

        Returns:
            List[str]: A list of recent activities.
        """
        return [activity for activity in recent_activity_str.split('|') if activity]

    def update_recent_activity(self, recent_activity: List[str], asset_activity: str) -> List[str]:
        """
        Updates the recent activity list, ensuring it contains only unique entries.

        Args:
            recent_activity (List[str]): The current list of recent activities.
            asset_activity (str): The current asset activity to add.

        Returns:
            List[str]: The updated list of recent activities.
        """
        recent_activity = [activity for activity in recent_activity if activity != asset_activity]  # Remove if already present
        recent_activity.insert(0, asset_activity)  # Add the latest activity
        return recent_activity[:5]  # Limit to 5 items

    def get_asset_id_from_url(self, path: str) -> Optional[str]:
        """
        Extracts the asset ID from the request URL path.

        Args:
            path (str): The request URL path.

        Returns:
            Optional[str]: The extracted asset ID if present, otherwise None.
        """
        match = re.search(r'/api/assets/(?P<asset_id>\d+)/', path)
        return match.group('asset_id') if match else None


class PaginationMiddleware:
    """
    Middleware to track and set the current page number in cookies for paginated views.
    The page number is retrieved from the query parameters or cookies, and it is set in the response.
    """

    def __init__(self, get_response: Callable):
        """
        Initializes the middleware with the next middleware or view in the chain.

        Args:
            get_response (Callable): The next middleware or view in the chain.
        """
        self.get_response = get_response

    def __call__(self, request: Request) -> JsonResponse:
        """
        Retrieves the current page from the request query parameters or cookies
        and sets it as a cookie in the response.

        Args:
            request (Request): The incoming HTTP request object.

        Returns:
            JsonResponse: The HTTP response with the current page cookie set.
        """
        response = self.get_response(request)

        if request.user.is_authenticated:
            current_page = request.GET.get('page', request.COOKIES.get('current_page', 1))

            # Set the cookie for the current page
            response.set_cookie('current_page', current_page, max_age=60 * 60 * 24)  # 1 day
            logger.info(f"Set current page for user {request.user.username}: {current_page}")

        return response
