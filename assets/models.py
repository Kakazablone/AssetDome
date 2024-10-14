from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from datetime import date, datetime
from geopy.geocoders import Nominatim  # Or use another geolocation service
from typing import Optional, List
from PIL import Image
import os
import logging
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta


logger = logging.getLogger(__name__)

def delete_old_image(instance: object, field_name: str, default_images: Optional[List[str]] = None) -> None:
    """
    Deletes the old image file when a new image is uploaded,
    but prevents deletion of any default images.

    Args:
        instance (object): The instance containing the image field.
        field_name (str): The name of the image field on the instance.
        default_images (Optional[List[str]]): A list of default image names to be preserved.
                                               If None, a default list will be used.
    """
    try:
        # Get the old image file from the instance
        old_image = getattr(instance, field_name)

        # Set default images to prevent deletion if none are provided
        if default_images is None:
            default_images = ['default_asset.png', 'default_employee.png', 'default_profile.png']

        # Proceed if there is an old image and it's a valid file
        if old_image and os.path.isfile(old_image.path):
            # Check if the old image's name is not in the list of default images
            if not any(default_image in old_image.name for default_image in default_images):
                os.remove(old_image.path)  # Delete the old image file
                logger.info(f"Deleted old image: {old_image.path}")  # Log the deletion for debugging
            else:
                logger.info(f"Skipped deletion for default image: {old_image.name}")

    except Exception as e:
        logger.error(f"Error deleting old image: {e}")  # Log any errors encountered


User = get_user_model()

class Department(models.Model):
    """Model representing a department within an organization.

    Attributes:
        name (str): The name of the department. Must be unique.
        department_code (str): A unique code for the department.
        manager (Employee): A foreign key to the Employee model,
                            representing the manager of the department.
                            Can be null or blank.
        description (str): A description of the department. Optional.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Department Name")
    department_code = models.CharField(max_length=50, unique=True, verbose_name="Department Code")
    manager = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        verbose_name="Department Manager"
    )
    description = models.TextField(null=True, blank=True, verbose_name="Department Description")

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ['name']  # Order by name

    def __str__(self) -> str:
        """String representation of the Department model."""
        return self.name

    def save(self, *args, **kwargs) -> None:
        """Overrides the default save method to add custom logic before saving.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        logger.info(f"Saving Department: {self.name} with code: {self.department_code}")
        super().save(*args, **kwargs)  # Call the "real" save() method

    def delete(self, *args, **kwargs) -> None:
        """Overrides the default delete method to log the deletion of a department.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        logger.info(f"Deleting Department: {self.name} with code: {self.department_code}")
        super().delete(*args, **kwargs)  # Call the "real" delete() method

class Employee(models.Model):
    """Model representing an employee within an organization.

    Attributes:
        first_name (str): The first name of the employee.
        middle_name (str): The middle name of the employee (optional).
        last_name (str): The last name of the employee.
        employee_number (str): A unique employee number.
        email (str): The email address of the employee. Must be unique.
        mobile_number (str): The mobile phone number of the employee.
        job_title (str): The job title of the employee.
        date_of_birth (date): The employee's date of birth.
        date_hired (date): The date the employee was hired.
        address (str): The home address of the employee.
        department (Department): A foreign key to the Department model,
                                 representing the employee's department.
        photo (ImageField): An optional photo of the employee.
    """

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100)
    employee_number = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=20)
    job_title = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    date_hired = models.DateField()
    address = models.TextField()
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True, default='employee_photos/default_employee.png')

    def save(self, *args, **kwargs) -> None:
        """Overrides the default save method to manage image uploads and size.

        If the employee already exists, deletes the old photo before saving a new one.
        Resizes the photo to a maximum of 300x300 pixels if it's larger.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        if self.pk:  # Check if the employee instance already exists
            logger.info(f"Deleting old photo for employee: {self.first_name} {self.last_name}")
            delete_old_image(self, 'photo')

        super().save(*args, **kwargs)  # Call the "real" save() method
        logger.info(f"Saved employee: {self.first_name} {self.last_name} with ID: {self.pk}")

        if self.photo:
            img = Image.open(self.photo.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.photo.path, quality=85)
                logger.info(f"Resized photo for employee: {self.first_name} {self.last_name}")

    def __str__(self) -> str:
        """String representation of the Employee model.

        Returns:
            str: The full name of the employee.
        """
        return f"{self.first_name} {self.last_name}"
