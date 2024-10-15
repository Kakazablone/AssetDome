from django.test import TestCase
from rest_framework.test import APITestCase
from assets.models import Department, MajorCategory, Employee, MinorCategory, Asset, Location, Supplier
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta
import logging
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from authentication.models import CustomUser
from rest_framework import status
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

class AuthenticatedAPITestCase(APITestCase):

    def setUp(self):
        """
        Set up initial data for the test cases and log in the user.
        """
        # Create a user
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='zablonsamba@gmail.com',
            password='testing#@123'
        )

        # Log in the user
        login_response = self.client.post(reverse('login-list'), {
            'email': 'zablonsamba@gmail.com',
            'password': 'testing#@123'
        }, format='json')

        # Ensure the login was successful
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Extract the access token from cookies
        access_token = login_response.cookies.get('access_token')

        # If the access token exists, store it in the authorization header
        if access_token:
            self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.value)
        else:
            raise Exception("Login failed or access token not provided.")


class DepartmentAPITestCase(AuthenticatedAPITestCase):

    def setUp(self):
        """Set up a MajorCategory instance for testing."""
        super().setUp()

        # Set up initial Department and Employee data
        self.department = Department.objects.create(
            name="IT",
            department_code="IT001",
            description="Information Technology Department"
        )
        self.manager = Employee.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            date_of_birth=date(1990, 1, 1),
            employee_number=1,
            mobile_number="0700000000",
            job_title="Head of Procurement",
            address="4141",
            date_hired=date(2020, 1, 1),
            department=self.department  # Assign the employee to the department
        )

    def test_create_department(self):
        """
        Test that a department can be created via the API with valid data.
        """
        url = reverse('department-list')  # Assuming you have a DRF view for department creation
        data = {
            'name': 'HR',
            'department_code': 'HR001',
            'description': 'Human Resources Department'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'HR')
        self.assertEqual(response.data['department_code'], 'HR001')

    def test_get_department(self):
        """
        Test that a department can be retrieved via the API.
        """
        url = reverse('department-detail', args=[self.department.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.department.name)
        self.assertEqual(response.data['department_code'], self.department.department_code)

    def test_update_department(self):
        """
        Test that a department can be updated via the API.
        """
        url = reverse('department-detail', args=[self.department.id])
        updated_data = {
            'name': 'IT Updated',
            'department_code': 'IT002',
            'description': 'Updated Information Technology Department'
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'IT Updated')
        self.assertEqual(response.data['department_code'], 'IT002')

    def test_department_unique_name(self):
        """
        Test that the department name must be unique when creating via the API.
        """
        url = reverse('department-list')
        data = {
            'name': 'IT',  # Same name as the department created in setUp
            'department_code': 'IT002',
            'description': 'Duplicate department name'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)  # Check that 'name' field has an error

    def test_department_unique_code(self):
        """
        Test that the department code must be unique when creating via the API.
        """
        url = reverse('department-list')
        data = {
            'name': 'Finance',
            'department_code': 'IT001',  # Same code as the department created in setUp
            'description': 'Duplicate department code'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('department_code', response.data)

    def test_department_can_have_null_manager(self):
        """
        Test that the manager field can be null when creating a department via the API.
        """
        url = reverse('department-list')
        data = {
            'name': 'Marketing',
            'department_code': 'MK001',
            'description': 'Marketing Department',
            'manager': None
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['manager'])

    def test_department_ordering(self):
        """
        Test that departments are returned in the correct order (by name) via the API.
        """
        Department.objects.create(
            name="Finance",
            department_code="FIN001",
            description="Finance department"
        )
        url = reverse('department-list')  # Assuming the list endpoint orders departments by name
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][1]['name'], 'Finance')
        self.assertEqual(response.data['results'][0]['name'], 'IT')

