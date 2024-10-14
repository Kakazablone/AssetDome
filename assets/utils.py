import csv
import pandas as pd
from io import BytesIO, StringIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from django.core.exceptions import ValidationError
from .models import Asset, MajorCategory, MinorCategory, Location, Department, Employee, Supplier
import os
from django.shortcuts import get_object_or_404
from django.conf import settings

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from django.db.models import Sum, QuerySet, Model
from typing import List, Dict, Any, Optional, Union, Type
from django.db import models
import logging

logger = logging.getLogger(__name__)

def generate_csv(data: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> HttpResponse:
    """
    Generate a CSV response from the provided data.

    Parameters:
    - data (List[Dict[str, Any]]): A list of dictionaries containing the data to be written to the CSV.
    - fields (Optional[List[str]]): A list of fields to include as headers in the CSV. If None, all fields will be included.

    Returns:
    - HttpResponse: A Django HttpResponse object containing the generated CSV file.

    Raises:
    - ValueError: If data is empty or not properly formatted.
    """
    logger.info("Starting CSV generation.")
    
    if not data:
        logger.error("No data provided for CSV generation.")
        raise ValueError("Data must not be empty.")

    output = StringIO()
    writer = csv.writer(output)

    # Write headers based on fields
    if fields:
        logger.info("Writing CSV headers: %s", fields)
        writer.writerow(fields)  # Write specified headers
        # Write data rows
        for index, row in enumerate(data):
            writer.writerow([row.get(field, '') for field in fields])  # Get values for specified fields
            logger.debug("Row %d written to CSV: %s", index, row)
    else:
        # Fallback to all fields if none specified
        logger.info("No fields specified. Using all available fields as headers.")
        writer.writerow(data[0].keys())
        for index, row in enumerate(data):
            writer.writerow(row.values())
            logger.debug("Row %d written to CSV: %s", index, row)

    output.seek(0)

    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report.csv"'
    
    logger.info("CSV generation complete. Response ready to send.")
    return response

def generate_pdf(
    data: List[Dict[str, Any]],
    user: Optional[Any] = None,
    fields: Optional[List[str]] = None,
    filtered_queryset: Optional[Any] = None
) -> HttpResponse:
    """
    Generate a PDF report from the provided asset data.

    Parameters:
    - data (List[Dict[str, Any]]): A list of dictionaries containing asset data to be included in the report.
    - user (Optional[Any]): The user object generating the report, used to identify the generator.
    - fields (Optional[List[str]]): Specific fields to be included in the PDF report, if applicable.
    - filtered_queryset (Optional[Any]): A filtered queryset for fetching overall summary data.

    Returns:
    - HttpResponse: A Django HttpResponse object containing the generated PDF file.

    Raises:
    - FileNotFoundError: If the logo file cannot be found.
    - ValueError: If no data is provided for the report.
    """
    logger.info("Starting PDF generation.")

    if not data:
        logger.error("No data provided for PDF generation.")
        raise ValueError("Data must not be empty.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Prepare styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    body_style = styles['BodyText']

    elements = []

    # Cover Page
    title = Paragraph("Asset Report", title_style)
    logo_path = os.path.join(settings.MEDIA_ROOT, 'asset_images', 'default_asset.png')
    
    if not os.path.exists(logo_path):
        logger.error("Logo file not found at %s", logo_path)
        raise FileNotFoundError(f"Logo file not found at {logo_path}")
    
    logo = Image(logo_path, 1.5 * inch, 1.5 * inch)

    # Create a centered layout for the logo and title
    cover_table_data = [
        [logo],
        [title],
        [Spacer(1, 20)],  # Space below title
        [Paragraph(f"Generated by: {user.username if user and hasattr(user, 'username') else 'Unknown'}", body_style)],
        [Paragraph(f"Generated on: {datetime.now().strftime('%A, %d %B, %Y')}", body_style)],
        [Paragraph(f"Generated at: {datetime.now().strftime('%H:%M')}", body_style)]
    ]

    cover_table = Table(cover_table_data, colWidths=[doc.width])
    cover_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    ]))

    elements.append(cover_table)

    # Add a page break after the cover page
    elements.append(PageBreak())

    # Fetch overall summary data for the filtered queryset
    overall_summary = fetch_overall_summary(filtered_queryset)

    # Summary Section
    summary_data = [
        [Paragraph("Overall Summary", title_style)],
        [Paragraph(f"Total Assets: {overall_summary['total_assets']}", body_style)],
        [Paragraph(f"Total Purchase Price: ${overall_summary['total_purchase_price']:,.2f}", body_style)],
        [Paragraph(f"Total NBV: ${overall_summary['total_nbv']:,.2f}", body_style)],
        [Paragraph(f"Total Accumulated Depreciation: ${overall_summary['total_accumulated_depreciation']:,.2f}", body_style)],
        [Spacer(1, 20)]  # Space below summary
    ]

    summary_table = Table(summary_data, colWidths=[doc.width])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    ]))
    elements.append(summary_table)

    # Table for Data
    if data:
        table_data = []
        headers = list(data[0].keys())
        table_data.append(headers)

        for row in data:
            table_data.append([row[key] if row[key] is not None else 'N/A' for key in headers])
            logger.debug("Row written to PDF: %s", row)

        data_table = Table(table_data)
        data_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(data_table)

    # Page Numbers
    def add_page_number(canvas, doc):
        page_number = f"Page {doc.page}"
        canvas.drawString(500, 10, page_number)

    doc.build(elements, onFirstPage=lambda c, d: add_page_number(c, d),
              onLaterPages=lambda c, d: add_page_number(c, d))

    buffer.seek(0)
    logger.info("PDF generation complete. Response ready to send.")
    return HttpResponse(buffer, content_type='application/pdf')

