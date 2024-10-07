from rest_framework import viewsets
from .models import (
    Asset, MajorCategory, MinorCategory, Department, Employee, Supplier, Location
)
from .serializers import (
    AssetSerializer, MajorCategorySerializer, MinorCategorySerializer,
    DepartmentSerializer, EmployeeSerializer, SupplierSerializer, LocationSerializer, DisposedAssetSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
import os
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.apps import apps
from .utils import generate_csv, generate_pdf, generate_excel, convert_to_naive_datetime, import_assets_from_file, FilterMixin
import logging
from django.contrib.auth import get_user_model
import pandas as pd
from datetime import datetime
from django.db.models import Sum, Count, QuerySet
from .pagination import StandardResultsSetPagination
from typing import Any, List, Dict, Optional
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from .filters import DynamicFilter
from .permissions import IsGetOnly
from .filters import DynamicFilter

from .signals import import_completed


User = get_user_model()
logger = logging.getLogger(__name__)

# class StandardResultsSetPagination(PageNumberPagination):
#     page_size = 10
#     page_size_query_param = 'page_size'
#     max_page_size = 100

class AssetViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing assets.
    
    Provides create, retrieve, update, and destroy actions for the Asset model.
    Utilizes pagination and enforces authentication for all actions.
    """

    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = (DynamicFilter,)

    def get_queryset(self) -> QuerySet:
        """
        Override get_queryset to cache active assets.
        
        The queryset is cached to improve performance. If the cache is empty,
        the queryset is fetched from the database and stored in the cache.
        
        Returns:
            QuerySet: The queryset of active (non-disposed) assets.
        """
        cache_key = 'active_assets'
        cached_queryset_ids = cache.get(cache_key)

        # Build the base queryset
        queryset = Asset.objects.filter(is_disposed=False).order_by('id')

        # Apply dynamic filters if they exist
        for filter_backend in self.filter_backends:
            queryset = filter_backend().filter_queryset(self.request, queryset, self)

        # If the queryset is cached, retrieve the objects by their IDs
        if cached_queryset_ids:
            logger.debug(f"Retrieving cached queryset for active assets: {cached_queryset_ids}")
            queryset = queryset.filter(id__in=cached_queryset_ids)

        else:
            # Fetch the queryset from the database and cache the IDs
            logger.debug("Caching active asset IDs")
            cache.set(cache_key, list(queryset.values_list('id', flat=True)), 60 * 15)

        return queryset

    def list(self, request, *args, **kwargs) -> Response:
        """
        Override the list method to use cached queryset.

        Returns a paginated response of active assets using a cached queryset.
        
        Args:
            request (HttpRequest): The incoming HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A paginated response of serialized active assets.
        """
        queryset = self.get_queryset()  # Use cached queryset
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.info("Returning paginated response for active assets.")
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        logger.info("Returning unpaginated response for active assets.")
        return Response(serializer.data)

    def perform_create(self, serializer):
        """
        Saves a new asset instance and associates it with the user.
        Invalidates the active assets cache.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save(created_by=self.request.user)
        logger.info(f"Created asset by user {self.request.user.username}.")
        cache.delete('active_assets')  # Clear active assets cache
        logger.debug("Cleared active assets cache after creation.")

    def perform_update(self, serializer):
        """
        Saves updates to an existing asset instance and associates it with the user.
        Invalidates the active assets cache.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save(updated_by=self.request.user)
        logger.info(f"Updated asset by user {self.request.user.username}.")
        cache.delete('active_assets')  # Clear active assets cache
        logger.debug("Cleared active assets cache after update.")

    def partial_update(self, request, *args, **kwargs) -> Response:
        """
        Override partial_update to handle asset disposal and undisposal.

        This method updates the asset's disposal status. If the asset is being disposed,
        it captures the disposal time and user. If it is being undisposed, it clears 
        the disposal time and captures who undisposed the asset.

        Returns:
            Response: A response indicating the result of the update operation.
        """
        asset = self.get_object()  # Get the asset instance to update

        # Check if the request data includes 'is_disposed'
        is_disposed = request.data.get('is_disposed', asset.is_disposed)

        if is_disposed:  # Asset is being disposed
            return self.handle_disposal(asset, request)

        # If not being disposed, handle normal updates
        serializer = self.get_serializer(asset, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def handle_disposal(self, asset, request) -> Response:
        """
        Handle the disposal of an asset.

        This method updates the asset's disposal status, capturing the disposal time
        and the user performing the action.

        Args:
            asset (Asset): The asset instance to be disposed.
            request (Request): The request containing the disposal information.

        Returns:
            Response: A response indicating the result of the disposal operation.
        """
        serializer = DisposedAssetSerializer(asset, data=request.data, partial=True)

        if serializer.is_valid():
            asset.is_disposed = True
            asset.disposed_at = timezone.now()
            asset.disposed_by = request.user  # Capture who disposed the asset
            asset.save()  # Save the updated asset

            logger.info(f"Asset {asset.asset_code} disposed by {request.user.username}.")
            cache.delete('active_assets')  # Clear active assets cache
            logger.debug("Cleared active assets cache after disposal.")

            return Response({"message": "Asset disposed successfully."}, status=status.HTTP_200_OK)

        logger.error(f"Failed to dispose asset {asset.asset_code}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs) -> Response:
        """
        Override destroy to clear cache when an asset is deleted.
        
        Deletes an asset and invalidates the active assets cache.

        Args:
            request (HttpRequest): The incoming HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response to the delete request.
        """
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"Deleted asset with ID: {kwargs['pk']} by user {request.user.username}.")
        
        # Invalidate the active assets cache after deletion
        cache.delete('active_assets')
        logger.debug("Cleared active assets cache after deletion.")

        return response

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Override filter_queryset to handle empty strings in filters.
        
        Args:
            queryset (QuerySet): The queryset to filter.

        Returns:
            QuerySet: The filtered queryset based on request parameters.
        """
        filters = self.request.query_params
        logger.debug("Applying filters to queryset: %s", filters)

        for key, value in filters.items():
            if key and value:  # Only apply filters that are not empty strings
                logger.debug(f"Applying filter: {key}={value}")
                queryset = queryset.filter(**{key: value})

        return queryset

class MajorCategoryViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing Major Categories.

    Provides `create`, `retrieve`, `update`, and `destroy` actions for the MajorCategory model.
    """

    queryset = MajorCategory.objects.all().order_by('id')
    serializer_class = MajorCategorySerializer

    def perform_create(self, serializer):
        """
        Create a new MajorCategory instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Created MajorCategory: %s", serializer.data)

    def perform_update(self, serializer):
        """
        Update an existing MajorCategory instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Updated MajorCategory: %s", serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a MajorCategory instance.

        Args:
            request (HttpRequest): The incoming HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response to the delete request.
        """
        response = super().destroy(request, *args, **kwargs)
        logger.info("Deleted MajorCategory with ID: %s", kwargs['pk'])
        return response


class MinorCategoryViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing Minor Categories.

    Provides `create`, `retrieve`, `update`, and `destroy` actions for the MinorCategory model.
    """

    queryset = MinorCategory.objects.all().order_by('id')
    serializer_class = MinorCategorySerializer

    def perform_create(self, serializer):
        """
        Create a new MinorCategory instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Created MinorCategory: %s", serializer.data)

    def perform_update(self, serializer):
        """
        Update an existing MinorCategory instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Updated MinorCategory: %s", serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a MinorCategory instance.

        Args:
            request (HttpRequest): The incoming HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response to the delete request.
        """
        response = super().destroy(request, *args, **kwargs)
        logger.info("Deleted MinorCategory with ID: %s", kwargs['pk'])
        return response


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing Departments.

    Provides `create`, `retrieve`, `update`, and `destroy` actions for the Department model.
    """

    queryset = Department.objects.all().order_by('id')
    serializer_class = DepartmentSerializer

    def perform_create(self, serializer):
        """
        Create a new Department instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Created Department: %s", serializer.data)

    def perform_update(self, serializer):
        """
        Update an existing Department instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Updated Department: %s", serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a Department instance.

        Args:
            request (HttpRequest): The incoming HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response to the delete request.
        """
        response = super().destroy(request, *args, **kwargs)
        logger.info("Deleted Department with ID: %s", kwargs['pk'])
        return response

class EmployeeViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing Employees.

    Provides `create`, `retrieve`, `update`, and `destroy` actions for the Employee model.
    """

    queryset = Employee.objects.all().order_by('id')
    serializer_class = EmployeeSerializer

    def update(self, request, *args, **kwargs) -> Response:
        """
        Update an existing Employee instance.

        This method overrides the default update behavior to handle
        the deletion of the old employee photo after a successful update.

        Args:
            request: The HTTP request containing the data for the update.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: A Response object containing the updated employee data.
        """
        instance = self.get_object()
        old_image = instance.photo.path if instance.photo else None

        logger.info("Updating Employee: %s", instance.id)  # Log the update action

        response = super().update(request, *args, **kwargs)

        # Delete old image after successful update
        if old_image and instance.photo.path != old_image:
            try:
                os.remove(old_image)
                logger.info("Deleted old image for Employee: %s", instance.id)  # Log successful deletion
            except OSError as e:
                logger.error("Error deleting old image for Employee %s: %s", instance.id, e)

        return response

    def perform_create(self, serializer):
        """
        Create a new Employee instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Created Employee: %s", serializer.data)

    def perform_update(self, serializer):
        """
        Update an existing Employee instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Updated Employee: %s", serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete an Employee instance.

        Args:
            request (HttpRequest): The incoming HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response to the delete request.
        """
        response = super().destroy(request, *args, **kwargs)
        logger.info("Deleted Employee with ID: %s", kwargs['pk'])
        return response

class SupplierViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing Suppliers.

    Provides `create`, `retrieve`, `update`, and `destroy` actions for the Supplier model.
    """
    
    queryset = Supplier.objects.all().order_by('id')
    serializer_class = SupplierSerializer

    def perform_create(self, serializer):
        """
        Create a new Supplier instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Created Supplier: %s", serializer.data)

    def perform_update(self, serializer):
        """
        Update an existing Supplier instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Updated Supplier: %s", serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a Supplier instance.

        Args:
            request: The HTTP request containing the delete request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response to the delete request.
        """
        response = super().destroy(request, *args, **kwargs)
        logger.info("Deleted Supplier with ID: %s", kwargs['pk'])
        return response


class LocationViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing Locations.

    Provides `create`, `retrieve`, `update`, and `destroy` actions for the Location model.
    """

    queryset = Location.objects.all().order_by('id')
    serializer_class = LocationSerializer

    def perform_create(self, serializer):
        """
        Create a new Location instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Created Location: %s", serializer.data)

    def perform_update(self, serializer):
        """
        Update an existing Location instance.

        Args:
            serializer: The serializer instance containing validated data.
        """
        serializer.save()
        logger.info("Updated Location: %s", serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a Location instance.

        Args:
            request: The HTTP request containing the delete request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response to the delete request.
        """
        response = super().destroy(request, *args, **kwargs)
        logger.info("Deleted Location with ID: %s", kwargs['pk'])
        return response
class ReportGenerationView(APIView):
    """
    A view to generate reports in various formats (CSV, PDF, Excel) based on
    the asset data stored in the system. It allows filtering of records dynamically
    using custom query parameters and provides reports in the requested format.
    
    The view supports filtering by human-readable names for foreign key fields
    (like `major_category`, `department`) instead of using their numeric IDs.
    """

    permission_classes = [IsGetOnly]

    def get(self, request) -> Response:
        """
        Handles the GET request to generate a report based on asset data.
        This includes applying dynamic filters based on the query parameters and
        generating the report in the requested format.

        Query Parameters:
            - report_format (str): The format of the report (pdf, csv, xlsx). Default is pdf.
            - model (str): The name of the model for which to generate the report.
            - fields (str): A comma-separated list of fields to include in the report.
            - Any other filtering parameters (e.g., major_category="Furniture").

        Args:
            request (Request): The HTTP request containing query parameters.

        Returns:
            Response: A response containing the generated report in the requested format
            or an error message if the request parameters are invalid or no data is found.
        """
        # Extract query params
        report_format: str = request.query_params.get('report_format', 'pdf').lower()
        model_name: Optional[str] = request.query_params.get('model_name', 'Asset')
        fields: List[str] = request.query_params.get('fields', '').split(',')

        if fields == ['']:  # If fields are an empty string
            fields = None  # Use None to indicate that all fields should be included

        # Check if model name is provided
        if not model_name:
            logger.error("Model name is required.")
            return Response(
                {'detail': 'Model name is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Retrieve the model dynamically from the 'assets' app
            model = apps.get_model('assets', model_name)
        except LookupError:
            logger.error(f'Model "{model_name}" not found.')
            return Response(
                {'detail': f'Model "{model_name}" not found.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the initial queryset of the model
        queryset = model.objects.all()

        # Apply dynamic filtering using the custom filter backend
        filter_backend = DynamicFilter()
        queryset = filter_backend.filter_queryset(request, queryset, self)

        # If data is found, generate the report
        if queryset.exists():
            # Serialize the filtered queryset data
            serializer = AssetSerializer(queryset, many=True, fields=fields)
            data = serializer.data

            # Handle report format: CSV, PDF, or XLSX (Excel)
            if report_format == 'csv':
                report_response = generate_csv(data, fields)
                logger.info("Generated CSV report for model: %s", model_name)
            elif report_format == 'pdf':
                report_response = generate_pdf(data, user=request.user, fields=fields, filtered_queryset=queryset)
                logger.info("Generated PDF report for model: %s", model_name)
            elif report_format == 'xlsx':
                report_response = generate_excel(data, fields)
                logger.info("Generated XLSX report for model: %s", model_name)
            else:
                logger.error("Unsupported report format requested: %s", report_format)
                return Response(
                    {'detail': 'Unsupported format.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Return the generated report
            return report_response
        else:
            logger.warning("No data available for the report for model: %s", model_name)
            # Return 404 if no data is found
            return Response(
                {'detail': 'No data available for the report.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
class ImportAssetsView(APIView):
    """
    A view for importing assets from an Excel file.
    This view handles the uploading of an Excel file containing asset data,
    validates the data, creates new assets or updates existing ones, and
    returns a conflict log for any issues encountered during the import.
    """

    def post(self, request) -> Response:
        """
        Handles POST requests to import asset data from an uploaded Excel file.
        The uploaded file must contain asset information with specific columns.

        Args:
            request (Request): The HTTP request containing the uploaded file.

        Returns:
            Response: A response containing a conflict log of any issues encountered
            during the import process or an error message if no file is provided.
        """
        file = request.FILES.get('file')
        if file:
            file_path = f'/tmp/{file.name}'  # Temporary path for uploaded file
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # Read the Excel file
            try:
                df = pd.read_excel(file_path)
                logger.info("Excel file '%s' uploaded and read successfully.", file.name)
            except Exception as e:
                logger.error("Error reading Excel file '%s': %s", file.name, str(e))
                return Response({'error': 'Failed to read the Excel file.'}, status=status.HTTP_400_BAD_REQUEST)

            # Convert date_placed_in_service to datetime format
            if 'date_placed_in_service' in df.columns:
                df['date_placed_in_service'] = pd.to_datetime(df['date_placed_in_service'], errors='coerce').dt.date
            if 'date_of_purchase' in df.columns:
                df['date_of_purchase'] = pd.to_datetime(df['date_of_purchase'], errors='coerce').dt.date


            conflict_log: List[Dict[str, Any]] = []
            for index, row in df.iterrows():
                asset_data = row.to_dict()
                asset_code = asset_data.get('asset_code')

                if not asset_code or asset_code == 'DEFAULT':
                    # Creating a new asset
                    serializer = AssetSerializer(data=asset_data, context={'request': request})  # Pass context here
                else:
                    # Updating an existing asset
                    try:
                        existing_asset = Asset.objects.get(asset_code=asset_code)
                        # Update the barcode only if it differs
                        if 'barcode' in asset_data and asset_data['barcode'] != existing_asset.barcode:
                            existing_asset.barcode = asset_data['barcode']
                        serializer = AssetSerializer(existing_asset, data=asset_data, partial=True, context={'request': request})  # Pass context here
                    except Asset.DoesNotExist:
                        conflict_log.append({
                            'row': index + 1,
                            'errors': f"Asset with asset_code '{asset_code}' not found."
                        })
                        logger.warning("Asset with asset_code '%s' not found on row %d.", asset_code, index + 1)
                        continue

                if serializer.is_valid():
                    serializer.save(created_by=request.user)  # Ensure that created_by is handled correctly
                    logger.info("Asset with asset_code '%s' imported successfully.", asset_code)
                else:
                    conflict_log.append({
                        'row': index + 1,
                        'errors': serializer.errors
                    })
                    logger.error("Validation errors for asset on row %d: %s", index + 1, serializer.errors)

            return Response({'conflicts': conflict_log}, status=status.HTTP_200_OK)

        logger.error("No file provided in the request.")
        return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

class AssetSummaryView(APIView):
    """
    A view that provides a summary of assets, including overall statistics
    and detailed breakdowns by department, supplier, location, and categories.
    """
    permission_classes = [IsGetOnly]

    def get(self, request, *args, **kwargs) -> Response:
        """
        Handle GET requests to return an asset summary.

        Retrieves overall asset statistics, including total assets, purchase price,
        net book value (NBV), and accumulated depreciation. Additionally, it 
        summarizes assets based on various fields such as department, supplier, 
        location, major category, and minor category.

        Args:
            request (HttpRequest): The incoming HTTP GET request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A Response object containing the summarized asset data.
        """
        cache_key = 'asset_summary_cache'  # Define your cache key
        response_data = cache.get(cache_key)

        if response_data is None:  # Check if cache is empty
            logger.info("Cache miss for key '%s', generating asset summary.", cache_key)

            # Overall summary
            active_assets = Asset.objects.filter(is_disposed=False)  # Filter for active assets
            total_assets = active_assets.count()
            total_purchase_price = active_assets.aggregate(total_purchase_price=Sum('purchase_price'))['total_purchase_price'] or 0
            total_nbv = active_assets.aggregate(total_nbv=Sum('net_book_value'))['total_nbv'] or 0
            total_accumulated_depreciation = total_purchase_price - total_nbv

            overall_summary = {
                'total_assets': total_assets,
                'total_purchase_price': total_purchase_price,
                'total_nbv': total_nbv,
                'total_accumulated_depreciation': total_accumulated_depreciation,
                'total_employees': Employee.objects.count(),
                'total_major_categories': MajorCategory.objects.count(),
                'total_minor_categories': MinorCategory.objects.count(),
                'total_locations': Location.objects.count(),
                'total_departments': Department.objects.count(),
                'total_suppliers': Supplier.objects.count(),
            }

            # Summarize assets by category
            def summarize_by_queryset(queryset, name_field: str) -> List[Dict[str, Any]]:
                """
                Summarize assets based on a given queryset and name field.

                Args:
                    queryset (QuerySet): A Django QuerySet of the model instances.
                    name_field (str): The field name to filter the assets.

                Returns:
                    List[Dict[str, Any]]: A list of dictionaries with asset summaries.
                """
                summaries = []
                for instance in queryset:
                    # Assuming instance is the department, supplier, etc.
                    assets = Asset.objects.filter(**{name_field: instance, 'is_disposed': False})   # Adjust as needed
                    total_assets = assets.count()
                    total_purchase_price = assets.aggregate(Sum('purchase_price'))['purchase_price__sum'] or 0
                    total_nbv = assets.aggregate(Sum('net_book_value'))['net_book_value__sum'] or 0
                    total_accumulated_depreciation = total_purchase_price - total_nbv
                    
                    # Use the appropriate field for the string representation
                    if name_field == 'department':
                        instance_name = instance.name  # Adjust this based on your actual field names
                    elif name_field == 'supplier':
                        instance_name = instance.name
                    elif name_field == 'location':
                        instance_name = instance.name
                    elif name_field == 'major_category':
                        instance_name = instance.name
                    elif name_field == 'minor_category':
                        instance_name = instance.name
                    else:
                        instance_name = str(instance)

                    # Create a dictionary for the summary
                    summary_item = {
                        'label': f"{name_field.replace('_', ' ').title()}: {instance_name}",
                        'total_assets': total_assets,
                        'total_purchase_price': total_purchase_price,
                        'total_nbv': total_nbv,
                        'total_accumulated_depreciation': total_accumulated_depreciation,
                    }
                    
                    summaries.append(summary_item)
                return summaries

            # Generate summaries
            department_summaries = summarize_by_queryset(Department.objects.all(), 'department')
            supplier_summaries = summarize_by_queryset(Supplier.objects.all(), 'supplier')
            location_summaries = summarize_by_queryset(Location.objects.all(), 'location')
            major_category_summaries = summarize_by_queryset(MajorCategory.objects.all(), 'major_category')
            minor_category_summaries = summarize_by_queryset(MinorCategory.objects.all(), 'minor_category')

            # Prepare the response data
            response_data = {
                'overall_summary': overall_summary,
                'departments_summary': department_summaries,
                'suppliers_summary': supplier_summaries,
                'locations_summary': location_summaries,
                'major_categories_summary': major_category_summaries,
                'minor_categories_summary': minor_category_summaries,
            }

            # Cache the response data
            cache.set(cache_key, response_data, timeout=60 * 15)  # Cache for 15 minutes
            logger.info("Asset summary generated and cached for key '%s'.", cache_key)
        else:
            logger.info("Cache hit for key '%s', returning cached asset summary.", cache_key)

        return Response(response_data, status=status.HTTP_200_OK)


class RecentActivityView(APIView):
    """
    A view that provides recent activity of the authenticated user, such as recently viewed assets.
    
    This view retrieves the recent activities from the user's cookies and returns the details
    of recently viewed assets. If the user is not authenticated, an appropriate error message 
    is returned.
    """
    permission_classes = [IsGetOnly]

    def get(self, request) -> Response:
        """
        Handle GET requests to return recent user activity.

        This method retrieves recent user activities, such as recently viewed assets,
        from cookies and returns them. If the user is not authenticated, an error
        message is returned.

        Args:
            request (HttpRequest): The incoming HTTP GET request.

        Returns:
            Response: A Response object containing recent activity data or an error message.
        """
        if request.user.is_authenticated:
            logger.info(f"User '{request.user.username}' is authenticated. Retrieving recent activities.")
            # Get recent activities from cookies
            recent_activities = request.COOKIES.get('recent_activity', '').split('|')

            recent_assets_ids = []

            for activity in recent_activities:
                if activity.startswith('asset:'):
                    # Extract asset ID
                    asset_id = activity.split(':')[1]
                    recent_assets_ids.append(int(asset_id))
                    logger.debug(f"Found asset ID: {asset_id}")

            response_data = {
                'recent_assets': [],
            }

            # Fetch assets if there are valid IDs
            if recent_assets_ids:
                assets = Asset.objects.filter(id__in=recent_assets_ids)
                assets_dict = {asset.id: asset for asset in assets}
                sorted_assets = [assets_dict[asset_id] for asset_id in recent_assets_ids if asset_id in assets_dict]

                serializer = AssetSerializer(sorted_assets, many=True)
                response_data['recent_assets'] = serializer.data
                logger.info(f"Retrieved {len(response_data['recent_assets'])} recent assets.")

            if not response_data['recent_assets']:
                logger.warning("No recent activity found.")
                return Response({'message': 'No recent activity found.'}, status=status.HTTP_200_OK)

            return Response(response_data, status=status.HTTP_200_OK)

        logger.error("User not authenticated. Access denied.")
        return Response({'error': 'User not authenticated'}, status=status.HTTP_403_FORBIDDEN)


class DisposedAssetViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing disposed assets.

    This viewset handles CRUD operations for assets that have been marked as disposed.
    Disposed assets are cached for performance optimization.
    """
    serializer_class = DisposedAssetSerializer  # Update to use the new serializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self) -> QuerySet:
        """
        Override get_queryset to cache disposed assets.

        Returns:
            QuerySet: The queryset of disposed assets.
        """
        cache_key = 'disposed_assets'
        cached_queryset = cache.get(cache_key)

        if cached_queryset:
            logger.info("Using cached queryset for disposed assets.")
            return cached_queryset
        
        queryset = Asset.objects.filter(is_disposed=True).order_by('id')
        cache.set(cache_key, queryset, 60 * 15)  # Cache for 15 minutes
        logger.info("Fetched disposed assets from the database and cached the queryset.")
        return queryset

    def list(self, request, *args, **kwargs) -> Response:
        """
        Override the list method to use cached queryset.

        Returns a paginated response of disposed assets using a cached queryset.

        Args:
            request (HttpRequest): The incoming HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A paginated response of serialized disposed assets.
        """
        queryset = self.get_queryset()  # Use cached queryset
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.info("Returning paginated response of disposed assets.")
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        logger.info("Returning response of all disposed assets.")
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs) -> Response:
        """
        Override partial_update to handle asset disposal and undisposal.

        This method updates the asset's disposal status. If the asset is being disposed,
        it captures the disposal time and user. If it is being undisposed, it clears 
        the disposal time and captures who undisposed the asset.

        Args:
            request (HttpRequest): The incoming HTTP request containing the update data.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A success message indicating the asset update.
        """
        asset = self.get_object()
        serializer = self.get_serializer(asset, data=request.data, partial=True)  # Use the new serializer

        # Validate and update the asset
        if serializer.is_valid(raise_exception=True):
            updated_asset = serializer.save()
            logger.info(f"Asset {updated_asset.asset_code} updated successfully.")
        
        # Invalidate the cache after disposal or undisposal
        cache.delete('disposed_assets')
        logger.info("Cache for disposed assets invalidated after update.")

        return Response({"message": "Asset updated successfully."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs) -> Response:
        """
        Override destroy to clear cache when an asset is deleted.

        Args:
            request (HttpRequest): The incoming HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response from the super method.
        """
        response = super().destroy(request, *args, **kwargs)

        # Invalidate the cache for disposed assets after deletion
        cache.delete('disposed_assets')
        logger.info("Cache for disposed assets invalidated after deletion.")
        
        return response
