from rest_framework import status
from rest_framework.test import APITestCase
from assets.models import Department, Employee, Supplier, Location, MajorCategory, MinorCategory, Asset
from assets.serializers import DepartmentSerializer, EmployeeSerializer
from django.core.exceptions import ValidationError
from unittest.mock import patch
import logging
from .test_models import AuthenticatedAPITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from datetime import date, timedelta, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

class DepartmentSerializerAPITests(AuthenticatedAPITestCase):
    """Tests for DepartmentSerializer with APITestCase and API validation."""
    def setUp(self):
        super().setUp()
        """Set up valid department data for testing."""
        self.department_data = {
            'name': 'Human Resources',
            'department_code': 'DEP001',
            'description': 'Responsible for managing employee relations',
        }
        self.department = Department.objects.create(**self.department_data)
        self.valid_update_data = {
            'name': 'HR',
            'department_code': 'DEP001',
            'description': 'Updated description for HR',
        }
        self.invalid_department_data = {
            'name': '',
            'department_code': '',
            'description': 'This should raise a validation error',
        }
        self.create_url = '/api/departments/'  # Adjust this based on your API endpoint
        self.update_url = f'/api/departments/{self.department.id}/'  # Update URL for existing department

    def test_create_department_success(self):
        """Test that a department can be created successfully."""
        data = {
            'name': 'Cyber Security',
            'department_code': 'DEP005',
            'description': 'Responsible for managing company data',
        }
        response = self.client.post(self.create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], data['name'])
        self.assertEqual(response.data['description'], data['description'])

    def test_create_department_invalid_data(self):
        """Test that creating a department with invalid data fails."""
        response = self.client.post(self.create_url, self.invalid_department_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)  # Assuming 'name' field is required

    def test_update_department_success(self):
        """Test that a department can be updated successfully."""
        response = self.client.put(self.update_url, self.valid_update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.valid_update_data['name'])
        self.assertEqual(response.data['description'], self.valid_update_data['description'])

    def test_update_department_invalid_data(self):
        """Test that updating a department with invalid data fails."""
        response = self.client.put(self.update_url, self.invalid_department_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)  # Assuming 'name' field is required

    def test_update_department_not_found(self):
        """Test that updating a non-existing department returns 404."""
        non_existing_url = '/api/departments/9999/'  # An ID that doesn't exist
        response = self.client.put(non_existing_url, self.valid_update_data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_string_representation(self):
        """Check the string representation of the Department serializer."""
        serializer = DepartmentSerializer(instance=self.department)
        self.assertEqual(str(serializer.instance), self.department.name)

    def test_department_serializer_fields(self):
        """Test that the serializer includes the correct fields."""
        serializer = DepartmentSerializer(instance=self.department)
        expected_fields = set(['id', 'name', 'description', 'department_code', 'manager'])
        self.assertSetEqual(set(serializer.data.keys()), expected_fields)

    @patch('assets.serializers.logger.info')  # Patching the logger used in the serializer
    def test_create_department_logging(self, mock_logger):
        """Test that the logging occurs during department creation."""
        data = self.department_data.copy()
        data['name'] = "Finance"
        data['department_code'] = "DEP002"
        self.client.post(self.create_url, data)
        mock_logger.assert_called_once_with('Created Department: Finance')

    @patch('assets.serializers.logger.info')  # Patching the logger used in the serializer
    def test_update_department_logging(self, mock_logger):
        """Test that the logging occurs during department update."""
        self.client.put(self.update_url, self.valid_update_data)
        mock_logger.assert_called_once_with('Updated Department: HR')

    def test_department_creation_with_missing_fields(self):
        """Test that an error is raised when creating a department without required fields."""
        incomplete_data = {'description': 'Missing name field'}
        response = self.client.post(self.create_url, incomplete_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    def test_department_update_with_missing_fields(self):
        """Test that an error is raised when updating a department without required fields."""
        incomplete_update_data = {'description': 'Updated description but missing name'}
        response = self.client.put(self.update_url, incomplete_update_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

class EmployeeSerializerAPITests(AuthenticatedAPITestCase):
    """Tests for EmployeeSerializer with APITestCase and API validation."""

    def setUp(self):
        """Set up initial data for the tests."""
        super().setUp()
        self.department = Department.objects.create(name='Finance', department_code='FIN001', manager=None)
        self.valid_employee_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'date_hired': '2010-01-01',
            'department': 'Finance',
            'employee_number': 7,
            'email': 'jd@gmail.com',
            'mobile_number': '0707000000',
            'job_title': 'Finance Manager',
            'address': '4040 Nairobi'
        }
        self.invalid_employee_data = {
            'first_name': 'Ben',
            'last_name': 'Kimani',
            'date_of_birth': '2010-01-01',
            'date_hired': '2010-01-01',
            'department': 'Finance',
            'employee_number': 9,
            'email': 'bk@gmail.com',
            'mobile_number': '0707000000',
            'job_title': 'Asst Finance Manager',
            'address': '4040 Nairobi'
        }

    def test_create_employee_success(self):
        """Test successful creation of an employee."""
        response = self.client.post('/api/employees/', self.valid_employee_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Validate that the employee is in the database
        employee = Employee.objects.get(first_name='John')
        self.assertEqual(employee.department, self.department)

    def test_create_employee_age_validation(self):
        """Test validation for employee age (must be 18 or older at hiring)."""
        response = self.client.post('/api/employees/', self.invalid_employee_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Employee must be at least 18 years old at the time of hiring.", response.data['non_field_errors'])

    @patch('assets.serializers.logger.info')
    def test_create_employee_logging(self, mock_logger):
        """Test that logging occurs during employee creation."""
        data = {
            'first_name': 'Kagu',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'date_hired': '2010-01-01',
            'department': 'Finance',
            'employee_number': 4,
            'email': 'kagu@gmail.com',
            'mobile_number': '0707000000',
            'job_title': 'Finance Manager',
            'address': '4040 Nairobi'
        }
        response = self.client.post('/api/employees/', data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert logger was called correctly
        mock_logger.assert_called_once_with('Created Employee: Kagu in Department: Finance')

    @patch('assets.serializers.logger.info')
    def test_update_employee_logging(self, mock_logger):
        """Test that logging occurs during employee update."""
        employee = Employee.objects.create(
            first_name='Evans',
            last_name='Kadenyi',
            date_of_birth='1990-01-01',
            date_hired='2010-01-01',
            department=self.department,
            email='Kadenyi@gmail.com',
            address='4040 Nbi',
            employee_number='25',
            mobile_number='0707000000',
            job_title='Accountant'
        )

        update_data = {
            'first_name': 'Michael',
            'last_name': 'Njue',
            'date_of_birth': '1990-01-01',
            'date_hired': '2010-01-01',
            'department': 'Finance',
        }

        response = self.client.patch(f'/api/employees/{employee.id}/', update_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert logger was called with correct update message
        mock_logger.assert_called_once_with('Updated Employee: Michael in Department: Finance')

    def test_employee_photo_validation_failure(self):
        """Test failure of photo validation due to invalid file type."""
        invalid_photo_data = self.valid_employee_data
        invalid_photo_data['photo'] = SimpleUploadedFile(
            name='invalid_image.txt',
            content=b'sample content',
            content_type='text/plain'
        )
        response = self.client.post('/api/employees/', invalid_photo_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Upload a valid image", str(response.data))

    def test_employee_serializer_fields(self):
        """Test that the serializer includes all the correct fields."""
        employee = Employee.objects.create(
            first_name='Kasmuel',
            last_name='McOure',
            date_of_birth='1990-01-01',
            date_hired='2010-01-01',
            department=self.department,
            email='KmcOure@gmail.com',
            address='4040 Nbi',
            employee_number='19',
            mobile_number='0707000000',
            job_title='Accountant'
        )
        serializer = EmployeeSerializer(employee)

        expected_fields = {'id', 'first_name', 'last_name', 'date_of_birth', 'date_hired', 'department', 'photo', 'email',
                           'address', 'employee_number', 'mobile_number', 'job_title', 'middle_name'}
        self.assertSetEqual(set(serializer.data.keys()), expected_fields)

class SupplierSerializerAPITests(AuthenticatedAPITestCase):
    """Tests for LocationSerializer with APITestCase and API validation."""
    def setUp(self):
        """Set up initial data for the tests"""
        super().setUp()
        self.valid_supplier_data = {
            'name': 'Supplier A',
            'email': 'supplierA@example.com',
            'phone_number': '1234567890',
            'address': '1234 Some Street',
            'supplier_code': 'SUP001',
            'contact_person': 'Head of Supply Chain'
        }

    def test_create_supplier_valid_data(self):
        """Test creating a supplier with valid data."""
        response = self.client.post('/api/suppliers/', self.valid_supplier_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supplier.objects.count(), 1)
        self.assertEqual(Supplier.objects.get().name, 'Supplier A')

    def test_create_supplier_invalid_data(self):
        """Test creating a supplier with invalid data."""
        invalid_supplier_data = self.valid_supplier_data.copy()
        invalid_supplier_data['email'] = 'invalid-email'  # Invalid email format

        response = self.client.post('/api/suppliers/', invalid_supplier_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_update_supplier_valid_data(self):
        """Test updating a supplier with valid data."""
        supplier = Supplier.objects.create(**self.valid_supplier_data)
        update_data = {
            'name': 'Supplier B',
            'email': 'supplierB@example.com',
            'phone_number': '9876543210',
        }

        response = self.client.patch(f'/api/suppliers/{supplier.id}/', update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        supplier.refresh_from_db()
        self.assertEqual(supplier.name, 'Supplier B')
        self.assertEqual(supplier.email, 'supplierB@example.com')

    def test_update_supplier_invalid_data(self):
        """Test updating a supplier with invalid data."""
        supplier = Supplier.objects.create(**self.valid_supplier_data)
        invalid_update_data = {
            'name': '',
            'email': 'invalid-email',
        }

        response = self.client.patch(f'/api/suppliers/{supplier.id}/', invalid_update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('name', response.data)

    @patch('assets.serializers.logger.info')
    def test_create_supplier_logging(self, mock_logger):
        """Test that logging occurs during supplier creation."""
        response = self.client.post('/api/suppliers/', self.valid_supplier_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert logger was called with correct message
        mock_logger.assert_called_once_with('Created Supplier: Supplier A')

    @patch('assets.serializers.logger.info')
    def test_update_supplier_logging(self, mock_logger):
        """Test that logging occurs during supplier update."""
        supplier = Supplier.objects.create(**self.valid_supplier_data)
        update_data = {
            'name': 'Supplier B',
            'email': 'supplierB@example.com',
        }

        response = self.client.patch(f'/api/suppliers/{supplier.id}/', update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert logger was called with correct update message
        mock_logger.assert_called_once_with('Updated Supplier: Supplier B')

class LocationSerializerAPITests(AuthenticatedAPITestCase):
    """Tests for LocationSerializer with APITestCase and API validation."""
    def setUp(self):
        """Set up initial data for the tests."""
        super().setUp()
        self.valid_location_data = {
            'name': 'Test Location',
            'use_current_location': False
        }

    @patch('assets.serializers.LocationSerializer.geocode_location')
    def test_create_location_with_valid_data(self, mock_geocode):
        """Test creating a location with valid data using geocoding."""
        mock_geocode.return_value = (12.34, 56.78)
        response = self.client.post('/api/locations/', self.valid_location_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        location = Location.objects.get(name='Test Location')
        self.assertEqual(location.longitude, 12.34)
        self.assertEqual(location.latitude, 56.78)

    @patch('assets.serializers.LocationSerializer.get_current_location')
    def test_create_location_with_current_location(self, mock_current_location):
        """Test creating a location by using the current location coordinates."""
        mock_current_location.return_value = (98.76, 54.32)
        location_data = self.valid_location_data.copy()
        location_data['use_current_location'] = True

        response = self.client.post('/api/locations/', location_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        location = Location.objects.get(name='Test Location')
        self.assertEqual(location.longitude, 98.76)
        self.assertEqual(location.latitude, 54.32)

    # @patch('assets.serializers.LocationSerializer.geocode_location')
    # def test_create_location_geocoding_failure(self, mock_geocode):
    #     """Test creating a location when geocoding fails."""
    #     # Simulate geocoding failure
    #     mock_geocode.side_effect = GeocoderUnavailable

    #     response = self.client.post('/api/locations/', self.valid_location_data, format='json')
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    #     location = Location.objects.get(name='Test Location')
    #     self.assertEqual(location.longitude, 0.0)
    #     self.assertEqual(location.latitude, 0.0)

    @patch('assets.serializers.LocationSerializer.geocode_location')
    def test_update_location_with_valid_data(self, mock_geocode):
        """Test updating a location with valid data using geocoding."""
        location = Location.objects.create(name='Valid Location', longitude=12.34, latitude=56.78)
        updated_data = {'name': 'Updated Location', 'use_current_location': False}
        mock_geocode.return_value = (34.56, 78.90)

        response = self.client.put(f'/api/locations/{location.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        location.refresh_from_db()
        self.assertEqual(location.name, 'Updated Location')
        self.assertEqual(location.longitude, 34.56)
        self.assertEqual(location.latitude, 78.90)

    @patch('assets.serializers.LocationSerializer.get_current_location')
    def test_update_location_using_current_location(self, mock_current_location):
        """Test updating a location by using current location coordinates."""
        location = Location.objects.create(name='Valid Location', longitude=12.34, latitude=56.78)
        updated_data = {'name': 'Updated Location', 'use_current_location': True}
        mock_current_location.return_value = (11.22, 33.44)

        response = self.client.put(f'/api/locations/{location.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        location.refresh_from_db()
        self.assertEqual(location.name, 'Updated Location')
        self.assertEqual(location.longitude, 11.22)
        self.assertEqual(location.latitude, 33.44)

    # def test_longitude_latitude_read_only(self):
    #     """Test that longitude and latitude are read-only fields."""
    #     location_data = self.valid_location_data.copy()
    #     location_data['longitude'] = 50.0
    #     location_data['latitude'] = 50.0

    #     response = self.client.post('/api/locations/', location_data, format='json')
    #     self.assertNotIn('longitude', response.data)
    #     self.assertNotIn('latitude', response.data)

class MajorCategorySerializerAPITests(AuthenticatedAPITestCase):
    """Test suite for MajorCategorySerializer API functionality."""

    def setUp(self):
        """Set up test variables and create a test MajorCategory."""
        super().setUp()
        self.valid_category_data = {
            'name': 'Test Category'
        }
        self.category_instance = MajorCategory.objects.create(**self.valid_category_data)

    def test_create_major_category(self):
        """Test creating a new major category."""
        data = {
            'name': 'Test B Category'
        }
        response = self.client.post('/api/major_categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        category = MajorCategory.objects.get(name='Test B Category')
        self.assertEqual(category.name, 'Test B Category')

    def test_create_duplicate_major_category(self):
        """Test creating a duplicate major category."""
        self.client.post('/api/major_categories/', self.valid_category_data, format='json')
        response = self.client.post('/api/major_categories/', self.valid_category_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_major_category(self):
        """Test updating an existing major category."""
        updated_data = {
            'name': 'Updated Category'
        }
        response = self.client.patch(f'/api/major_categories/{self.category_instance.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.category_instance.refresh_from_db()  # Refresh to get the updated instance
        self.assertEqual(self.category_instance.name, 'Updated Category')

    def test_update_non_existent_major_category(self):
        """Test updating a non-existent major category."""
        updated_data = {
            'name': 'Non-Existent Category'
        }
        response = self.client.patch('/api/major_categories/999/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_major_category_invalid_data(self):
        """Test creating a major category with invalid data."""
        invalid_data = {
            'name': ''  # Invalid because name cannot be empty
        }
        response = self.client.post('/api/major_categories/', invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_major_category_invalid_data(self):
        """Test updating a major category with invalid data."""
        invalid_data = {
            'name': ''  # Invalid because name cannot be empty
        }
        response = self.client.patch(f'/api/major_categories/{self.category_instance.id}/', invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_major_category(self):
        """Test retrieving a major category."""
        response = self.client.get(f'/api/major_categories/{self.category_instance.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.category_instance.name)

    def test_get_non_existent_major_category(self):
        """Test retrieving a non-existent major category."""
        response = self.client.get('/api/major_categories/999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_major_categories(self):
        """Test retrieving all major categories."""
        response = self.client.get('/api/major_categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)  # Ensure there is at least one category

    def test_delete_major_category(self):
        """Test deleting an existing major category."""
        response = self.client.delete(f'/api/major_categories/{self.category_instance.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(MajorCategory.DoesNotExist):
            MajorCategory.objects.get(id=self.category_instance.id)

    def test_delete_non_existent_major_category(self):
        """Test deleting a non-existent major category."""
        response = self.client.delete('/api/major_categories/999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('assets.serializers.MajorCategorySerializer.create')
    def test_create_major_category_logging(self, mock_create):
        """Test that logging occurs when creating a major category."""
        data = {
            'name': 'Test C Category'
        }
        response = self.client.post('/api/major_categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_create.assert_called_once_with(data)

    @patch('assets.serializers.MajorCategorySerializer.update')
    def test_update_major_category_logging(self, mock_update):
        """Test that logging occurs when updating a major category."""
        mock_update.return_value = self.category_instance
        updated_data = {'name': 'New Name'}
        response = self.client.patch(f'/api/major_categories/{self.category_instance.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_update.assert_called_once_with(self.category_instance, updated_data)

    def test_create_major_category_no_name(self):
        """Test creating a major category without a name."""
        response = self.client.post('/api/major_categories/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_major_category_with_empty_name(self):
        """Test updating a major category with an empty name."""
        response = self.client.patch(f'/api/major_categories/{self.category_instance.id}/', {'name': ''}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_major_category_with_whitespace_name(self):
        """Test updating a major category with a name that is only whitespace."""
        response = self.client.patch(f'/api/major_categories/{self.category_instance.id}/', {'name': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_major_category_with_special_characters(self):
        """Test creating a major category with special characters in the name."""
        special_char_data = {'name': '@#$%^&*()'}
        response = self.client.post('/api/major_categories/', special_char_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_major_category_with_special_characters(self):
        """Test updating a major category with special characters in the name."""
        special_char_data = {'name': '@#$%^&*()'}
        response = self.client.patch(f'/api/major_categories/{self.category_instance.id}/', special_char_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_major_category_with_special_characters(self):
        """Test retrieving a major category with special characters in the name."""
        special_char_data = {'name': '@#$%^&*()'}
        special_category = MajorCategory.objects.create(**special_char_data)
        response = self.client.get(f'/api/major_categories/{special_category.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], special_char_data['name'])

class MinorCategorySerializerAPITests(AuthenticatedAPITestCase):
    """Test suite for MinorCategorySerializer API functionality."""

    def setUp(self):
        """Set up test variables and create a test MajorCategory and MinorCategory."""
        super().setUp()
        self.major_category_data = {'name': 'Test Major Category'}
        self.major_category_instance = MajorCategory.objects.create(**self.major_category_data)

        self.valid_minor_category_data = {
            'name': 'Test Minor Category',
            'major_category': self.major_category_instance
        }
        self.minor_category_instance = MinorCategory.objects.create(**self.valid_minor_category_data)

    def test_create_minor_category(self):
        """Test creating a new minor category."""
        data = {
            'name': 'Test Minor B Category',
            'major_category': 'Test Major Category'
        }
        response = self.client.post('/api/minor_categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        category = MinorCategory.objects.get(name='Test Minor B Category')
        self.assertEqual(category.name, 'Test Minor B Category')
        self.assertEqual(category.major_category, self.major_category_instance)

    def test_create_minor_category_invalid_major_category(self):
        """Test creating a minor category with a non-existent major category."""
        invalid_data = {
            'name': 'Invalid Minor Category',
            'major_category': 'Non-Existent Major'
        }
        response = self.client.post('/api/minor_categories/', invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_duplicate_minor_category(self):
        """Test creating a duplicate minor category."""
        data = {
            'name': 'Test Minor Category',
            'major_category': 'Test Major Category'
        }
        # self.client.post('/api/minor_categories/', data, format='json')
        response = self.client.post('/api/minor_categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_minor_category(self):
        """Test updating an existing minor category."""
        updated_data = {
            'name': 'Updated Minor Category',
            'major_category': self.major_category_instance.name
        }
        response = self.client.patch(f'/api/minor_categories/{self.minor_category_instance.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.minor_category_instance.refresh_from_db()  # Refresh to get the updated instance
        self.assertEqual(self.minor_category_instance.name, 'Updated Minor Category')

    def test_update_non_existent_minor_category(self):
        """Test updating a non-existent minor category."""
        updated_data = {
            'name': 'Non-Existent Category',
            'major_category': self.major_category_instance.name
        }
        response = self.client.patch('/api/minor_categories/999/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_minor_category_invalid_major_category(self):
        """Test updating a minor category with a non-existent major category."""
        updated_data = {
            'name': 'Updated Minor Category',
            'major_category': 'Non-Existent Major'
        }
        response = self.client.patch(f'/api/minor_categories/{self.minor_category_instance.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_minor_category_invalid_data(self):
        """Test creating a minor category with invalid data."""
        invalid_data = {
            'name': '',  # Invalid because name cannot be empty
            'major_category': self.major_category_instance.name
        }
        response = self.client.post('/api/minor_categories/', invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_minor_category_invalid_data(self):
        """Test updating a minor category with invalid data."""
        invalid_data = {
            'name': '',  # Invalid because name cannot be empty
            'major_category': self.major_category_instance.name
        }
        response = self.client.patch(f'/api/minor_categories/{self.minor_category_instance.id}/', invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_minor_category(self):
        """Test retrieving a minor category."""
        response = self.client.get(f'/api/minor_categories/{self.minor_category_instance.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.minor_category_instance.name)

    def test_get_non_existent_minor_category(self):
        """Test retrieving a non-existent minor category."""
        response = self.client.get('/api/minor_categories/999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_minor_categories(self):
        """Test retrieving all minor categories."""
        response = self.client.get('/api/minor_categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)  # Ensure there is at least one category

    def test_delete_minor_category(self):
        """Test deleting an existing minor category."""
        response = self.client.delete(f'/api/minor_categories/{self.minor_category_instance.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(MinorCategory.DoesNotExist):
            MinorCategory.objects.get(id=self.minor_category_instance.id)

    def test_delete_non_existent_minor_category(self):
        """Test deleting a non-existent minor category."""
        response = self.client.delete('/api/minor_categories/999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('assets.serializers.MinorCategorySerializer.create')
    def test_create_minor_category_logging(self, mock_create):
        """Test that logging occurs when creating a minor category."""
        # Set up the MajorCategory instance
        major_category = MajorCategory.objects.create(name='Test Major B Category')

        # Set up the data, passing the actual MajorCategory instance
        data = {
            'name': 'Test B Minor Category',
            'major_category': major_category.name
        }

        # Simulate the response that the view would return
        mock_create.return_value = self.minor_category_instance

        response = self.client.post('/api/minor_categories/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Update the assertion to reflect the actual method call
        expected_call_data = {
            'name': 'Test B Minor Category',
            'major_category': major_category  # The actual MajorCategory instance
        }
        mock_create.assert_called_once_with(expected_call_data)

    @patch('assets.serializers.MinorCategorySerializer.update')
    def test_update_minor_category_logging(self, mock_update):
        """Test that logging occurs when updating a minor category."""
        # Mock the return value of the update method
        mock_update.return_value = self.minor_category_instance

        # Set up the updated data with the MajorCategory instance
        updated_data = {
            'name': 'New Name',
            'major_category': self.major_category_instance.name
        }

        # Perform the PATCH request
        response = self.client.patch(f'/api/minor_categories/{self.minor_category_instance.id}/', updated_data, format='json')

        # Assert that the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Prepare the expected data for the update call
        expected_call_data = {
            'name': 'New Name',
            'major_category': self.major_category_instance  # The actual MajorCategory instance
        }

        # Assert that the update method was called once with the correct arguments
        mock_update.assert_called_once_with(self.minor_category_instance, expected_call_data)

    def test_create_minor_category_no_name(self):
        """Test creating a minor category without a name."""
        response = self.client.post('/api/minor_categories/', {'major_category': self.major_category_instance.name}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_minor_category_with_empty_name(self):
        """Test updating a minor category with an empty name."""
        response = self.client.patch(f'/api/minor_categories/{self.minor_category_instance.id}/', {'name': '', 'major_category': self.major_category_instance.name}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_minor_category_with_whitespace_name(self):
        """Test updating a minor category with a name that is only whitespace."""
        response = self.client.patch(f'/api/minor_categories/{self.minor_category_instance.id}/', {'name': '   ', 'major_category': self.major_category_instance.name}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_minor_category_with_special_characters(self):
        """Test creating a minor category with special characters in the name."""
        special_char_data = {'name': '@#$%^&*()', 'major_category': self.major_category_instance.name}
        response = self.client.post('/api/minor_categories/', special_char_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_minor_category_with_special_characters(self):
        """Test updating a minor category with special characters in the name."""
        special_char_data = {'name': '@#$%^&*()', 'major_category': self.major_category_instance.name}
        response = self.client.patch(f'/api/minor_categories/{self.minor_category_instance.id}/', special_char_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_minor_category_with_special_characters(self):
        """Test retrieving a minor category with special characters in the name."""
        special_char_data = {'name': '@#$%^&*()', 'major_category': self.major_category_instance}
        special_minor_category = MinorCategory.objects.create(**special_char_data)
        response = self.client.get(f'/api/minor_categories/{special_minor_category.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], special_char_data['name'])

class AssetSerializerAPITests(AuthenticatedAPITestCase):
    """Test suite for MinorCategorySerializer API functionality."""
    def setUp(self):
        """Set up various models to use to run tests in this class"""
        super().setUp()
        self.major_category = MajorCategory.objects.create(name='Furniture')
        self.minor_category = MinorCategory.objects.create(name='Chair', major_category=self.major_category)
        self.location = Location.objects.create(name='Office')
        self.department = Department.objects.create(name='HR')
        self.supplier = Supplier.objects.create(name='ABC Supplies')
        self.employee = Employee.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            date_of_birth=date(1995, 1, 1),
            employee_number=2,
            mobile_number="0711111111",
            job_title="Software Engineer",
            address="1234",
            date_hired=date(2021, 1, 1),
            department=self.department
        )

        self.valid_payload = {
            'description': 'Office Chair',
            'major_category': self.major_category.name,
            'minor_category': self.minor_category.name,
            'department': self.department.name,
            'location': self.location.name,
            'employee': self.employee.first_name,
            'supplier': self.supplier.name,
            'purchase_price': 150.00,
            'units': 10,
            'date_of_purchase': date.today(),
            'date_placed_in_service': date.today(),
            'barcode': '123456789012',
            'asset_type': 'MOVABLE',
            'condition': 'NEW',
            'status': 'ACTIVE'
        }

        self.valid_instance= {
            'description': 'Office Chair',
            'major_category': self.major_category,
            'minor_category': self.minor_category,
            'department': self.department,
            'location': self.location,
            'employee': self.employee,
            'supplier': self.supplier,
            'purchase_price': 150.00,
            'units': 10,
            'date_of_purchase': date.today(),
            'date_placed_in_service': date.today(),
            'barcode': '123456789012',
            'asset_type': 'MOVABLE',
            'condition': 'NEW',
            'status': 'ACTIVE'
        }

    def test_create_asset(self):
        """Test successful asset creation."""
        response = self.client.post(reverse('asset-list'), self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Asset.objects.count(), 1)
        self.assertEqual(Asset.objects.first().description, 'Office Chair')

    def test_create_asset_negative_price(self):
        """Test validation for negative purchase price."""
        invalid_payload = self.valid_payload.copy()
        invalid_payload['purchase_price'] = -100

        response = self.client.post(reverse('asset-list'), invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('purchase_price', response.data)
        self.assertEqual(response.data['purchase_price'][0], 'Purchase price cannot be negative.')

    def test_create_asset_negative_units(self):
        """Test validation for negative units."""
        invalid_payload = self.valid_payload.copy()
        invalid_payload['units'] = -5

        response = self.client.post(reverse('asset-list'), invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('units', response.data)
        self.assertEqual(response.data['units'][0], 'Units must be a positive integer greater than 0.')

    def test_create_asset_future_purchase_date(self):
        """Test validation for future date of purchase."""
        invalid_payload = self.valid_payload.copy()
        invalid_payload['date_of_purchase'] = (date.today() + timedelta(days=1)).isoformat()

        response = self.client.post(reverse('asset-list'), invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_purchase', response.data)
        self.assertEqual(response.data['date_of_purchase'][0], 'Date of purchase cannot be in the future.')

    def test_create_asset_future_service_date(self):
        """Test validation for future date placed in service."""
        invalid_payload = self.valid_payload.copy()
        invalid_payload['date_placed_in_service'] = (date.today() + timedelta(days=1)).isoformat()

        response = self.client.post(reverse('asset-list'), invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_placed_in_service', response.data)
        self.assertEqual(response.data['date_placed_in_service'][0], 'Date placed in service cannot be in the future.')

    def test_create_asset_duplicate_barcode(self):
        """Test validation for duplicate barcode."""
        # First, create an asset with a barcode
        self.client.post(reverse('asset-list'), self.valid_payload, format='json')

        # Try to create another asset with the same barcode
        duplicate_payload = self.valid_payload.copy()
        response = self.client.post(reverse('asset-list'), duplicate_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('barcode', response.data)
        self.assertEqual(response.data['barcode'][0], 'asset with this barcode already exists.')

    def test_update_asset(self):
        """Test updating an asset successfully."""
        asset = Asset.objects.create(**self.valid_instance)
        update_payload = self.valid_payload.copy()
        update_payload['description'] = 'Updated Office Chair'

        response = self.client.patch(reverse('asset-detail', args=[asset.id]), update_payload, format='json')

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Expecting 200 OK
        asset.refresh_from_db()  # Refresh the asset from the database
        self.assertEqual(asset.description, 'Updated Office Chair')

    def test_update_asset_invalid_supplier(self):
        """Test update failure with invalid supplier."""
        asset = Asset.objects.create(**self.valid_instance)
        invalid_payload = self.valid_payload.copy()
        invalid_payload['supplier'] = 'Nonexistent Supplier'

        response = self.client.patch(reverse('asset-detail', args=[asset.pk]), invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('supplier', response.data)
        self.assertEqual(response.data['supplier'][0], "Supplier 'Nonexistent Supplier' does not exist.")

    def test_delete_asset(self):
        """Test deleting an asset."""
        asset = Asset.objects.create(**self.valid_instance)
        response = self.client.delete(reverse('asset-detail', args=[asset.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Asset.objects.count(), 0)

    def test_retrieve_asset(self):
        """Test retrieving an asset."""
        asset = Asset.objects.create(**self.valid_instance)
        response = self.client.get(reverse('asset-detail', args=[asset.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Office Chair')

class ReportGenerationSerializerAPITests(AuthenticatedAPITestCase):
    """Tests that the serializer works as expected"""
    def setUp(self):
        """Set up test variables for all tests."""
        super().setUp()
        self.major_category = MajorCategory.objects.create(name='Furniture')
        self.minor_category = MinorCategory.objects.create(name='Chair', major_category=self.major_category)
        self.location = Location.objects.create(name='Office', use_current_location='True')
        self.department = Department.objects.create(name='HR')
        self.supplier = Supplier.objects.create(name='ABC Supplies')
        self.employee = Employee.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            date_of_birth=date(1995, 1, 1),
            employee_number=2,
            mobile_number="0711111111",
            job_title="Software Engineer",
            address="1234",
            date_hired=date(2021, 1, 1),
            department=self.department
        )

        self.valid_payload = {
            'description': 'Office Chair',
            'major_category': self.major_category,
            'minor_category': self.minor_category,
            'department': self.department,
            'location': self.location,
            'employee': self.employee,
            'supplier': self.supplier,
            'purchase_price': 150.00,
            'units': 10,
            'date_of_purchase': date.today(),
            'date_placed_in_service': date.today(),
            'barcode': '123456789012',
            'asset_type': 'MOVABLE',
            'condition': 'NEW',
            'status': 'ACTIVE'
        }
        asset = Asset.objects.create(**self.valid_payload)
        self.url = '/api/reports/'

    def test_valid_report_generation(self):
        """Test generating a report with valid input."""
        payload = {
            "model_name": "Asset",
            "fields": ["asset_code", "description"],
            "start_date": '2024-01-01',
            "end_date": '2024-10-01',
            "search_text": "Furniture",
            "search_type": "contains",
            "sort_by": "asset_code",
            "sort_order": "asc",
            "report_format": "csv",
        }
        response = self.client.get(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Assuming 200 OK for successful report generation
        # Optionally, check if the response content matches expected output

    def test_invalid_model_name(self):
        """Test report generation with an invalid model_name."""
        payload = {
            "model_name": "invalid_type",  # Invalid report type
            "fields": ["asset_code"],
        }
        response = self.client.get(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expecting bad request due to invalid model_name

    def test_invalid_search_type(self):
        """Test report generation with an invalid search_type."""
        payload = {
            "model_name": "assets",
            "fields": ["asset_code"],
            "search_type": "invalid_search",  # Invalid search type
        }
        response = self.client.get(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expecting bad request due to invalid search_type

    def test_invalid_sort_order(self):
        """Test report generation with an invalid sort_order."""
        payload = {
            "model_name": "assets",
            "fields": ["asset_code"],
            "sort_order": "invalid_order",  # Invalid sort order
        }
        response = self.client.get(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expecting bad request due to invalid sort_order

    def test_date_validation(self):
        """Test report generation with invalid date range."""
        payload = {
            "model_name": "assets",
            "fields": ["asset_code"],
            "start_date": "2024-12-31",
            "end_date": "2024-01-01",  # Start date after end date
        }
        response = self.client.get(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expecting bad request due to invalid date range

    def test_optional_fields(self):
        """Test report generation with optional fields."""
        payload = {
            "model_name": "Asset",
            "fields": ["description", "department"],
            # Testing with optional fields only
        }
        response = self.client.get(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
