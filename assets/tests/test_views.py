from rest_framework import status
from rest_framework.test import APITestCase
from assets.models import Asset, MajorCategory, MinorCategory, Location, Department, Supplier, Employee
from assets.serializers import MajorCategorySerializer
from authentication.models import CustomUser  
from unittest.mock import patch
from django.urls import reverse
from django.utils import timezone
from datetime import date
from datetime import timedelta


class AssetViewSetTests(APITestCase):

    @patch('geopy.geocoders.Nominatim.geocode')
    def setUp(self, mock_geocode):
        mock_geocode.return_value = None  # Mock response if needed

        # Create necessary instances for tests
        self.user = CustomUser.objects.create_user(
            username='testuser', 
            email='zablonsamba@gmail.com',
            password='testing#@123'
        )
        self.major_category = MajorCategory.objects.create(name='Furniture')
        self.minor_category = MinorCategory.objects.create(name='Chair', major_category=self.major_category)
        self.location = Location.objects.create(name='Warehouse', use_current_location='True')
        self.department = Department.objects.create(name='Sales')
        self.supplier = Supplier.objects.create(name='Supplier A')
        self.employee = Employee.objects.create(
            first_name='Test Employee',
            last_name='Okbwang',
            date_of_birth='1991-01-20',
            date_hired='2000-01-01',
            department=self.department
        )

        self.asset_data = {
            'barcode': 'BARCODE12345',
            'rfid': None,
            'major_category': self.major_category.name,
            'minor_category': self.minor_category.name,
            'description': 'A nice office chair',
            'serial_number': 'SN123456',
            'model_number': 'MODEL123',
            'asset_type': 'MOVABLE',
            'location': self.location.name,
            'department': self.department.name,
            'employee': self.employee.first_name,
            'supplier': self.supplier.name,
            'economic_life': 8,
            'purchase_price': 150.00,
            'net_book_value': 0.00,
            'units': 1,
            'date_of_purchase': date(2024, 9, 30),
            'date_placed_in_service': date(2024, 10, 1),
            'condition': 'NEW',
            'status': 'ACTIVE',
            'depreciation_method': 'STRAIGHT_LINE',
        }

        # Login the user before tests
        login_response = self.client.post(reverse('login-list'), {
            'email': 'zablonsamba@gmail.com',
            'password': 'testing#@123'
        }, format='json')
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_create_asset(self):
        """Test asset creation with valid data."""
        response = self.client.post(reverse('asset-list'), self.asset_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Asset.objects.count(), 1)
        asset = Asset.objects.get()
        self.assertEqual(asset.asset_code, 'AS000001')  # Check generated asset code
        self.assertEqual(asset.major_category.name, 'Furniture')  # Validate major category
        self.assertEqual(asset.created_by, self.user)  # Check who created the asset

    def test_invalid_major_category(self):
        """Test asset creation with an invalid major category."""
        invalid_data = self.asset_data.copy()
        invalid_data['major_category'] = 'Invalid Category'  # Non-existent category
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Major category 'Invalid Category' does not exist.", str(response.data))

    def test_barcode_uniqueness(self):
        """Test that the barcode must be unique for each asset."""
        # Create the first asset with a barcode
        self.client.post(reverse('asset-list'), self.asset_data, format='json')
        
        # Attempt to create another asset with the same barcode
        response = self.client.post(reverse('asset-list'), self.asset_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('asset with this barcode already exists.', str(response.data['barcode'][0]))

    def test_retrieve_asset(self):
        """Test retrieving an existing asset by ID."""
        # Create the asset using the self.asset_data defined in setUp
        asset = Asset.objects.create(
            barcode=self.asset_data['barcode'],
            rfid=self.asset_data['rfid'],
            major_category=self.major_category,
            minor_category=self.minor_category,
            description=self.asset_data['description'],
            serial_number=self.asset_data['serial_number'],
            model_number=self.asset_data['model_number'],
            asset_type=self.asset_data['asset_type'],
            location=self.location,
            department=self.department,
            employee=self.employee,
            supplier=self.supplier,
            economic_life=self.asset_data['economic_life'],
            purchase_price=self.asset_data['purchase_price'],
            net_book_value=self.asset_data['net_book_value'],
            units=self.asset_data['units'],
            date_of_purchase=self.asset_data['date_of_purchase'],
            date_placed_in_service=self.asset_data['date_placed_in_service'],
            condition=self.asset_data['condition'],
            status=self.asset_data['status'],
            depreciation_method=self.asset_data['depreciation_method'],
            created_by=self.user,
            updated_by=self.user
        )

        # Retrieve the asset by ID
        response = self.client.get(reverse('asset-detail', args=[asset.id]))
        
        # Check the response status and data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], asset.id)
        self.assertEqual(response.data['serial_number'], 'SN123456')
        self.assertEqual(response.data['major_category'], 'Furniture')
        self.assertEqual(response.data['minor_category'], 'Chair')
        self.assertEqual(response.data['employee'], 'Test Employee')
        self.assertEqual(response.data['supplier'], 'Supplier A')

    def test_create_asset_with_invalid_condition(self):
        """Test asset creation with an invalid condition."""
        invalid_data = self.asset_data.copy()
        invalid_data['condition'] = 'SPOILT'  # Set an invalid condition
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('"SPOILT" is not a valid choice.', str(response.data['condition']))

    def test_create_asset_with_negative_purchase_price(self):
        """Test asset creation with a negative purchase price."""
        invalid_data = self.asset_data.copy()
        invalid_data['purchase_price'] = -150.00  # Set negative purchase price
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Purchase price cannot be negative.', str(response.data['purchase_price']))

    def test_create_asset_with_empty_description(self):
        """Test asset creation with an empty description."""
        invalid_data = self.asset_data.copy()
        invalid_data['description'] = ''  # Set empty description
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This field may not be blank.', str(response.data['description']))

    def test_create_asset_with_zero_units(self):
        """Test creating an asset with zero units."""
        invalid_asset_data = {
            "serial_number": "SN12345",
            "major_category": self.major_category.id,
            "minor_category": self.minor_category.id,
            "units": 0,  # Invalid because we want positive units
            # Other required fields...
        }
        response = self.client.post(reverse('asset-list'), data=invalid_asset_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expecting a bad request

    def test_update_asset(self):
        """Test updating an existing asset."""
        # Create the asset using the correct instances for related fields
        asset = Asset.objects.create(
            barcode='BARCODE12345',
            rfid=None,
            major_category=self.major_category,  # Use the MajorCategory instance
            minor_category=self.minor_category,  # Use the MinorCategory instance
            description='A nice office chair',
            serial_number='SN123456',
            model_number='MODEL123',
            asset_type='MOVABLE',
            location=self.location,  # Use the Location instance
            department=self.department,  # Use the Department instance
            employee=self.employee,  # Use the Employee instance
            supplier=self.supplier,  # Use the Supplier instance
            economic_life=8,
            purchase_price=150.00,
            net_book_value=0.00,
            units=1,
            date_of_purchase=date(2024, 9, 30),
            date_placed_in_service=date(2024, 10, 1),
            condition='NEW',  # Use a valid condition
            status='ACTIVE',
            depreciation_method='STRAIGHT_LINE',
            created_by=self.user,  # Use the CustomUser instance
            updated_by=self.user,  # Use the CustomUser instance
        )

        # Prepare updated data with correct instances for the update
        updated_data = {
            'barcode': 'BARCODE54321',
            'serial_number': 'SN54321',
            'rfid': None,
            'major_category': 'Furniture',  # Pass the ID for major category
            'minor_category': 'Chair',  # Pass the ID for minor category
            'description': 'Updated office chair',
            'model_number': 'MODEL543',
            'asset_type': 'MOVABLE',
            'location': 'Warehouse',  # Pass the ID for location
            'department': 'Sales',  # Pass the ID for department
            'employee': 'Test Employee',  # Pass the ID for employee
            'supplier': 'Supplier A',  # Pass the ID for supplier
            'economic_life': 10,
            'purchase_price': 200.00,
            'net_book_value': 50.00,
            'units': 2,
            'date_of_purchase': date(2023, 9, 30),
            'date_placed_in_service': date(2023, 1, 10),
            'condition': 'NEW',  # Use a valid condition
            'status': 'ACTIVE',
            'depreciation_method': 'STRAIGHT_LINE',
            'created_by': self.user.id,  # Use the user ID
            'updated_by': self.user.id,  # Use the user ID
        }

        # Send the PUT request to update the asset
        response = self.client.put(reverse('asset-detail', args=[asset.id]), data=updated_data, format='json')

        # Print response content to see why it's failing
        if response.status_code != status.HTTP_200_OK:
            print(response.data)  # Print the response error

        # Check the status code for a successful update
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that the asset was updated with the correct data
        asset.refresh_from_db()  # Refresh from database to get the latest state
        self.assertEqual(asset.serial_number, 'SN54321')
        self.assertEqual(asset.units, 2)
        self.assertEqual(asset.date_of_purchase, date(2023, 9, 30))
        self.assertEqual(asset.date_placed_in_service.strftime('%Y-%m-%d'), '2023-01-10')
        self.assertEqual(asset.description, 'Updated office chair')
        self.assertEqual(asset.purchase_price, 200.00)

    def test_delete_asset(self):
        """Test deleting an existing asset."""
        asset_data = {
            'serial_number': 'SN12345',
            'major_category': self.major_category,
            'minor_category': self.minor_category,
            'units': 5,
            'date_placed_in_service': date(2023, 1, 1),
            'created_by': self.user,
            'updated_by': self.user,
            'date_of_purchase': date(2022, 12, 30),
            'department': self.department,
            'employee': self.employee,
            'supplier': self.supplier,
            'economic_life': 8,
            'purchase_price': 150.00,
            'net_book_value': 0.00,
            'units': 1,
            'condition': 'NEW',
            'status': 'ACTIVE',
            'depreciation_method': 'STRAIGHT_LINE',
            'location': self.location
        }

        asset = Asset.objects.create(**asset_data)

        response = self.client.delete(reverse('asset-detail', args=[asset.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_asset_with_missing_fields(self):
        """Test asset creation with missing required fields."""
        invalid_data = self.asset_data.copy()
        invalid_data.pop('barcode')  # Remove the required barcode
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This field is required.', str(response.data['barcode']))

    def test_create_asset_with_invalid_asset_type(self):
        """Test asset creation with an invalid asset type."""
        invalid_data = self.asset_data.copy()
        invalid_data['asset_type'] = 'INVALID_TYPE'  # Set invalid asset type
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('"INVALID_TYPE" is not a valid choice.', str(response.data['asset_type']))

    def test_create_asset_with_non_existent_employee(self):
        """Test asset creation with a non-existent employee."""
        invalid_data = self.asset_data.copy()
        invalid_data['employee'] = 'Non Existent Employee'  # Set to non-existent employee
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Employee 'Non Existent Employee' does not exist.", str(response.data['employee']))

    def test_create_asset_with_invalid_supplier(self):
        """Test asset creation with an invalid supplier."""
        invalid_data = self.asset_data.copy()
        invalid_data['supplier'] = 'Non Existent Supplier'  # Set to non-existent supplier
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Supplier 'Non Existent Supplier' does not exist.", str(response.data['supplier']))

    def test_create_asset_with_future_date_of_purchase(self):
        """Test asset creation with a future date of purchase."""
        invalid_data = self.asset_data.copy()
        
        # Set the date of purchase to tomorrow
        invalid_data['date_of_purchase'] = timezone.now().date() + timedelta(days=1)  
        
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')

        # Check that the response status is 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check for the field in the response
        self.assertIn('date_of_purchase', response.data)
        
        # Check for the specific validation error message
        self.assertIn('Date of purchase cannot be in the future.', str(response.data['date_of_purchase'][0]))

    def test_create_asset_with_future_date_placed_in_service(self):
        """Test asset creation with a future date for 'date_placed_in_service'."""
        invalid_data = self.asset_data.copy()
        # Set date placed in service to tomorrow
        invalid_data['date_placed_in_service'] = (timezone.now() + timezone.timedelta(days=1)).date()  
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Date placed in service cannot be in the future.', str(response.data))

    def test_create_asset_with_large_input_size(self):
        """Test asset creation with very large input sizes."""
        large_description = 'A' * 1000  # 1000 characters
        invalid_data = self.asset_data.copy()
        invalid_data['description'] = large_description  # Set a very large description
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # Should still succeed

    def test_create_asset_with_special_characters(self):
        """Test asset creation with special characters in fields."""
        special_description = 'A nice chair @ $150.00!'
        invalid_data = self.asset_data.copy()
        invalid_data['description'] = special_description  # Include special characters
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # Should still succeed

    # def test_create_asset_with_historical_date(self):
    #     """Test asset creation with an excessively old date."""
    #     invalid_data = self.asset_data.copy()
    #     invalid_data['date_of_purchase'] = 1800  # Set an excessively old date of purchase
    #     response = self.client.post(reverse('asset-list'), invalid_data, format='json')
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertIn('date of purchase cannot be earlier than the current date.', str(response.data['date_of_purchase']))

    def test_create_asset_with_empty_optional_fields(self):
        """Test asset creation with optional fields being empty."""
        invalid_data = self.asset_data.copy()
        invalid_data['rfid'] = None  # Set optional field to None
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # Should succeed

    def test_create_asset_with_high_purchase_price(self):
        """Test asset creation with a very high purchase price."""
        invalid_data = self.asset_data.copy()
        invalid_data['purchase_price'] = 1_000_000.00  # High purchase price
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # Should still succeed

    def test_update_asset_with_invalid_data(self):
        """Test updating an asset with invalid data."""
        
        # Create the asset with valid data using the setup's asset_data
        asset = Asset.objects.create(
            barcode=self.asset_data['barcode'],
            rfid=self.asset_data['rfid'],
            major_category=self.major_category,
            minor_category=self.minor_category,
            description=self.asset_data['description'],
            serial_number=self.asset_data['serial_number'],  # This can be empty
            model_number=self.asset_data['model_number'],
            asset_type=self.asset_data['asset_type'],
            location=self.location,
            department=self.department,
            employee=self.employee,
            supplier=self.supplier,
            economic_life=self.asset_data['economic_life'],
            purchase_price=self.asset_data['purchase_price'],
            net_book_value=self.asset_data['net_book_value'],
            units=self.asset_data['units'],
            date_of_purchase=self.asset_data['date_of_purchase'],
            date_placed_in_service=self.asset_data['date_placed_in_service'],
            condition=self.asset_data['condition'],
            status=self.asset_data['status'],
            depreciation_method=self.asset_data['depreciation_method'],
            created_by=self.user,
            updated_by=self.user
        )
        
        # Prepare invalid data (excluding serial_number since it's optional)
        invalid_data = {
            'units': -1,  # Invalid units (negative value)
            'minor_category': 'InvalidCategory',  # Should be a valid minor_category ID or name
            'date_placed_in_service': date(2023, 1, 1),  # Valid date, but logic can cause a mismatch if earlier than purchase date
            'date_of_purchase': date(2022, 12, 30),
            'created_by': self.user.id,
            'updated_by': self.user.id,
            'major_category': 'InvalidCategory'  # Should be a valid major_category ID or name
        }

        # Perform the update request with invalid data
        response = self.client.put(reverse('asset-detail', args=[asset.id]), data=invalid_data)

        # Assert that the response is a bad request (HTTP 400) due to invalid data
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Optionally, check for the specific error messages for each invalid field
        self.assertIn('units', response.data)  # Ensure error due to invalid units
        self.assertIn('major_category', response.data)  # Ensure error due to invalid major category
        self.assertIn('minor_category', response.data)  # Ensure error due to invalid minor category


    def test_create_asset_with_same_serial_number_in_different_categories(self):
        """Test creating assets with the same serial number in different categories."""

        # First asset with serial number 'SN12345' in the 'Furniture' category
        asset_data_1 = self.asset_data.copy()
        asset_data_1['serial_number'] = 'SN12345'  # Same serial number
        asset_data_1['major_category'] = self.major_category.name  # 'Furniture'
        asset_data_1['minor_category'] = self.minor_category.name  # 'Chair'
        asset_data_1['barcode'] = 'BARCODE12345'  # Unique barcode for the first asset

        response_1 = self.client.post(reverse('asset-list'), data=asset_data_1, format='json')
        # print(response_1.data)
        self.assertEqual(response_1.status_code, status.HTTP_201_CREATED)  # Should succeed

        # Create a new major and minor category for the second asset
        major_category_2 = MajorCategory.objects.create(name='Electronics')
        minor_category_2 = MinorCategory.objects.create(name='Laptop', major_category=major_category_2)

        # Second asset with the same serial number 'SN12345' but in the 'Electronics' category
        asset_data_2 = self.asset_data.copy()
        asset_data_2['serial_number'] = 'SN12345'  # Same serial number
        asset_data_2['major_category'] = major_category_2.name  # 'Electronics'
        asset_data_2['minor_category'] = minor_category_2.name  # 'Laptop'
        asset_data_2['barcode'] = 'BARCODE67890'  # Different barcode for the second asset

        response_2 = self.client.post(reverse('asset-list'), data=asset_data_2, format='json')
        # print(response_2.data)
        self.assertEqual(response_2.status_code, status.HTTP_201_CREATED) 

    def test_create_asset_with_non_standard_currency_format(self):
        """Test asset creation with non-standard currency format."""
        invalid_data = self.asset_data.copy()
        invalid_data['purchase_price'] = '1,000.00'  # Non-standard format (comma separated)
        response = self.client.post(reverse('asset-list'), invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('A valid number is required.', str(response.data['purchase_price']))

    def test_retrieve_asset_with_invalid_id(self):
        """Test asset retrieval with a non-existent ID."""
        # Use a non-existent ID
        response = self.client.get(reverse('asset-detail', args=[99999]))  # Use an ID that you know does not exist
        
        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check that the response detail matches what you expect
        self.assertEqual(response.data['detail'].code, 'not_found')
        self.assertIn('No Asset matches the given query.', str(response.data['detail']))

class MajorCategoryViewSetTests(APITestCase):
    """
    Test suite for MajorCategoryViewSet.
    """

    def setUp(self):
        """
        Set up the test environment by creating a MajorCategory instance.
        """
        self.user = CustomUser.objects.create_user(
            username='testuser', 
            email='zablonsamba@gmail.com',
            password='testing#@123'
        )
        self.category1 = MajorCategory.objects.create(name="Furniture")
        self.category2 = MajorCategory.objects.create(name="ICT")
        self.url = reverse('majorcategory-list')

        # Login the user before tests
        login_response = self.client.post(reverse('login-list'), {
            'email': 'zablonsamba@gmail.com',
            'password': 'testing#@123'
        }, format='json')
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)


    def test_create_major_category(self):
        """
        Test creating a new MajorCategory.
        """
        data = {'name': 'Electronics'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MajorCategory.objects.count(), 3)
        self.assertEqual(MajorCategory.objects.get(id=3).name, 'Electronics')

    def test_retrieve_major_category(self):
        """
        Test retrieving an existing MajorCategory.
        """
        response = self.client.get(reverse('majorcategory-detail', kwargs={'pk': self.category1.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serializer = MajorCategorySerializer(self.category1)
        self.assertEqual(response.data, serializer.data)

    def test_update_major_category(self):
        """
        Test updating an existing MajorCategory.
        """
        data = {'name': 'Updated Furniture'}
        response = self.client.put(reverse('majorcategory-detail', kwargs={'pk': self.category1.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category1.refresh_from_db()
        self.assertEqual(self.category1.name, 'Updated Furniture')

    def test_delete_major_category(self):
        """
        Test deleting an existing MajorCategory.
        """
        response = self.client.delete(reverse('majorcategory-detail', kwargs={'pk': self.category1.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MajorCategory.objects.count(), 1)  # Only category2 should remain

    def test_create_major_category_without_name(self):
        """
        Test creating a MajorCategory without a name (should fail).
        """
        data = {}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_non_existent_major_category(self):
        """
        Test retrieving a MajorCategory that does not exist (should fail).
        """
        response = self.client.get(reverse('majorcategory-detail', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_non_existent_major_category(self):
        """
        Test updating a MajorCategory that does not exist (should fail).
        """
        data = {'name': 'Non-existent Category'}
        response = self.client.put(reverse('majorcategory-detail', kwargs={'pk': 999}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_non_existent_major_category(self):
        """
        Test deleting a MajorCategory that does not exist (should fail).
        """
        response = self.client.delete(reverse('majorcategory-detail', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_duplicate_major_category(self):
        """
        Test creating a MajorCategory with a duplicate name (should fail).
        """
        data = {'name': 'Furniture'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
