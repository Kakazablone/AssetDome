from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class StandardResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class to set standard pagination parameters.

    Attributes:
        page_size (int): The default number of items per page.
        page_size_query_param (str): The query parameter to specify custom page sizes.
        max_page_size (int): The maximum number of items allowed per page.
    """
    page_size: int = 10
    page_size_query_param: str = 'page_size'
    max_page_size: int = 100

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'next_page_number': self.page.number + 1 if self.page.has_next() else None,
            'previous': self.get_previous_link(),
            'previous_page_number': self.page.number - 1 if self.page.has_previous() else None,
            'results': data,
        })