class Supplier(models.Model):
    """Model representing a supplier.

    Attributes:
        name (str): The name of the supplier.
        supplier_code (str): A unique code for the supplier.
        contact_person (str): The name of the contact person at the supplier.
        phone_number (str): The contact phone number of the supplier.
        email (str): The email address of the supplier.
        address (str): The address of the supplier.
        website (str): An optional URL for the supplier's website.
    """

    name = models.CharField(max_length=255)
    supplier_code = models.CharField(max_length=50, unique=True)
    contact_person = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    address = models.TextField()
    website = models.URLField(null=True, blank=True)

    def __str__(self) -> str:
        """String representation of the Supplier model.

        Returns:
            str: The name of the supplier.
        """
        return self.name

    def save(self, *args, **kwargs) -> None:
        """Overrides the default save method to log supplier creation or updates.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().save(*args, **kwargs)  # Call the "real" save() method
        logger.info(f"Supplier saved: {self.name} with code: {self.supplier_code}")
class Location(models.Model):
    """Model representing a physical location with automatic GPS coordinates fetching or current location usage.

    Attributes:
        name (str): The name of the location.
        longitude (Optional[float]): The longitude of the location, can be null or blank.
        latitude (Optional[float]): The latitude of the location, can be null or blank.
        use_current_location (bool): Flag indicating whether to use the current GPS location.
    """

    name: str = models.CharField(max_length=100, unique=True)
    longitude: Optional[float] = models.FloatField(null=True, blank=True)
    latitude: Optional[float] = models.FloatField(null=True, blank=True)
    use_current_location: bool = models.BooleanField(default=False)

    def save(self, *args, **kwargs) -> None:
        """Overrides the save method to fetch and set GPS coordinates based on user input or current location.

        If `use_current_location` is set to True, the model will log the provided latitude and longitude.
        If those are not provided, it will attempt to fetch them based on the location name.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        if self.use_current_location:
            if self.latitude is not None and self.longitude is not None:
                logger.info(f"Using provided coordinates for {self.name}: ({self.latitude}, {self.longitude})")
            else:
                logger.warning(f"Current location flag is set but coordinates are not provided for {self.name}.")
        elif not self.longitude or not self.latitude:
            # If longitude and latitude are not manually provided, fetch them using the location name
            geolocator = Nominatim(user_agent="your_app_name")
            try:
                location = geolocator.geocode(self.name)
                if location:
                    self.latitude = location.latitude
                    self.longitude = location.longitude
                    logger.info(f"Fetched coordinates for {self.name}: ({self.latitude}, {self.longitude})")
                else:
                    logger.error(f"Could not find coordinates for {self.name}.")
                    # Raise ValidationError for not finding coordinates
                    raise ValidationError(f"Could not find coordinates for {self.name}.")
            except Exception as e:
                logger.error(f"Geolocation service error: {str(e)}")
                # Raise ValidationError with a generic message for any other errors
                raise ValidationError("Geolocation service error. Please check the service availability.")

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """String representation of the Location model.

        Returns:
            str: The name of the location.
        """
        return self.name

class MajorCategory(models.Model):
    """Model representing a major category for an asset.

    Attributes:
        name (str): The unique name of the major category.
    """

    name: str = models.CharField(max_length=100, unique=True)

    def save(self, *args, **kwargs) -> None:
        """Overrides the save method to log when a major category is created or updated.

        If the category is new (not yet saved), it logs a creation message.
        If it already exists, it logs an update message.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        if self.pk is None:
            logger.info(f"Creating a new major category: '{self.name}'")
        else:
            logger.info(f"Updating major category: '{self.name}'")

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """String representation of the MajorCategory model.

        Returns:
            str: The name of the major category.
        """
        return self.name


class MinorCategory(models.Model):
    """Model representing a minor category within a major category.

    Attributes:
        name (str): The name of the minor category.
        major_category (MajorCategory): The related major category to which this minor category belongs.
    """

    name: str = models.CharField(max_length=100, unique=True)
    major_category: MajorCategory = models.ForeignKey(MajorCategory, on_delete=models.CASCADE)

    def save(self, *args, **kwargs) -> None:
        """Overrides the save method to log creation or update of a minor category.

        Logs the creation or update of a minor category along with its associated major category.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        if self.pk is None:
            logger.info(f"Creating a new minor category: '{self.name}' under '{self.major_category.name}'")
        else:
            logger.info(f"Updating minor category: '{self.name}' under '{self.major_category.name}'")

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """String representation of the MinorCategory model.

        Returns:
            str: The name of the minor category along with its major category.
        """
        return f"{self.name} (Major Category: {self.major_category.name})"


