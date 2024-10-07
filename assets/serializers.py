from rest_framework import serializers
from .models import Asset, MajorCategory, MinorCategory, Department, Employee, Supplier, Location
from django.core.exceptions import ValidationError
import imghdr
from typing import IO, Optional
import decimal
import logging
from io import IOBase
from django.utils import timezone
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
import requests
import traceback
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

def validate_image_format(image: IOBase) -> None:
    """Validates the format of an image file.

    This function checks if the given image file is in one of the allowed formats:
    PNG, JPEG, or JPG. If the image format is not valid, a ValidationError is raised.

    Args:
        image (IOBase): The image file to validate.

    Raises:
        ValidationError: If the image format is not one of the allowed formats (PNG, JPEG, JPG).

    Examples:
        >>> with open('test_image.png', 'rb') as img_file:
        ...     validate_image_format(img_file)

    Logging:
        Logs an info message indicating the format validation process.
    """
    valid_formats = ['jpeg', 'png', 'jpg']
    file_format = imghdr.what(image)

    logger.info(f"Validating image format: {file_format}")

    if file_format not in valid_formats:
        logger.error(f"Invalid image format: {file_format}. Allowed formats are: {valid_formats}")
        raise ValidationError(f"Invalid image format: {file_format}. Only PNG, JPEG, and JPG are allowed.")

def validate_image_size(image: IOBase) -> None:
    """Validates the size of an image file.

    This function checks if the given image file size exceeds the specified limit
    (2MB). If the image file size exceeds this limit, a ValidationError is raised.

    Args:
        image (IOBase): The image file to validate.

    Raises:
        ValidationError: If the image file size exceeds the specified limit (2MB).

    Examples:
        >>> with open('test_image.jpg', 'rb') as img_file:
        ...     validate_image_size(img_file)

    Logging:
        Logs an info message indicating the size validation process.
    """
    limit_mb = 2  # 2MB limit
    image.seek(0, 2)  # Seek to the end of the file to get the size
    file_size = image.tell()

    logger.info(f"Validating image size: {file_size / (1024 * 1024):.2f} MB")

    if file_size > limit_mb * 1024 * 1024:
        logger.error(f"Image size exceeds {limit_mb} MB. Current size: {file_size / (1024 * 1024):.2f} MB")
        raise ValidationError(f"Image size should not exceed {limit_mb} MB.")
class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for the Department model.

    This serializer converts Department model instances to JSON and vice versa.
    It includes a string representation of the department for better readability.

    Attributes:
        department (str): A string representation of the department.

    Meta:
        model: The Department model.
        fields: All fields from the Department model.

    Logging:
        Logs the creation and update processes of Department instances.
    """
    department: serializers.StringRelatedField = serializers.StringRelatedField()

    class Meta:
        model = Department
        fields = '__all__'

    def create(self, validated_data):
        """Create a new Department instance.

        Args:
            validated_data (dict): Validated data for creating a new Department.

        Returns:
            Department: The newly created Department instance.

        Logging:
            Logs the creation of a new Department instance.
        """
        department_instance = Department.objects.create(**validated_data)
        logger.info(f"Created Department: {department_instance.name}")
        return department_instance

    def update(self, instance, validated_data):
        """Update an existing Department instance.

        Args:
            instance (Department): The existing Department instance to update.
            validated_data (dict): Validated data for updating the Department.

        Returns:
            Department: The updated Department instance.

        Logging:
            Logs the update of an existing Department instance.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"Updated Department: {instance.name}")
        return instance