def fetch_overall_summary(filtered_queryset: QuerySet) -> Dict[str, float]:
    """
    Calculate overall summary metrics from a filtered queryset of assets.

    Args:
        filtered_queryset (QuerySet): A Django QuerySet containing asset objects
                                       filtered based on specific criteria.

    Returns:
        Dict[str, float]: A dictionary containing the total number of assets,
                          total purchase price, total net book value (NBV),
                          and total accumulated depreciation.
    """
    logger.info("Calculating overall summary from filtered queryset.")
    
    total_assets = filtered_queryset.count()
    logger.debug("Total assets: %d", total_assets)
    
    total_purchase_price = filtered_queryset.aggregate(
        total_purchase_price=Sum('purchase_price')
    )['total_purchase_price'] or 0
    logger.debug("Total purchase price: $%.2f", total_purchase_price)
    
    total_nbv = filtered_queryset.aggregate(
        total_nbv=Sum('net_book_value')
    )['total_nbv'] or 0
    logger.debug("Total NBV: $%.2f", total_nbv)
    
    total_accumulated_depreciation = total_purchase_price - total_nbv

    return {
        'total_assets': total_assets,
        'total_purchase_price': total_purchase_price,
        'total_nbv': total_nbv,
        'total_accumulated_depreciation': total_accumulated_depreciation,
    }

def convert_to_naive_datetime(value: Union[pd.Timestamp, datetime]) -> Union[pd.Timestamp, datetime]:
    """
    Convert a timezone-aware datetime or pandas Timestamp to a timezone-naive datetime.

    Args:
        value (Union[pd.Timestamp, datetime]): The input value to convert. This can be a
                                                pandas Timestamp or a datetime object.

    Returns:
        Union[pd.Timestamp, datetime]: The converted timezone-naive datetime or
                                        Timestamp. If the input value is already naive,
                                        it is returned unchanged.
    """
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            return value.tz_localize(None)
    elif hasattr(value, 'tzinfo') and value.tzinfo is not None:
        return value.replace(tzinfo=None)

    return value

