Asset Dome - Asset Management Web Application
Overview
Asset Dome is a comprehensive asset management solution built using Django REST Framework (DRF) with JWT-based authentication. This application enables organizations to manage assets efficiently, track asset lifecycle stages, calculate depreciation, and generate reports, among other functionalities.

Features
1. Asset Management
Detailed Asset Information: Store and manage assets with fields like Asset Code, Barcode, RFID, Major/Minor Categories, Asset Type, Location, and Department.
Automatic Asset Code Generation: Asset codes are auto-incremented in the format AS000001, AS000002, etc.
Customizable Fields: Add dynamic options for categories, departments, and asset conditions.
Depreciation Calculation: Calculate asset depreciation based on user-selected accounting methods.
CRUD Tracking: Timestamped logs for each Create, Read, Update, and Delete operation, retaining user records even after account deletion.
2. User Authentication and Management
Custom Authentication System: Users can register, log in, and manage their passwords with JWT authentication.
Enhanced Security: Includes functionalities for password reset, password change, and secure account deletion.
Custom User Model: Extends AbstractUser to support first name, last name, email, and password fields.
Role-Based Access Control: Allows superusers to edit specific fields like Barcode, while other users have restricted permissions.
3. API Functionalities
DRF API with Viewsets: Provides CRUD endpoints for assets, user authentication, and related entities using viewsets.
Swagger Documentation: Integrated Swagger for API documentation, covering endpoints, parameters, and response formats.
Internationalization and Pagination: Supports multi-language responses and paginates data for optimized API performance.
4. Reports and Exporting
Excel Report Generation: Generate detailed Excel reports for all assets with their fields (e.g., asset code, barcode, condition, status).
Historical Data Retention: Retains asset history even if users or categories are removed, ensuring accurate reporting.
5. Database Structure and Relationships
Modular Database Design: Related classes (Departments, Locations, Suppliers, Major/Minor Categories, Employees) use ForeignKey relationships for easy data linkage.
Cascading Deletes for Categories: Deleting a major or minor category will delete associated assets, preserving data integrity.
Geolocation Support: Location model includes latitude and longitude fields, automatically updated.
Project Structure
graphql

Setup and Installation
Prerequisites
Python 3.7
Django 3.x+
Django REST Framework
djangorestframework-simplejwt (for JWT support)
Installation
Clone the Repository

git clone https://github.com/Kakazablone/AssetDome.git
cd AssetDome
Create a Virtual Environment
python3 -m venv venv
source venv/bin/activate
Install Dependencies
pip install -r requirements.txt

Database Migration
python manage.py migrate
Create a Superuser

python manage.py createsuperuser
Run the Server
python manage.py runserver

API Documentation
The API documentation can be accessed at:
http://localhost:8000/swagger/

Usage
Running Tests
python manage.py test

Sample API Requests
Using curl or Postman, you can interact with various endpoints. Examples:

Login
curl -X POST http://localhost:8000/auth/login/ -d "username=user&password=pass"

Create Asset
curl -X POST http://localhost:8000/assets/ -H "Authorization: Bearer <token>" -d "<asset_data>"

Available Endpoints
Refer to the Swagger documentation for a full list of endpoints, including:

GET /assets/ - List all assets
POST /assets/ - Create a new asset
PUT /assets/<id>/ - Update an asset
DELETE /assets/<id>/ - Delete an asset

Contributing
Feel free to submit issues or pull requests. Contributions are welcome!

License
This project is licensed under the MIT License - see the LICENSE file for details.