class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Employee model.

    This serializer converts Employee model instances to JSON and vice versa.
    It includes department-related data and handles validation for photo uploads.

    Attributes:
        department (SlugRelatedField): Field representing the department by its name.

    Meta:
        model: The Employee model.
        fields: All fields from the Employee model.

    Methods:
        validate_photo(value): Validates the format and size of the uploaded photo.

    Logging:
        Logs the creation and update of Employee instances.
    """
    department: serializers.SlugRelatedField = serializers.SlugRelatedField(
        queryset=Department.objects.all(),
        slug_field='name'  # Refer to Department by its name
    )

    class Meta:
        model = Employee
        fields = '__all__'

    def validate_photo(self, value: serializers.ImageField) -> serializers.ImageField:
        """
        Validates the format and size of the uploaded photo.

        Args:
            value (serializers.ImageField): The uploaded image file.

        Returns:
            serializers.ImageField: The validated image file.

        Raises:
            ValidationError: If the image format is not supported or if the file exceeds the size limit.

        Logging:
            Logs validation attempts for photo uploads, including success or failure.
        """
        try:
            validate_image_format(value.file)
            validate_image_size(value.file)
            logger.info(f"Photo validation passed for file: {value.name}")
        except ValidationError as e:
            logger.error(f"Photo validation failed for file: {value.name}. Reason: {str(e)}")
            raise e
        return value
    
    def validate(self, attrs):
        """Validate employee's age at hiring."""
        date_of_birth = attrs.get('date_of_birth')
        date_hired = attrs.get('date_hired')

        if date_of_birth and date_hired:
            # Calculate the difference in years
            age = relativedelta(date_hired, date_of_birth)

            # If age is less than 18 years, raise a validation error
            if age.years < 18:
                raise serializers.ValidationError("Employee must be at least 18 years old at the time of hiring.")
            
            # If the employee is exactly 18 years old, check the month and day
            if age.years == 18:
                if date_hired < date_of_birth + relativedelta(years=18):
                    raise serializers.ValidationError("Employee must be at least 18 years old at the time of hiring.")

        return attrs

    def create(self, validated_data):
        """Create a new Employee instance.

        Args:
            validated_data (dict): Validated data for creating a new Employee.

        Returns:
            Employee: The newly created Employee instance.

        Logging:
            Logs the creation of a new Employee instance with department and name details.
        """
        employee_instance = Employee.objects.create(**validated_data)
        logger.info(f"Created Employee: {employee_instance.first_name} in Department: {employee_instance.department.name}")
        return employee_instance

    def update(self, instance, validated_data):
        """Update an existing Employee instance.

        Args:
            instance (Employee): The existing Employee instance to update.
            validated_data (dict): Validated data for updating the Employee.

        Returns:
            Employee: The updated Employee instance.

        Logging:
            Logs the update of an Employee instance, including their name and department.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"Updated Employee: {instance.first_name} in Department: {instance.department.name}")
        return instance

class SupplierSerializer(serializers.ModelSerializer):
    """
    Serializer for the Supplier model.

    This serializer converts Supplier model instances to JSON and vice versa.
    It handles validation and data transformation for supplier-related data.

    Meta:
        model: The Supplier model.
        fields: All fields from the Supplier model.

    Logging:
        Logs the creation and update of Supplier instances.
    """

    class Meta:
        model = Supplier
        fields = '__all__'

    def create(self, validated_data):
        """Create a new Supplier instance.

        Args:
            validated_data (dict): Validated data for creating a new Supplier.

        Returns:
            Supplier: The newly created Supplier instance.

        Logging:
            Logs the creation of a Supplier instance, including its name.
        """
        supplier_instance = Supplier.objects.create(**validated_data)
        logger.info(f"Created Supplier: {supplier_instance.name}")
        return supplier_instance

    def update(self, instance, validated_data):
        """Update an existing Supplier instance.

        Args:
            instance (Supplier): The existing Supplier instance to update.
            validated_data (dict): Validated data for updating the Supplier.

        Returns:
            Supplier: The updated Supplier instance.

        Logging:
            Logs the update of a Supplier instance, including its name.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"Updated Supplier: {instance.name}")
        return instance