def generate_excel(data: List[Dict[str, Union[str, int, float, pd.Timestamp]]],
                   fields: List[str]) -> HttpResponse:
    """
    Generate an Excel file from the provided data and return it as an HTTP response.

    This function processes the input data to ensure that any timezone-aware datetime
    values are converted to naive datetimes before generating the Excel file.

    Args:
        data (List[Dict[str, Union[str, int, float, pd.Timestamp]]]): A list of dictionaries
            representing the data to be exported to Excel. Each dictionary should map
            field names to their corresponding values, which can be strings, integers,
            floats, or pandas Timestamps.
        fields (List[str]): A list of field names to include in the Excel file. If empty,
            all fields will be included.

    Returns:
        HttpResponse: An HTTP response containing the generated Excel file as an
                      attachment with the filename "report.xlsx".

    Raises:
        ValueError: If the input data is empty or if none of the specified fields are found
                    in the data.
    """
    # Check if data is empty
    if not data:
        logger.error("Input data is empty.")
        raise ValueError("Input data cannot be empty.")

    # Convert timezone-aware datetimes to naive datetimes
    logger.info("Converting timezone-aware datetime values to naive datetime.")
    for row in data:
        for key, value in row.items():
            if isinstance(value, pd.Timestamp):
                row[key] = convert_to_naive_datetime(value)

    # Filter data based on fields
    logger.info("Filtering data based on specified fields.")
    if fields:
        # Check if fields are present in the data
        missing_fields = [field for field in fields if field not in data[0]]
        if missing_fields:
            logger.warning(f"Some specified fields are missing in the data: {missing_fields}")

        filtered_data = [{field: row[field] for field in fields if field in row} for row in data]
    else:
        filtered_data = data

    # Create a DataFrame and write to Excel
    logger.info("Creating Excel file.")
    df = pd.DataFrame(filtered_data)
    output = BytesIO()

    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            logger.info("Excel file created successfully.")
    except Exception as e:
        logger.error("Error while writing to Excel file: %s", e)
        raise

    output.seek(0)
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="report.xlsx"'
    logger.info("Excel file prepared for download.")
    
    return response

def import_assets_from_file(file_path: str) -> List[str]:
    """
    Imports assets from an Excel or CSV file and updates or creates asset records.

    This function reads data from a specified Excel or CSV file, checks for existing assets
    based on asset codes, and updates their details. If an asset code does not exist,
    a new asset record is created. The function logs any conflicts for assets that could
    not be found during the import process.

    Args:
        file_path (str): The path to the Excel or CSV file containing asset data.

    Returns:
        List[str]: A list of conflict messages indicating any assets that were not found.

    Raises:
        ValueError: If the file format is unsupported.
    """
    # Determine the file type and read the data
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.xlsx':
        logger.info("Importing data from Excel file: %s", file_path)
        df = pd.read_excel(file_path)
    elif file_extension == '.csv':
        logger.info("Importing data from CSV file: %s", file_path)
        df = pd.read_csv(file_path)
    else:
        logger.error("Unsupported file format: %s", file_extension)
        raise ValueError("Unsupported file format. Please use .xlsx or .csv files.")

    conflict_log = []

    for index, row in df.iterrows():
        asset_code = row.get('asset_code', '').strip() or 'DEFAULT'

        if asset_code and asset_code != 'DEFAULT':
            try:
                asset = Asset.objects.get(asset_code=asset_code)
                logger.info("Updating asset: %s", asset_code)

                # Update fields if the asset exists
                asset.barcode = row.get('barcode', asset.barcode)
                asset.rfid = row.get('rfid', asset.rfid)
                asset.major_category = get_related_object('MajorCategory', row.get('major_category'))
                asset.minor_category = get_related_object('MinorCategory', row.get('minor_category'))
                asset.description = row.get('description', asset.description)
                asset.serial_number = row.get('serial_number', asset.serial_number)
                asset.model_number = row.get('model_number', asset.model_number)
                asset.asset_type = row.get('asset_type', asset.asset_type)
                asset.location = get_related_object('Location', row.get('location'))
                asset.department = get_related_object('Department', row.get('department'))
                asset.employee = get_related_object('Employee', row.get('employee'))
                asset.supplier = get_related_object('Supplier', row.get('supplier'))
                asset.economic_life = row.get('economic_life', asset.economic_life)
                asset.purchase_price = row.get('purchase_price', asset.purchase_price)
                asset.units = row.get('units', asset.units)
                asset.date_of_purchase = row.get('date_of_purchase', asset.date_of_purchase)
                asset.date_placed_in_service = row.get('date_placed_in_service', asset.date_placed_in_service)
                asset.condition = row.get('condition', asset.condition)
                asset.status = row.get('status', asset.status)
                asset.depreciation_method = row.get('depreciation_method', asset.depreciation_method)

                asset.save()  # Call the save method to handle updates
                logger.info("Asset updated successfully: %s", asset_code)

            except Asset.DoesNotExist:
                conflict_log.append(f"Asset with code '{asset_code}' does not exist.")
                logger.warning("Conflict: %s", conflict_log[-1])

        else:
            # Generate a new asset code for new entries
            logger.info("Creating new asset with placeholder code.")
            asset = Asset()
            asset.asset_code = 'DEFAULT'  # Placeholder for auto generation
            asset.barcode = row.get('barcode')
            asset.rfid = row.get('rfid')
            asset.major_category = get_related_object('MajorCategory', row.get('major_category'))
            asset.minor_category = get_related_object('MinorCategory', row.get('minor_category'))
            asset.description = row.get('description')
            asset.serial_number = row.get('serial_number')
            asset.model_number = row.get('model_number')
            asset.asset_type = row.get('asset_type')
            asset.location = get_related_object('Location', row.get('location'))
            asset.department = get_related_object('Department', row.get('department'))
            asset.employee = get_related_object('Employee', row.get('employee'))
            asset.supplier = get_related_object('Supplier', row.get('supplier'))
            asset.economic_life = row.get('economic_life')
            asset.purchase_price = row.get('purchase_price')
            asset.units = row.get('units')
            asset.date_of_purchase = row.get('date_of_purchase')
            asset.date_placed_in_service = row.get('date_placed_in_service')
            asset.condition = row.get('condition')
            asset.status = row.get('status')
            asset.depreciation_method = row.get('depreciation_method')

            asset.save()  # This will generate a new asset code
            logger.info("New asset created with code: %s", asset.asset_code)

    return conflict_log