class MajorCategoryAPITestCase(AuthenticatedAPITestCase):

    def setUp(self):
        """Set up a MajorCategory instance for testing."""
        super().setUp()
        self.category = MajorCategory.objects.create(name='Furniture')

    def test_create_major_category(self):
        """Test creating a major category via the API."""
        url = reverse('majorcategory-list')  # Adjust the URL to your endpoint
        data = {'name': 'Electronics'}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MajorCategory.objects.count(), 2)  # One existing + new one
        self.assertEqual(MajorCategory.objects.get(id=response.data['id']).name, 'Electronics')

    def test_unique_name_constraint(self):
        """Test that the name field is unique via the API."""
        url = reverse('majorcategory-list')
        MajorCategory.objects.create(name='Appliances')

        data = {'name': 'Appliances'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)  # Ensure the error is related to the name field

    def test_string_representation(self):
        """Test the string representation of MajorCategory."""
        self.assertEqual(str(self.category), 'Furniture')

    @patch('assets.models.logger')  # Patch the logger in the module where it's used
    def test_save_logging_on_creation(self, mock_logger):
        """Test the logging message when creating a new major category via the API."""
        url = reverse('majorcategory-list')
        data = {'name': 'Appliances'}

        response = self.client.post(url, data, format='json')

        # Check that the logger's info method was called with the expected message
        mock_logger.info.assert_called_with("Creating a new major category: 'Appliances'")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('assets.models.logger')
    def test_save_logging_on_update(self, mock_logger):
        """Test the logging message when updating a major category via the API."""
        url = reverse('majorcategory-detail', args=[self.category.id])  # Adjust the URL to your endpoint
        data = {'name': 'Updated Office Furniture'}

        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the logger's info method was called with the expected message
        mock_logger.info.assert_called_with("Updating major category: 'Updated Office Furniture'")

    def test_delete_major_category(self):
        """Test deleting a major category via the API."""
        url = reverse('majorcategory-detail', args=[self.category.id])  # Adjust the URL to your endpoint
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MajorCategory.objects.filter(id=self.category.id).exists())