class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Location model.

    Fields:
        - name: The name of the location.
        - longitude: The longitude of the location (optional).
        - latitude: The latitude of the location (optional).
        - use_current_location: Boolean to indicate if current location should be used.

    Methods:
        validate(attrs): Validates data and retrieves coordinates.
        get_current_location(): Retrieves current location coordinates.
        geocode_location(name): Geocodes the provided name to get longitude and latitude.
        create(validated_data): Creates a new Location instance.
        update(instance, validated_data): Updates an existing Location instance.
    """

    name: str
    longitude: Optional[float]
    latitude: Optional[float]
    use_current_location: bool

    class Meta:
        model = Location
        fields = ['name', 'longitude', 'latitude', 'use_current_location']
        read_only_fields = ['longitude', 'latitude']

    def validate(self, attrs):
        """Validate the data and get coordinates based on the use_current_location flag.

        Args:
            attrs (dict): The data passed to the serializer.

        Returns:
            dict: The validated data, potentially including longitude and latitude.
        """
        # Initialize longitude and latitude to 0.0
        longitude = 0.0
        latitude = 0.0

        if attrs.get('use_current_location'):
            # Attempt to get the current location coordinates
            longitude, latitude = self.get_current_location()

        else:
            # Attempt to geocode the provided name
            try:
                longitude, latitude = self.geocode_location(attrs['name'])
            except GeocoderUnavailable:
                logger.error("Geocoding service is currently unavailable.")
                longitude, latitude = 0.0, 0.0
            except GeocoderTimedOut:
                logger.error("Geocoding service timed out.")
                longitude, latitude = 0.0, 0.0
            except Exception as e:
                logger.error(f"Geocoding failed for '{attrs['name']}': {e}")
                longitude, latitude = 0.0, 0.0

        # Set the longitude and latitude in the validated data
        attrs['longitude'] = longitude
        attrs['latitude'] = latitude

        return attrs

    def get_current_location(self):
        """Retrieve the current location coordinates.

        Returns:
            tuple: A tuple containing longitude and latitude.
        """
        try:
            # Using a public IP geolocation service to get the current coordinates
            response = requests.get("http://ip-api.com/json/")
            data = response.json()
            if response.status_code == 200 and data.get('status') == 'success':
                longitude = data['lon']
                latitude = data['lat']
                logger.info(f"Retrieved current location: ({longitude}, {latitude})")
                return longitude, latitude
            else:
                logger.warning("Could not retrieve current location using IP geolocation.")
        except requests.RequestException as e:
            logger.error(f"Error retrieving current location: {e}")

        return 0.0, 0.0  # Default to 0.0 if the location cannot be retrieved

    def geocode_location(self, name):
        """Geocode the provided name to get its longitude and latitude.

        Args:
            name (str): The name to geocode.

        Returns:
            tuple: A tuple containing longitude and latitude.

        Raises:
            serializers.ValidationError: If the name cannot be geocoded.
        """
        geolocator = Nominatim(user_agent="asset_tracker")
        location = geolocator.geocode(name)

        if location:
            logger.info(f"Geocoded '{name}' to coordinates: ({location.longitude}, {location.latitude})")
            return location.longitude, location.latitude
        else:
            logger.error(f"Geocoding failed for '{name}': Location not found.")
            return 0.0, 0.0  # Default to 0.0 if the location is not found

    def create(self, validated_data):
        """Create a new Location instance.

        Args:
            validated_data (dict): Validated data for creating a new Location.

        Returns:
            Location: The newly created Location instance.
        """
        location_instance = Location.objects.create(**validated_data)
        logger.info(f"Created Location: {location_instance.name}, Coordinates: "
                    f"({location_instance.longitude}, {location_instance.latitude})")
        return location_instance

    def update(self, instance, validated_data):
        """Update an existing Location instance.

        Args:
            instance (Location): The existing Location instance to update.
            validated_data (dict): Validated data for updating the Location.

        Returns:
            Location: The updated Location instance.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"Updated Location: {instance.name}, Coordinates: "
                    f"({instance.longitude}, {instance.latitude})")
        return instance

class MajorCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the MajorCategory model.

    Fields:
        - name: The name of the major category.

    Methods:
        create(validated_data): Creates a new MajorCategory instance.
        update(instance, validated_data): Updates an existing MajorCategory instance.
    """

    name: str

    class Meta:
        model = MajorCategory
        fields = '__all__'

    def create(self, validated_data):
        """Create a new MajorCategory instance.

        Args:
            validated_data (dict): Validated data for creating a new MajorCategory.

        Returns:
            MajorCategory: The newly created MajorCategory instance.

        Logging:
            Logs the creation of a MajorCategory instance, including its name.
        """
        category_instance = MajorCategory.objects.create(**validated_data)
        logger.info(f"Created MajorCategory: {category_instance.name}")
        return category_instance

    def update(self, instance, validated_data):
        """Update an existing MajorCategory instance.

        Args:
            instance (MajorCategory): The existing MajorCategory instance to update.
            validated_data (dict): Validated data for updating the MajorCategory.

        Returns:
            MajorCategory: The updated MajorCategory instance.

        Logging:
            Logs the update of a MajorCategory instance, including its name.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"Updated MajorCategory: {instance.name}")
        return instance

class MinorCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the MinorCategory model.

    This serializer converts MinorCategory model instances to JSON and vice versa.
    It handles validation and data transformation for minor category-related data.

    Fields:
        - name (str): The name of the minor category.
        - major_category (SlugRelatedField): The related MajorCategory, referenced by its name.

    Meta:
        model: The MinorCategory model.
        fields: All fields from the MinorCategory model.

    Methods:
        create(validated_data): Creates a new MinorCategory instance.
        update(instance, validated_data): Updates an existing MinorCategory instance.
    """

    name: str
    major_category: serializers.SlugRelatedField = serializers.SlugRelatedField(
        queryset=MajorCategory.objects.all(),
        slug_field='name'  # Refer to the MajorCategory by its name
    )

    class Meta:
        model = MinorCategory
        fields = '__all__'

    def create(self, validated_data):
        """Create a new MinorCategory instance.

        Args:
            validated_data (dict): Validated data for creating a new MinorCategory.

        Returns:
            MinorCategory: The newly created MinorCategory instance.

        Logging:
            Logs the creation of a MinorCategory instance, including its name and the related MajorCategory.
        """
        minor_category_instance = MinorCategory.objects.create(**validated_data)
        logger.info(f"Created MinorCategory: {minor_category_instance.name}, "
                    f"Related MajorCategory: {minor_category_instance.major_category.name}")
        return minor_category_instance

    def update(self, instance, validated_data):
        """Update an existing MinorCategory instance.

        Args:
            instance (MinorCategory): The existing MinorCategory instance to update.
            validated_data (dict): Validated data for updating the MinorCategory.

        Returns:
            MinorCategory: The updated MinorCategory instance.

        Logging:
            Logs the update of a MinorCategory instance, including its name and the related MajorCategory.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"Updated MinorCategory: {instance.name}, "
                    f"Related MajorCategory: {instance.major_category.name}")
        return instance

