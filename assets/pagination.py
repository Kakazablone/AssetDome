from rest_framework.pagination import PageNumberPagination

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