class MinorCategoryAPITestCase(AuthenticatedAPITestCase):
    """Test cases for the MinorCategory API."""

    def setUp(self):
        """Set up a major category for testing."""
        super().setUp()  # Call the setup method of the base class
        self.major_category = MajorCategory.objects.create(name='Electronics')

    @patch('assets.models.logger')  # Patch the logger in the module where it's used
    def test_minor_category_creation_logging(self, mock_logger):
        """Test logging when creating a new minor category."""
        response = self.client.post(reverse('minorcategory-list'), {  # Adjust to your URL name
            'name': 'Mobile Phones',
            'major_category': 'Electronics'  # Pass the ID instead of the instance
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # Check if creation is successful

        # Check that the logger's info method was called with the expected message
        mock_logger.info.assert_called_with("Creating a new minor category: 'Mobile Phones' under 'Electronics'")


    @patch('assets.models.logger')
    def test_minor_category_update_logging(self, mock_logger):
        """Test logging when updating a minor category."""
        minor_category = MinorCategory.objects.create(name='Laptops', major_category=self.major_category)

        response = self.client.patch(reverse('minorcategory-detail', kwargs={'pk': minor_category.id}), {  # Adjust to your URL name
            'name': 'Gaming Laptops'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Check if update is successful

        # Check that the logger's info method was called with the expected message
        mock_logger.info.assert_called_with("Updating minor category: 'Gaming Laptops' under 'Electronics'")

    def test_str_method(self):
        """Test the string representation of the MinorCategory."""
        minor_category = MinorCategory(name='Tablets', major_category=self.major_category)
        self.assertEqual(str(minor_category), 'Tablets (Major Category: Electronics)')

    def test_minor_category_relationship(self):
        """Test the relationship between minor category and major category."""
        minor_category = MinorCategory.objects.create(name='Smart TVs', major_category=self.major_category)
        self.assertEqual(minor_category.major_category, self.major_category)

    def test_create_minor_category_without_name(self):
        """Test that creating a minor category without a name fails."""
        response = self.client.post(reverse('minorcategory-list'), {
            'major_category': self.major_category.id
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)  # Check for validation error in response

    def test_create_minor_category_without_major_category(self):
        """Test that creating a minor category without a major category fails."""
        response = self.client.post(reverse('minorcategory-list'), {
            'name': 'New Minor Category'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('major_category', response.data)  # Check for validation error in response

class AssetModelAPITestCase(AuthenticatedAPITestCase):

    def setUp(self):
        """Set up test data."""
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

    def test_create_asset_success(self):
        """Test creating an Asset successfully via API."""
        response = self.client.post('/api/assets/', {
            'barcode': '1234567890',
            'major_category': 'Furniture',
            'minor_category': 'Chair',
            'description': 'Office Chair',
            'asset_type': 'MOVABLE',
            'location': 'Office',
            'department': 'HR',
            'purchase_price': '150.00',
            'date_of_purchase': '2024-01-01',
            'date_placed_in_service': '2024-01-01',
            'condition': 'NEW',
            'status': 'ACTIVE',
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'units': 1,
            'supplier': 'ABC Supplies',
            'employee': 'Jane'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['description'], 'Office Chair')
        self.assertEqual(response.data['units'], 1)
        self.assertEqual(response.data['purchase_price'], '150.00')

    def test_asset_code_auto_generation(self):
        """Test that the asset code is generated automatically via API."""
        response1 = self.client.post('/api/assets/', {
            'barcode': '1234567899',
            'major_category': 'Furniture',
            'minor_category': 'Chair',
            'description': 'Office Chair',
            'asset_type': 'MOVABLE',
            'location': 'Office',
            'department': 'HR',
            'purchase_price': '150.00',
            'date_of_purchase': '2024-01-10',
            'date_placed_in_service': '2024-01-12',
            'condition': 'NEW',
            'status': 'ACTIVE',
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'units': 1,
            'supplier': 'ABC Supplies',
            'employee': 'Jane'
        })

        response2 = self.client.post('/api/assets/', {
            'barcode': '0987654321',
            'major_category': 'Furniture',
            'minor_category': 'Chair',
            'description': 'Desk',
            'asset_type': 'MOVABLE',
            'location': 'Office',
            'department': 'HR',
            'purchase_price': '200.00',
            'date_of_purchase': '2024-01-10',
            'date_placed_in_service': '2024-01-12',
            'condition': 'NEW',
            'status': 'ACTIVE',
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'units': 1,
            'supplier': 'ABC Supplies',
            'employee': 'Jane'
        })

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response1.data['asset_code'], 'AS000001')
        self.assertEqual(response2.data['asset_code'], 'AS000002')

    def test_invalid_purchase_price(self):
        """Test that negative purchase price raises validation error via API."""
        response = self.client.post('/api/assets/', {
            'barcode': '1234567890',
            'major_category': self.major_category.id,
            'minor_category': self.minor_category.id,
            'description': 'Office Chair',
            'asset_type': 'MOVABLE',
            'location': self.location.id,
            'department': self.department.id,
            'purchase_price': '-150.00',
            'date_of_purchase': '2024-01-10',
            'date_placed_in_service': '2024-01-15',
            'condition': 'NEW',
            'status': 'ACTIVE',
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'units': 1,
            'supplier': self.supplier.id,
            'employee': self.employee.id
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('purchase_price', response.data)

    def test_date_of_purchase_in_future(self):
        """Test that date of purchase cannot be in the future via API."""
        future_date = date.today() + timedelta(days=1)
        response = self.client.post('/api/assets/', {
            'barcode': '1234567890',
            'major_category': self.major_category.id,
            'minor_category': self.minor_category.id,
            'description': 'Office Chair',
            'asset_type': 'MOVABLE',
            'location': self.location.id,
            'department': self.department.id,
            'purchase_price': '150.00',
            'date_of_purchase': future_date,
            'date_placed_in_service': '2024-01-12',
            'condition': 'NEW',
            'status': 'ACTIVE',
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'units': 1,
            'supplier': self.supplier.id,
            'employee': self.employee.id
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_purchase', response.data)

    def test_date_placed_in_service_in_future(self):
        """Test that date placed in service cannot be in the future via API."""
        future_date = date.today() + timedelta(days=1)
        response = self.client.post('/api/assets/', {
            'barcode': '1234567890',
            'major_category': self.major_category.id,
            'minor_category': self.minor_category.id,
            'description': 'Office Chair',
            'asset_type': 'MOVABLE',
            'location': self.location.id,
            'department': self.department.id,
            'purchase_price': '150.00',
            'date_of_purchase': '2024-01-10',
            'date_placed_in_service': future_date,
            'condition': 'NEW',
            'status': 'ACTIVE',
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'units': 1,
            'supplier': self.supplier.id,
            'employee': self.employee.id
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_placed_in_service', response.data)

    def test_economic_life_based_on_major_category(self):
        """Test that economic life is set based on major category via API."""
        response_furniture = self.client.post('/api/assets/', {
            'barcode': '1234567790',
            'major_category': 'Furniture',
            'minor_category': 'Chair',
            'description': 'Office Chair',
            'asset_type': 'MOVABLE',
            'location': 'Office',
            'department': 'HR',
            'purchase_price': '150.00',
            'date_of_purchase': '2024-01-10',
            'date_placed_in_service': '2024-01-15',
            'condition': 'NEW',
            'status': 'ACTIVE',
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'units': 1,
            'supplier': 'ABC Supplies',
            'employee': 'Jane'
        })

        self.assertEqual(response_furniture.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_furniture.data['economic_life'], 8)

        self.major_category = MajorCategory.objects.create(name='ICT')
        self.minor_category = MinorCategory.objects.create(name='Laptop', major_category=self.major_category)
        response_ict = self.client.post('/api/assets/', {
            'barcode': '1234567789',
            'major_category': 'ICT',
            'minor_category': 'Laptop',
            'description': 'Dell Laptop',
            'asset_type': 'MOVABLE',
            'location': 'Office',
            'department': 'HR',
            'purchase_price': '1500.00',
            'date_of_purchase': '2024-01-10',
            'date_placed_in_service': '2024-01-15',
            'condition': 'NEW',
            'status': 'ACTIVE',
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'units': 1,
            'supplier': 'ABC Supplies',
            'employee': 'Jane'
        })

        self.assertEqual(response_ict.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_ict.data['economic_life'], 3)

    def test_asset_deletion(self):
        """Test asset deletion via API."""
        asset = Asset.objects.create(
            barcode='1234567890',
            major_category=self.major_category,
            minor_category=self.minor_category,
            description='Office Chair',
            asset_type='MOVABLE',
            location=self.location,
            department=self.department,
            purchase_price=Decimal('150.00'),
            date_of_purchase=date(2024, 1, 10),
            date_placed_in_service=date(2024 ,1, 15),
            condition='NEW',
            status='ACTIVE',
            created_by=self.user,
            updated_by=self.user,
            units=1,
            supplier=self.supplier,
            employee=self.employee
        )
        response = self.client.delete(f'/api/assets/{asset.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Asset.objects.filter(id=asset.id).exists())

    def test_asset_retrieval(self):
        """Test retrieving an asset via API."""
        asset = Asset.objects.create(
            barcode='1234567890',
            major_category=self.major_category,
            minor_category=self.minor_category,
            description='Office Chair',
            asset_type='MOVABLE',
            location=self.location,
            department=self.department,
            purchase_price=Decimal('150.00'),
            date_of_purchase=date(2024, 1, 10),
            date_placed_in_service=date(2024, 1, 15),
            condition='NEW',
            status='ACTIVE',
            created_by=self.user,
            updated_by=self.user,
            units=1,
            supplier=self.supplier,
            employee=self.employee
        )
        response = self.client.get(f'/api/assets/{asset.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Office Chair')

    def test_update_asset(self):
        """Test updating an asset via API."""
        asset = Asset.objects.create(
            barcode='1234567890',
            major_category=self.major_category,
            minor_category=self.minor_category,
            description='Office Chair',
            asset_type='MOVABLE',
            location=self.location,
            department=self.department,
            purchase_price=Decimal('150.00'),
            date_of_purchase=date(2024, 1, 10),
            date_placed_in_service=date(2024, 1, 15),
            condition='NEW',
            status='ACTIVE',
            created_by=self.user,
            updated_by=self.user,
            units=1,
            supplier=self.supplier,
            employee=self.employee
        )
        response = self.client.patch(f'/api/assets/{asset.id}/', {
            'description': 'Updated Office Chair',
            'purchase_price': '200.00'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        asset.refresh_from_db()
        self.assertEqual(asset.description, 'Updated Office Chair')
        self.assertEqual(asset.purchase_price, Decimal('200.00'))

class SupplierAPITestCase(AuthenticatedAPITestCase):
    def setUp(self):
        """Set up initial data for the test cases."""
        super().setUp()
        self.valid_supplier_data = {
            "name": "Test Supplier",
            "supplier_code": "TS001",
            "contact_person": "Jane Doe",
            "phone_number": "0700000000",
            "email": "jane.doe@example.com",
            "address": "1234 Test St, Test City, TC 12345",
            "website": "https://example.com",
        }
        self.create_url = "/api/suppliers/"
        self.supplier = Supplier.objects.create(**self.valid_supplier_data)

    def test_supplier_creation(self):
        """Test creating a supplier via API."""
        supplier_data = {
            "name": "Test Supplier New",
            "supplier_code": "TS011",
            "contact_person": "Jane Doe",
            "phone_number": "0700000000",
            "email": "jadoe@example.com",
            "address": "1234 Test St, Test City, TC 12345",
            "website": "https://example.com",
        }
        response = self.client.post(self.create_url, supplier_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], supplier_data["name"])
        self.assertEqual(response.data["supplier_code"], supplier_data["supplier_code"])

    def test_unique_supplier_code(self):
        """Test that the supplier_code must be unique via API."""
        self.client.post(self.create_url, self.valid_supplier_data)
        duplicate_data = self.valid_supplier_data.copy()
        duplicate_data["supplier_code"] = "TS001"  # Duplicate supplier code

        response = self.client.post(self.create_url, duplicate_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('supplier_code', response.data)

    def test_str_method(self):
        """Test the string representation of the supplier."""
        self.assertEqual(str(self.supplier), self.valid_supplier_data["name"])

    def test_email_validation(self):
        """Test that an invalid email raises a ValidationError via API."""
        invalid_email_data = self.valid_supplier_data.copy()
        invalid_email_data["email"] = "invalid-email"
        response = self.client.post(self.create_url, invalid_email_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_phone_number_length(self):
        """Test that the phone_number does not exceed maximum length via API."""
        invalid_phone_data = self.valid_supplier_data.copy()
        invalid_phone_data["phone_number"] = "1" * 21  # 21 characters
        response = self.client.post(self.create_url, invalid_phone_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

    def test_website_field(self):
        """Test that a valid URL is accepted in the website field via API."""
        valid_url_data = {
            "name": "Test Supplier Best",
            "supplier_code": "TS123",
            "contact_person": "Jane Doe",
            "phone_number": "0700000000",
            "email": "doe@example.com",
            "address": "1234 Test St, Test City, TC 12345",
            "website": "https://example.com",
        }
        response = self.client.post(self.create_url, valid_url_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        invalid_url_data = {
            "name": "Test Supplier Invalid",
            "supplier_code": "TS041",
            "contact_person": "Jane Doe",
            "phone_number": "0700000000",
            "email": "doest@example.com",
            "address": "1234 Test St, Test City, TC 12345",
            "website": "invalid url",
        }
        response = self.client.post(self.create_url, invalid_url_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('website', response.data)

    def test_required_fields(self):
        """Test that required fields cannot be blank via API."""
        required_fields = ["name", "supplier_code", "contact_person", "phone_number", "email", "address"]
        for field in required_fields:
            invalid_data = self.valid_supplier_data.copy()
            invalid_data[field] = ""  # Set the required field to an empty string
            response = self.client.post(self.create_url, invalid_data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn(field, response.data)

    def test_special_characters_in_name(self):
        """Test that special characters are accepted in the name and contact_person fields via API."""
        valid_data = self.valid_supplier_data.copy()
        valid_data["name"] = "Supplier & Co."
        valid_data["contact_person"] = "John O'Connor"
        valid_data["supplier_code"] = 'SUP002'
        valid_data["email"] = 'johnsup@gmail.com'
        response = self.client.post(self.create_url, valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_long_input(self):
        """Test that overly long inputs raise a ValidationError via API."""
        long_name = "A" * 256  # Assuming max length for name is 255
        long_name_supplier = {
            "name": long_name,
            "supplier_code": "TS009",
            "contact_person": "Jane Doe",
            "phone_number": "0700000000",
            "email": "janedo@example.com",
            "address": "1234 Test St, Test City, TC 12345",
            "website": "https://example.com",
        }
        response = self.client.post(self.create_url, long_name_supplier)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    @patch('assets.models.logger')
    def test_save_method_logging(self, mock_logger):
        """Test that the save method logs supplier information via API."""
        new_supplier = {
            "name": "Test Supplier B",
            "supplier_code": "TS007",
            "contact_person": "James Dord",
            "phone_number": "0700000000",
            "email": "jaymo.dord@example.com",
            "address": "1234 Test St, Test City, TC 12345",
            "website": "https://example.com",
        }
        response = self.client.post(self.create_url, new_supplier)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_logger.info.assert_called_once_with("Supplier saved: Test Supplier B with code: TS007")

    def test_bulk_creation(self):
        """Test creating multiple suppliers via API."""
        suppliers = [
            {
                "name": "Supplier A",
                "supplier_code": "SA001",
                "contact_person": "Alice",
                "phone_number": "0700000001",
                "email": "alice@example.com",
                "address": "1234 Supplier A St, City A",
            },
            {
                "name": "Supplier B",
                "supplier_code": "SB001",
                "contact_person": "Bob",
                "phone_number": "0700000002",
                "email": "bob@example.com",
                "address": "5678 Supplier B St, City B",
            },
        ]
        for supplier_data in suppliers:
            response = self.client.post(self.create_url, supplier_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_deletion(self):
        """Test that a supplier can be deleted via API."""
        response = self.client.delete(f"{self.create_url}{self.supplier.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(f"{self.create_url}{self.supplier.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_blank_fields(self):
        """Test that optional fields can be blank via API without raising ValidationError."""
        with_blank = {
            "name": "Test Supplier Co.",
            "supplier_code": "TS005",
            "contact_person": "Jason Ouma",
            "phone_number": "0700000000",
            "email": "jason.doe@example.com",
            "address": "1234 Test St, Test City, TC 12345",
            "website": "",
        }
        response = self.client.post(self.create_url, with_blank)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_email_uniqueness(self):
        """Test that email addresses must be unique across suppliers via API."""
        self.client.post(self.create_url, self.valid_supplier_data)
        duplicate_supplier_data = {
            "name": "Duplicate Supplier",
            "supplier_code": "DS002",
            "contact_person": "Jane Smith",
            "phone_number": "0700000003",
            "email": self.valid_supplier_data["email"],  # Same email
            "address": "9999 Duplicate St, City D",
        }
        response = self.client.post(self.create_url, duplicate_supplier_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

class EmployeeAPITestCase(AuthenticatedAPITestCase):

    def setUp(self):
        """Set up test data for the Employee model."""
        super().setUp()
        self.department = Department.objects.create(name='HR', department_code='HR001')
        self.create_url = '/api/employees/'  # Replace with your actual URL
        self.valid_employee_data = {
            'first_name': 'John',
            'middle_name': 'A.',
            'last_name': 'Doe',
            'employee_number': 'EMP001',
            'email': 'john.doe@example.com',
            'mobile_number': '0700000000',
            'job_title': 'HR Manager',
            'date_of_birth': date(1990, 1, 1).isoformat(),  # Use ISO format for the date
            'date_hired': date(2020, 1, 1).isoformat(),
            'address': '123 Main St, City, Country',
            'department': self.department,  # Use department ID
        }

    def test_empty_first_name(self):
        """Test that first name cannot be empty."""
        data = self.valid_employee_data.copy()
        data['first_name'] = ''
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_last_name(self):
        """Test that last name cannot be empty."""
        data = self.valid_employee_data.copy()
        data['last_name'] = ''
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_employee_number(self):
        """Test that employee number cannot be empty."""
        data = self.valid_employee_data.copy()
        data['employee_number'] = ''
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_email(self):
        """Test that email cannot be empty."""
        data = self.valid_employee_data.copy()
        data['email'] = ''
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email_format(self):
        """Test that invalid email format raises a ValidationError."""
        data = self.valid_employee_data.copy()
        data['email'] = 'invalid-email'  # Invalid format
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_mobile_number(self):
        """Test that mobile number cannot be empty."""
        data = self.valid_employee_data.copy()
        data['mobile_number'] = ''
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_job_title(self):
        """Test that job title cannot be empty."""
        data = self.valid_employee_data.copy()
        data['job_title'] = ''
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_department(self):
        """Test that department cannot be empty."""
        data = self.valid_employee_data.copy()
        data.pop('department')  # Remove the department key entirely
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_minimum_age_at_hiring(self):
        """Test that an employee must be at least 18 years old at the time of hiring."""
        # Set date_of_birth to make the employee 17 years old
        data = {
            'first_name': 'James',
            'middle_name': 'A.',
            'last_name': 'Karani',
            'employee_number': 'EMP003',
            'email': 'jamess@example.com',
            'mobile_number': '0700000000',
            'job_title': 'HR Manager',
            'date_of_birth': (date.today() - relativedelta(years=17)).isoformat(),  # 17 years old
            'date_hired': date.today().isoformat(),
            'address': '123 Main St, City, Country',
            'department': self.department,  # Use department ID
        }
        response = self.client.post(self.create_url, data)

        # Expect a 400 BAD REQUEST because the employee is too young
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_hiring_age_valid(self):
        """Test that an employee can be hired if they are at least 18 years old."""
        # Employee exactly 18 years old
        data = {
            'first_name': 'Adipo',
            'middle_name': 'A.',
            'last_name': 'Kuome',
            'employee_number': 'EMP030',
            'email': 'adipo@example.com',
            'mobile_number': '0700000000',
            'job_title': 'HR Manager',
            'date_of_birth': (date.today() - relativedelta(years=18)).isoformat(),  # Use ISO format for the date
            'date_hired': date.today().isoformat(),
            'address': '123 Main St, City, Country',
            'department': self.department,  # Use department ID
        }
        response = self.client.post(self.create_url, data)
        # Expect a 201 CREATED because the employee is old enough
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_employee_minimum_age_invalid(self):
        """Test that an employee cannot be hired if they are under 18 years old."""
        # Set date_of_birth to make the employee 17 years old at the time of hiring
        data = {
            'first_name': 'Maureen',
            'middle_name': 'A.',
            'last_name': 'Chepr',
            'employee_number': 'EMP006',
            'email': 'chepr@example.com',
            'mobile_number': '0700000000',
            'job_title': 'HR Manager',
            'date_of_birth': (date.today() - timedelta(days=17*365)).isoformat(),  # Use ISO format for the date
            'date_hired': date.today().isoformat(),
            'address': '123 Main St, City, Country',
            'department': self.department,  # Use department ID
        }
        response = self.client.post(self.create_url, data)

        # Expect a 400 BAD REQUEST because the employee is not old enough
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_hired_today(self):
        """Test that today's date can be set for date hired."""
        data = self.valid_employee_data.copy()
        data['date_hired'] = date.today().isoformat()  # Set to today
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_multiple_employees(self):
        """Test that multiple employees can be created without conflicts."""
        employee_data_1 = self.valid_employee_data.copy()
        Employee.objects.create(**employee_data_1)  # Pre-create one employee
        employee_data_2 = self.valid_employee_data.copy()
        employee_data_2['employee_number'] = 'EMP002'
        employee_data_2['email'] = 'john2.doe@example.com'  # Different email
        response = self.client.post(self.create_url, employee_data_2)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Employee.objects.count(), 2)

class LocationAPITestCase(AuthenticatedAPITestCase):

    def setUp(self):
        """Set up valid location data for testing."""
        super().setUp()
        """Set up valid location data for testing."""
        self.valid_location_data = {
            'name': 'Central Park',
            'use_current_location': False  # Assume default; no latitude/longitude input
        }

        self.invalid_location_data = {
            'name': 'Invalid Location',
            'use_current_location': False
        }

        self.create_url = '/api/locations/'  # Adjust this based on your API endpoint

    @patch('assets.models.Nominatim.geocode')
    def test_create_location_success(self, mock_geocode):
        """Test that a location can be created successfully, fetching coordinates automatically."""
        mock_geocode.return_value.latitude = 40.785091
        mock_geocode.return_value.longitude = -73.968285

        response = self.client.post(self.create_url, self.valid_location_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], self.valid_location_data['name'])
        self.assertEqual(response.data['latitude'], 40.785091)
        self.assertEqual(response.data['longitude'], -73.968285)
        logger.info(f"Location created: {response.data['name']} with coordinates: ({response.data['latitude']}, {response.data['longitude']})")

    def test_create_location_no_coordinates_found(self):
        """Test that creating a location fails when geolocation service does not find coordinates."""
        with patch('assets.models.Nominatim.geocode') as mock_geocode:
            mock_geocode.return_value = None  # Simulate no result from geolocation service

            response = self.client.post(self.create_url, self.valid_location_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)  # Assuming the response contains an error field

    def test_unique_name_constraint(self):
        """Test that creating a location with a duplicate name raises a ValidationError."""
        Location.objects.create(name='Unique Location')

        duplicate_data = {
            'name': 'Unique Location',
            'use_current_location': False
        }
        response = self.client.post(self.create_url, duplicate_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)  # Assuming the response contains error messages

    def test_empty_location_name(self):
        """Test that an empty location name raises a ValidationError."""
        location_data = {
            'name': '',
            'use_current_location': False
        }
        response = self.client.post(self.create_url, location_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)  # Assuming the response contains error messages

    def test_long_name_exceeds_max_length(self):
        """Test that a location name exceeding max length raises a ValidationError."""
        long_name = 'A' * 101  # 101 characters long
        location_data = {
            'name': long_name,
            'use_current_location': False
        }
        response = self.client.post(self.create_url, location_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)  # Assuming the response contains error messages

    @patch('assets.models.Nominatim.geocode')
    def test_geolocator_error_handling(self, mock_geocode):
        """Test that an error in the geolocator is handled gracefully."""
        location_data = {
            'name': 'Test Location',
            'use_current_location': False
        }

        mock_geocode.side_effect = Exception("Geolocation service error. Please check the service availability.")

        response = self.client.post(self.create_url, location_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)  # Assuming the response contains an error field

    def test_both_coordinates_and_current_location(self):
        """Test behavior when both coordinates and current location flag are provided."""
        location_data = {
            'name': 'Ambiguous Location',
            'use_current_location': True  # Only using current location; no lat/long
        }
        response = self.client.post(self.create_url, location_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Assuming that the geolocation service is called to fetch the coordinates
        self.assertIn('latitude', response.data)
        self.assertIn('longitude', response.data)