class Asset(models.Model):
    """Model representing an asset."""

    # Constants for choices
    ASSET_TYPE_CHOICES = [
        ('MOVABLE', 'Movable'),
        ('IMMOVABLE', 'Immovable')
    ]

    CONDITION_CHOICES = [
        ('NEW', 'New'),
        ('VERY_GOOD', 'Very Good'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('FAULTY', 'Faulty'),
        ('BROKEN', 'Broken'),
        ('OBSOLETE', 'Obsolete')
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive')
    ]

    DEPRECIATION_METHOD_CHOICES = [
        ('STRAIGHT_LINE', 'Straight Line'),
        ('DECLINING_BALANCE', 'Declining Balance')
    ]

    asset_code = models.CharField(max_length=10, unique=True, editable=False)
    barcode = models.CharField(max_length=255, unique=True)
    rfid = models.CharField(max_length=255, null=True, blank=True)
    major_category = models.ForeignKey(MajorCategory, on_delete=models.CASCADE, related_name='assets')
    minor_category = models.ForeignKey(MinorCategory, on_delete=models.CASCADE, related_name='assets')
    description = models.TextField()
    serial_number = models.CharField(max_length=100, null=True, blank=True)
    model_number = models.CharField(max_length=100, null=True, blank=True)
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPE_CHOICES)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='assets')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='assets')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='assets')
    economic_life = models.IntegerField(default=5)  # Set a default
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    price_is_per_unit = models.BooleanField(default=False)
    net_book_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=False)
    revalued_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    units = models.PositiveIntegerField(default=0)
    date_of_purchase = models.DateField()
    date_placed_in_service = models.DateField()
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    depreciation_method = models.CharField(max_length=50, choices=DEPRECIATION_METHOD_CHOICES, default='STRAIGHT_LINE')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assets_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assets_updated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    asset_image = models.ImageField(upload_to='asset_images/', null=True, blank=True, default='asset_images/default_asset.png')
    disposed_at = models.DateTimeField(null=True, blank=True)
    undisposed_at = models.DateTimeField(null=True, blank=True)
    is_disposed = models.BooleanField(default=False)
    disposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets_disposed')
    undisposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='undisposed_assets')
    accumulated_depreciation = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def save(self, *args, **kwargs) -> None:
        """Overrides the save method to manage asset properties and log changes."""
        if self.pk:  # Check if the asset is being updated
            delete_old_image(self, 'asset_image')

        if not self.asset_code:
            self.asset_code = self.generate_asset_code()

        self.economic_life = self.set_economic_life()
        self.validate_purchase_price()
        self.validate_dates()
        self.is_price_per_unit()

        self.net_book_value = self.calculate_depreciation()
        self.accumulated_depreciation = self.calculate_accumulated_depreciation()

        super().save(*args, **kwargs)
        self.resize_image_if_needed()

    def is_price_per_unit(self) -> float:
        # If price_is_per_unit is True, calculate total price
        if self.price_is_per_unit:
            self.purchase_price = self.purchase_price * self.units

    def generate_asset_code(self) -> str:
        """Generates a new asset code based on existing codes."""
        last_asset = Asset.objects.order_by('-id').first()
        new_code = 'AS000001' if not last_asset else f'AS{int(last_asset.asset_code[2:]) + 1:06d}'
        logger.info(f"Generated new asset code: {new_code}")
        return new_code

    def validate_purchase_price(self):
        """Validate the purchase price."""
        if self.purchase_price < 0:
            raise ValidationError("Purchase price cannot be negative.")
        return self.purchase_price

    def set_economic_life(self) -> int:
        """Sets the economic life based on the major category."""
        economic_life_mapping = {
        'Furniture': 8,
        'ICT': 3
        }
        return economic_life_mapping.get(self.major_category.name, 5)

    def validate_date_of_purchase(self):
        """Validate that the date of purchase is not later than the current date."""
        if self.date_of_purchase > timezone.now().date():
            raise ValidationError("Date of purchase cannot be in the future.")

    def validate_dates(self):
        """Validate that the placed in service date is not later than the current date and is required."""
        # Check if date_placed_in_service is None
        if self.date_placed_in_service is None:
            raise ValidationError("The 'date placed in service' field is required.")

        # Check if date_of_purchase is None
        if self.date_of_purchase is None:
            raise ValidationError("The 'date of purchase' field is required.")

        # Check if the date placed in service is in the future
        if self.date_placed_in_service > timezone.now().date():
            raise ValidationError("Date placed in service cannot be in the future.")

    def resize_image_if_needed(self) -> None:
        """Resizes the asset image if it exceeds the specified dimensions."""
        if self.asset_image:
            img = Image.open(self.asset_image.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.asset_image.path, quality=85)
                logger.info(f"Resized asset image for asset {self.asset_code} to {output_size}")

    def calculate_depreciation(self) -> float:
        """Calculates net book value based on depreciation method.

        Returns:
            float: The calculated net book value of the asset.
        """
        if isinstance(self.date_of_purchase, str):
            self.date_of_purchase = datetime.strptime(self.date_of_purchase, '%Y-%m-%d').date()

        # Calculate years in use as a float
        days_in_use = (date.today() - self.date_of_purchase).days
        years_in_use = Decimal(days_in_use) / Decimal(365.25)  # Convert days to years

        # Straight-Line Depreciation
        if self.depreciation_method == 'STRAIGHT_LINE':
            annual_depreciation = Decimal(self.purchase_price) / Decimal(self.economic_life)
            net_value = max(Decimal(0), Decimal(self.purchase_price) - (years_in_use * annual_depreciation))

        # Declining Balance Depreciation
        elif self.depreciation_method == 'DECLINING_BALANCE':
            depreciation_rate = Decimal(2) / Decimal(self.economic_life)  # 200% declining balance
            net_value = Decimal(self.purchase_price)
            for year in range(int(years_in_use)):  # Loop for full years only
                net_value -= net_value * depreciation_rate
            net_value = max(Decimal(0), net_value)  # Ensure it doesn't go below 0

        logger.info(f"Calculated net book value for asset {self.asset_code}: {net_value}")
        return float(net_value)

    def calculate_accumulated_depreciation(self) -> float:
        """Calculates accumulated depreciation for the asset.

        Returns:
            float: The accumulated depreciation based on years in use.
        """

        # Ensure date_of_purchase is a date object
        if isinstance(self.date_of_purchase, str):
            self.date_of_purchase = datetime.strptime(self.date_of_purchase, '%Y-%m-%d').date()

        # Calculate years in use as a float
        days_in_use = (date.today() - self.date_of_purchase).days
        years_in_use = Decimal(days_in_use) / Decimal(365.25)  # Convert days to years

        if years_in_use <= 0:
            return 0.0  # No depreciation for unused assets

        # Straight-Line Depreciation
        if self.depreciation_method == 'STRAIGHT_LINE':
            annual_depreciation = Decimal(self.purchase_price) / Decimal(self.economic_life)
            accumulated_depreciation = min(annual_depreciation * years_in_use, Decimal(self.purchase_price))

        # Declining Balance Depreciation
        elif self.depreciation_method == 'DECLINING_BALANCE':
            depreciation_rate = Decimal(2) / Decimal(self.economic_life)  # 200% declining balance
            accumulated_depreciation = Decimal(0)
            net_value = Decimal(self.purchase_price)
            for year in range(int(years_in_use)):  # Loop for full years only
                depreciation = net_value * depreciation_rate
                accumulated_depreciation += depreciation
                net_value -= depreciation

        logger.info(f"Calculated accumulated depreciation for asset {self.asset_code}: {accumulated_depreciation}")
        return float(accumulated_depreciation)

    def __str__(self) -> str:
        """Returns a string representation of the asset."""
        return f"{self.asset_code} - {self.description}"