class AssetSerializer(serializers.ModelSerializer):
    """
    Serializer for the Asset model.

    This serializer handles the validation, transformation, and serialization of asset-related data.
    It tracks the user performing create and update operations.

    Fields:
        - major_category (SlugRelatedField): Major category of the asset, referenced by its name.
        - minor_category (SlugRelatedField): Minor category of the asset, referenced by its name.
        - department (SlugRelatedField): Department to which the asset belongs, referenced by its name.
        - location (SlugRelatedField): Location of the asset, referenced by its name.
        - employee (SlugRelatedField): Employee responsible for the asset, referenced by their first name.
        - supplier (SlugRelatedField): Supplier of the asset, referenced by its name.
        - created_by_name (CharField): Username of the user who created the asset.
        - updated_by_name (CharField): Username of the user who last updated the asset.
    """

    major_category = serializers.SlugRelatedField(
        slug_field='name',
        queryset=MajorCategory.objects.all(),
        error_messages={
            'does_not_exist': "Major category '{value}' does not exist.",
            'invalid': "Invalid major category."
        }
    )
    minor_category = serializers.SlugRelatedField(
        slug_field='name',
        queryset=MinorCategory.objects.all(),
        error_messages={
            'does_not_exist': "Minor category '{value}' does not exist.",
            'invalid': "Invalid minor category."
        }
    )
    department = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Department.objects.all(),
        error_messages={
            'does_not_exist': "Department '{value}' does not exist.",
            'invalid': "Invalid department."
        }
    )
    location = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Location.objects.all(),
        error_messages={
            'does_not_exist': "Location '{value}' does not exist.",
            'invalid': "Invalid location."
        }
    )
    employee = serializers.SlugRelatedField(
        slug_field='first_name',
        queryset=Employee.objects.all(),
        allow_null=True,
        error_messages={
            'does_not_exist': "Employee '{value}' does not exist.",
            'invalid': "Invalid employee name."
        }
    )
    supplier = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Supplier.objects.all(),
        error_messages={
            'does_not_exist': "Supplier '{value}' does not exist.",
            'invalid': "Invalid supplier."
        }
    )
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = Asset
        fields = '__all__'
        read_only_fields = ('created_by', 'updated_by', 'asset_code', 'net_book_value')

    def __init__(self, *args, **kwargs):
        """Initialize the serializer with optional dynamic field selection.

        If `fields` is passed in kwargs, only the specified fields will be included.

        Logging:
            Logs the fields that are dynamically selected if `fields` is provided.
        """
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)

        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)
            logger.debug(f"AssetSerializer initialized with dynamic fields: {allowed}")
        else:
            logger.debug("AssetSerializer initialized with all fields.")

    def validate_purchase_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Purchase price cannot be negative.")
        return value
    
    def validate_date_of_purchase(self, value):
        """Validate that the date of purchase is not in the future."""
        if value > timezone.now().date():
            raise serializers.ValidationError("Date of purchase cannot be in the future.")
        return value

    def validate_date_placed_in_service(self, value):
        """Validate that the date placed in service is not later than the current date."""
        
        # Check if the date placed in service is in the future
        if value > timezone.now().date():
            raise ValidationError("Date placed in service cannot be in the future.")
        
        # Get the purchase date from input data
        date_of_purchase = self.initial_data.get('date_of_purchase')
        
        if date_of_purchase:
            date_of_purchase = serializers.DateField().to_internal_value(date_of_purchase)  # Convert to date type
            
            # The date placed in service can be after the date of purchase
            # No need to raise an error if value > date_of_purchase

        if not value:
            raise ValidationError("The date placed in service is required.")

        return value

    def validate_units(self, value):
        if value <= 0:  # This will reject zero and negative values
            raise serializers.ValidationError("Units must be a positive integer greater than 0.")
        return value

    def validate_asset_image(self, value: serializers.ImageField) -> serializers.ImageField:
        """Validate the asset image for format and size.

        Args:
            value (serializers.ImageField): The uploaded image file.

        Returns:
            serializers.ImageField: The validated image file.

        Raises:
            ValidationError: If the image format or size is invalid.

        Logging:
            Logs the validation success or failure of the asset image.
        """
        try:
            validate_image_format(value.file)
            validate_image_size(value.file)
            logger.info("Asset image validated successfully.")
        except Exception as e:
            logger.error(f"Asset image validation failed: {e}")
            raise serializers.ValidationError("Invalid image format or size.")
        return value

    def create(self, validated_data: dict) -> Asset:
        """Create a new asset instance with custom save logic and user tracking."""
        user = self.context['request'].user  # Capture the user making the request
        asset = Asset(**validated_data)
        asset.created_by = user  # Assign the user to the created_by field

        try:
            asset.save()  # Save without the user parameter
            logger.info(f"Created new asset with asset code: {asset.asset_code} by user: {user.username}")
        except Exception as e:
            print(f"Error creating asset: {e}")
            print(traceback.format_exc())  # Print full traceback for detailed debugging
            logger.error(f"Error creating asset: {e}")
            raise serializers.ValidationError("Error saving the asset.")

        return asset

    def update(self, instance: Asset, validated_data: dict) -> Asset:
        """Update an existing asset instance with custom save logic and user tracking."""
        user = self.context['request'].user  # Capture the user making the request

        if 'is_disposed' in validated_data:
            is_disposed = validated_data.pop('is_disposed')

            if is_disposed:  # Asset is being disposed
                instance.is_disposed = True
                instance.disposed_at = timezone.now()
                instance.disposed_by = user
                instance.updated_by = user
                logger.info(f"Asset {instance.asset_code} disposed by {user.username}.")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.updated_by = user  # Assign the user to the updated_by field

        try:
            instance.save()  # Save without the user parameter
            logger.info(f"Updated asset with asset code: {instance.asset_code} by user: {user.username}")
        except Exception as e:
            logger.error(f"Error updating asset: {e}")
            raise serializers.ValidationError("Error updating the asset.")

        return instance

    def validate(self, attrs: dict) -> dict:
        """Custom validation method to ensure unique barcode handling.

        Args:
            attrs (dict): The input attributes to validate.

        Returns:
            dict: The validated attributes.

        Raises:
            ValidationError: If the barcode already exists for another asset.
        """
        barcode = attrs.get('barcode')
        asset_code = self.instance.asset_code if self.instance else attrs.get('asset_code')

        # If asset exists (for updates)
        if asset_code:
            try:
                existing_asset = Asset.objects.get(asset_code=asset_code)
                
                # Only check if the barcode has changed
                if barcode and existing_asset.barcode != barcode:
                    if Asset.objects.filter(barcode=barcode).exists():
                        logger.warning(f"Validation failed: Barcode '{barcode}' already exists for another asset.")
                        raise serializers.ValidationError({
                            'barcode': ['Asset with this barcode already exists.']
                        })
            except Asset.DoesNotExist:
                logger.debug(f"No existing asset found with code '{asset_code}' for barcode validation.")

        # If creating a new asset, ensure barcode uniqueness
        elif barcode and Asset.objects.filter(barcode=barcode).exists():
            logger.warning(f"Validation failed: Barcode '{barcode}' already exists.")
            raise serializers.ValidationError({
                'barcode': ['Asset with this barcode already exists.']
            })

        return attrs
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_by'] = instance.created_by.username if instance.created_by else None
        representation['updated_by'] = instance.updated_by.username if instance.updated_by else None
        representation['disposed_by'] = instance.disposed_by.username if instance.disposed_by else None
        representation['undisposed_by'] = instance.undisposed_by.username if instance.undisposed_by else None
        return representation