def get_related_object(model_name: str, value: Any) -> Any:
    """
    Fetches the related object based on the model name and identifier.

    This function attempts to retrieve an instance of a model based on the given
    model name and value. It raises a 404 error if the object is not found.

    Args:
        model_name (str): The name of the model to fetch.
        value (Any): The value to match the 'name' field of the model.

    Returns:
        Any: The related object instance if found.

    Raises:
        ValidationError: If the provided model name is not valid.
    """
    # Define the models dictionary and type hint with Type[models.Model]
    Model: Optional[Type[models.Model]] = {
        'MajorCategory': MajorCategory,
        'MinorCategory': MinorCategory,
        'Location': Location,
        'Department': Department,
        'Employee': Employee,
        'Supplier': Supplier,
    }.get(model_name)

    if Model:
        # Use SlugRelatedField's 'name' field to match
        return get_object_or_404(Model, name=value)  # Raises a 404 if not found

    logger.error("Invalid model name: %s", model_name)
    raise ValidationError(f"Model '{model_name}' is not valid.")


class FilterMixin:
    def filter_queryset(self, model: Type[Model]) -> QuerySet:
        """
        Filters the queryset based on the request's query parameters.

        This method retrieves all objects of the specified model and applies
        filtering based on the provided query parameters, excluding certain keys.

        Args:
            model (Type[Model]): The model class to filter.

        Returns:
            QuerySet: The filtered queryset based on the applied criteria.

        Logs:
            - INFO: Logs the number of total objects before filtering.
            - DEBUG: Logs each filtering operation and the resultant queryset size.
        """
        queryset = model.objects.all()
        logger.info(f"Total objects retrieved: {queryset.count()}")

        # Apply dynamic filtering based on query parameters
        for key, value in self.request.query_params.items():
            if key not in ['report_format', 'model', 'fields']:
                filter_criteria = {key: value}
                queryset = queryset.filter(**filter_criteria)
                logger.debug(f"Applied filter: {filter_criteria}, Resulting queryset size: {queryset.count()}")

        return queryset