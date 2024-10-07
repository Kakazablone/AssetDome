import logging
from django.db.models import Q
from rest_framework import filters
from rest_framework.request import Request
from django.db.models.query import QuerySet
from typing import Any, List
from django.http import Http404
from django.shortcuts import get_object_or_404
from .models import MajorCategory, MinorCategory, Location, Supplier, Employee, Department, Asset  # Assuming Asset model exists

# Configure logging
logger = logging.getLogger(__name__)

class DynamicFilter(filters.BaseFilterBackend):
    """Custom filter backend for dynamic filtering of querysets."""

    def filter_queryset(self, request: Request, queryset: QuerySet, view: Any) -> QuerySet:
        """Filters the queryset based on request parameters."""
        q_object = Q()

        # Apply all filters
        for name, value in request.GET.items():
            if name == 'match_all':
                continue  # Handle match_all separately
            field = self.get_field_from_name(name)
            if field:
                # If the field is a foreign key, resolve it by name
                if field in ['major_category', 'minor_category', 'department', 'location', 'supplier', 'employee']:
                    value = self.resolve_foreign_key(field, value)

                # Combine the Q object for filtering
                q_object &= self._apply_filter(field, value, self.get_allowed_lookups(field))

                # Log the filters applied
                logger.debug(f"Applied filter: {field} with value {value}. Current Q object: {q_object}")

        # Log final Q object before executing the query
        logger.debug(f"Final Q object: {q_object}")

        # Apply match_all logic if provided
        match_all = request.GET.get('match_all', 'true').lower() == 'true'
        result_queryset = queryset.filter(q_object).distinct() if match_all else queryset.filter(q_object | Q()).distinct()

        logger.info(f"Queryset filtered with match_all={match_all}. Result count: {result_queryset.count()}")
        return result_queryset

    def resolve_foreign_key(self, field: str, value: str) -> int:
        model_mapping = {
            'major_category': MajorCategory,
            'minor_category': MinorCategory,
            'department': Department,
            'location': Location,
            'supplier': Supplier,
            'employee': Employee
        }

        model = model_mapping.get(field)
        if model:
            if field == 'employee':
                # Split names by space for employees
                names = value.split()
                employee_filter = Q()

                for name in names:
                    employee_filter |= (
                        Q(first_name__icontains=name) | 
                        Q(middle_name__icontains=name) | 
                        Q(last_name__icontains=name)
                    )

                # Return a list of matching employee IDs
                employees = model.objects.filter(employee_filter)
                logger.debug(f"Resolved employee IDs: {list(employees.values_list('id', flat=True))}")
                return list(employees.values_list('id', flat=True))  # Return a list of IDs
        try:
            obj = get_object_or_404(model, name=value.strip())
            logger.debug(f"Resolved foreign key for {field} with name {value}: {obj.id}")
            return [obj.id]  # Return a list with a single ID for other fields
        except Http404:
            logger.warning(f"{field} with name {value} not found.")
            return None  # Or handle the case where the object is not found

        return None

    def _apply_filter(self, field: str, value: Any, allowed_lookups: List[str]) -> Q:
        if field == 'employee':  # Allow lists for these fields
            return Q(**{f"{field}__in": value})  # Use __in for list of IDs
        
        if field in ['supplier', 'major_category', 'minor_category', 'department', 'location']:
            # Ensure single value is not wrapped in a list
            if isinstance(value, list):
                if len(value) == 1:
                    value = value[0]

        lookup = 'exact'

        # Handle range lookups specifically
        if isinstance(value, str) and "__" in value:
            value, lookup = value.split("__")

        if lookup in OPERATOR_MAP:
            lookup = OPERATOR_MAP[lookup]

        if lookup in allowed_lookups:
            if lookup == 'range':
                # Ensure value is properly formatted for range
                if isinstance(value, str):
                    try:
                        value = list(map(int, value.split(',')))  # Convert to integers
                        return Q(**{f"{field}__range": (value[0], value[1])})
                    except ValueError:
                        logger.error(f"Error converting range values: {value}")
                        return Q()  # Return an empty Q object on failure

            return Q(**{f"{field}__{lookup}": value})

        return Q()

    def get_field_from_name(self, name: str) -> str:
        """Maps request parameter names to model field names."""
        field_map = {
            'asset_code': 'asset_code',
            'barcode': 'barcode',
            'rfid': 'rfid',
            'description': 'description',
            'serial_number': 'serial_number',
            'model_number': 'model_number',
            'asset_type': 'asset_type',
            'major_category': 'major_category',
            'minor_category': 'minor_category',
            'location': 'location',
            'department': 'department',
            'employee': 'employee',
            'supplier': 'supplier',
            'economic_life': 'economic_life',
            'purchase_price': 'purchase_price',
            'net_book_value': 'net_book_value',
            'revalued_amount': 'revalued_amount',
            'units': 'units',
            'year_of_purchase': 'year_of_purchase',
            'date_placed_in_service': 'date_placed_in_service',
            'condition': 'condition',
            'status': 'status',
            'depreciation_method': 'depreciation_method',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            'disposed_at': 'disposed_at',
            'is_disposed': 'is_disposed'
        }
        return field_map.get(name)

    def get_allowed_lookups(self, field: str) -> List[str]:
        """Returns the allowed lookups for a specific field."""
        lookups = {
            'asset_code': ['exact', 'icontains', 'iexact'],
            'barcode': ['exact', 'icontains', 'iexact'],
            'rfid': ['exact', 'icontains', 'iexact'],
            'description': ['icontains'],
            'serial_number': ['exact', 'icontains', 'iexact'],
            'model_number': ['exact', 'icontains', 'iexact'],
            'asset_type': ['exact'],
            'major_category': ['exact'],
            'minor_category': ['exact'],
            'location': ['exact'],
            'department': ['exact'],
            'employee': ['exact'],  # Filtering for employee based on foreign key ID
            'supplier': ['exact'],
            'economic_life': ['exact', 'lt', 'lte', 'gt', 'gte'],
            'purchase_price': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'net_book_value': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'revalued_amount': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'units': ['exact', 'lt', 'lte', 'gt', 'gte'],
            'year_of_purchase': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'date_placed_in_service': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'condition': ['exact'],
            'status': ['exact'],
            'depreciation_method': ['exact'],
            'created_at': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'updated_at': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'disposed_at': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'is_disposed': ['exact']
        }
        return lookups.get(field, ['exact'])

# Mapping operators from user-friendly UI terms to lookups
OPERATOR_MAP = {
    'equals': 'exact',
    'not equals': 'exclude',
    'contains': 'icontains',
    'does not contain': 'exclude__icontains',
    'less than': 'lt',
    'greater than': 'gt',
    'less than or equal to': 'lte',
    'greater than or equal to': 'gte',
    'within range': 'range',
    'outside range': 'exclude__range'
}