class ReportGenerationSerializer(serializers.Serializer):
    """
    Serializer for generating reports based on various criteria.

    Fields:
        report_type: The type of report to generate (e.g., assets, employees, track).
        fields: A list of specific fields to include in the report.
        start_date: The starting date for the report period.
        end_date: The ending date for the report period.
        search_text: A text to search within the report data.
        search_type: The type of search to perform (contains or does not contain).
        sort_by: The field to sort the report by.
        sort_order: The order to sort the report (ascending or descending).
        report_format: The format of the generated report (e.g., CSV, PDF, XLSX).
    """

    model_name: serializers.ChoiceField
    fields: serializers.ListField
    start_date: serializers.DateField
    end_date: serializers.DateField
    search_text: serializers.CharField
    search_type: serializers.ChoiceField
    sort_by: serializers.CharField
    sort_order: serializers.ChoiceField
    report_format: serializers.ChoiceField

    model_name = serializers.ChoiceField(choices=['Asset', 'Employee', 'Supplier', 'Location', 'Department',
                                                  'MajorCategory', 'MinorCategory'], required=True)
    fields = serializers.ListField(child=serializers.CharField(), required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    search_text = serializers.CharField(required=False, allow_blank=True)
    search_type = serializers.ChoiceField(choices=['contains', 'does_not_contain'], required=False)
    sort_by = serializers.CharField(required=False)
    sort_order = serializers.ChoiceField(choices=['asc', 'desc'], required=False, default='asc')
    report_format = serializers.ChoiceField(choices=['csv', 'pdf', 'xlsx'], required=False, default='csv')

# class DepartmentSummarySerializer(serializers.ModelSerializer):
#     """
#     Serializer for summarizing department information, including asset totals and financials.

#     Fields:
#         total_assets: Total number of assets within the department.
#         total_purchase_price: Total purchase price of all assets in the department.
#         total_nbv: Total net book value of all assets in the department.
#         total_accumulated_depreciation: Total accumulated depreciation of all assets in the department.
#     """

#     total_assets: int
#     total_purchase_price: decimal.Decimal
#     total_nbv: decimal.Decimal
#     total_accumulated_depreciation: decimal.Decimal

#     total_assets = serializers.IntegerField()
#     total_purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_nbv = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_accumulated_depreciation = serializers.DecimalField(max_digits=12, decimal_places=2)

#     class Meta:
#         model = Department
#         fields = ['name', 'total_assets', 'total_purchase_price', 'total_nbv', 'total_accumulated_depreciation']

# class SupplierSummarySerializer(serializers.ModelSerializer):
#     """
#     Serializer for summarizing supplier information, including asset totals and financials.

#     Fields:
#         total_assets: Total number of assets supplied by the supplier.
#         total_purchase_price: Total purchase price of all assets associated with the supplier.
#         total_nbv: Total net book value of all assets associated with the supplier.
#         total_accumulated_depreciation: Total accumulated depreciation of all assets associated with the supplier.
#     """

#     total_assets: int
#     total_purchase_price: decimal.Decimal
#     total_nbv: decimal.Decimal
#     total_accumulated_depreciation: decimal.Decimal

#     total_assets = serializers.IntegerField()
#     total_purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_nbv = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_accumulated_depreciation = serializers.DecimalField(max_digits=12, decimal_places=2)

#     class Meta:
#         model = Supplier
#         fields = ['name', 'total_assets', 'total_purchase_price', 'total_nbv', 'total_accumulated_depreciation']

# class LocationSummarySerializer(serializers.ModelSerializer):
#     """
#     Serializer for summarizing location information, including asset totals and financials.

#     Fields:
#         total_assets: Total number of assets located at the location.
#         total_purchase_price: Total purchase price of all assets associated with the location.
#         total_nbv: Total net book value of all assets associated with the location.
#         total_accumulated_depreciation: Total accumulated depreciation of all assets associated with the location.
#     """

#     total_assets: int
#     total_purchase_price: decimal.Decimal
#     total_nbv: decimal.Decimal
#     total_accumulated_depreciation: decimal.Decimal

#     total_assets = serializers.IntegerField()
#     total_purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_nbv = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_accumulated_depreciation = serializers.DecimalField(max_digits=12, decimal_places=2)

#     class Meta:
#         model = Location
#         fields = ['name', 'total_assets', 'total_purchase_price', 'total_nbv', 'total_accumulated_depreciation']

# class MajorCategorySummarySerializer(serializers.ModelSerializer):
#     """
#     Serializer for summarizing major category information, including asset totals and financials.

#     Fields:
#         total_assets: Total number of assets within the major category.
#         total_purchase_price: Total purchase price of all assets associated with the major category.
#         total_nbv: Total net book value of all assets associated with the major category.
#         total_accumulated_depreciation: Total accumulated depreciation of all assets associated with the major category.
#     """

#     total_assets: int
#     total_purchase_price: decimal.Decimal
#     total_nbv: decimal.Decimal
#     total_accumulated_depreciation: decimal.Decimal

#     total_assets = serializers.IntegerField()
#     total_purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_nbv = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_accumulated_depreciation = serializers.DecimalField(max_digits=12, decimal_places=2)

#     class Meta:
#         model = MajorCategory
#         fields = ['name', 'total_assets', 'total_purchase_price', 'total_nbv', 'total_accumulated_depreciation']


# class MinorCategorySummarySerializer(serializers.ModelSerializer):
#     """
#     Serializer for summarizing minor category information, including asset totals and financials.

#     Fields:
#         total_assets: Total number of assets within the minor category.
#         total_purchase_price: Total purchase price of all assets associated with the minor category.
#         total_nbv: Total net book value of all assets associated with the minor category.
#         total_accumulated_depreciation: Total accumulated depreciation of all assets associated with the minor category.
#     """

#     total_assets: int
#     total_purchase_price: decimal.Decimal
#     total_nbv: decimal.Decimal
#     total_accumulated_depreciation: decimal.Decimal

#     total_assets = serializers.IntegerField()
#     total_purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_nbv = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_accumulated_depreciation = serializers.DecimalField(max_digits=12, decimal_places=2)

#     class Meta:
#         model = MinorCategory
#         fields = ['name', 'total_assets', 'total_purchase_price', 'total_nbv', 'total_accumulated_depreciation']

class DisposedAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'id',
            'asset_code',
            'is_disposed',
            'disposed_at',
            'disposed_by',
            'undisposed_at',
            'undisposed_by'
        ]
        read_only_fields = [
            'disposed_at',
            'disposed_by',
            'undisposed_at',
            'undisposed_by'
        ]

    def validate_is_disposed(self, value):
        """Custom validation to ensure that disposal actions are logically sound."""
        if value is True:
            #Checking if the asset is already disposed
            if self.instance and self.instance.is_disposed:
                raise serializers.ValidationError("This asset is already disposed.")
            return value

        elif value is False:
            # Ensuring that if the asset is being undisposed, it was previously disposed
            if self.instance and not self.instance.is_disposed:
                raise serializers.ValidationError("This asset is not currently disposed.")
            return value

        raise serializers.ValidationError("Invalid value for disposal status.")

    def update(self, instance, validated_data):
        """Update the asset instance with validated data.

        This method handles the disposal or undisposal logic based on the input data.

        Args:
            instance (Asset): The asset instance to update.
            validated_data (dict): The validated data from the request.

        Returns:
            Asset: The updated asset instance.
        """
        # Check if disposal status is in the validated data
        if 'is_disposed' in validated_data:
            instance.is_disposed = validated_data['is_disposed']

            if instance.is_disposed:
                logger.info(f"Disposal was successful")
            else:
                instance.disposed_at = None
                instance.disposed_by = None
                instance.updated_by = self.context['request'].user
                instance.undisposed_at = timezone.now()  # Capture the time when it was undisposed
                instance.undisposed_by = self.context['request'].user  # Capture who undisposed the asset

        # Save the changes to the instance
        instance.save()

        return instance

    def create(self, validated_data):
        """Create a new disposed asset instance.

        Note: Normally, for disposal, assets are updated rather than created. This is just for demonstration.

        Args:
            validated_data (dict): The validated data for creating a new asset.

        Returns:
            Asset: The created asset instance.
        """
        # Logic for creating an asset can be added if necessary.
        raise NotImplementedError("Creating a disposed asset is not supported. Use update instead.")

    def to_representation(self, instance):
        """Customize the representation of the asset.

        This method modifies how the asset data is represented in the response.

        Args:
            instance (Asset): The asset instance to represent.

        Returns:
            dict: A dictionary representation of the asset.
        """
        representation = super().to_representation(instance)
        representation['disposed_by'] = instance.disposed_by.username if instance.disposed_by else None
        representation['undisposed_by'] = instance.undisposed_by.username if instance.undisposed_by else None
        return representation
