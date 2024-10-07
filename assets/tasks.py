from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime, timedelta
import os
import csv
from weasyprint import HTML
from django.template.loader import render_to_string
from django.db.models import Sum
from .models import Asset, Department, Supplier, Location, MajorCategory, MinorCategory
from assetracker.celery import is_last_day_of_month
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_monthly_report():
    """
    Generates and sends a monthly asset report via email.

    This function collects data about:
    - New assets added during the current month.
    - Assets disposed of during the current month.
    - Assets that have become fully depreciated during the current month.
    
    The report is generated as a CSV file and sent via email.

    Returns:
        str: A message indicating whether the report was successfully sent.
    """
    try:
        # Check if today is the last day of the month before generating the report
        if is_last_day_of_month():
            today = datetime.now().date()
            first_day_of_month = today.replace(day=1)

            # Log the report generation process
            logger.info("Generating monthly asset report for the period from %s to %s.", first_day_of_month, today)

            # Fetch assets created this month
            new_assets = Asset.objects.filter(created_at__gte=first_day_of_month)
            logger.info("Found %d new assets created this month.", new_assets.count())

            # Fetch assets disposed of this month
            disposed_assets = Asset.objects.filter(is_disposed=True, disposed_at__gte=first_day_of_month)
            logger.info("Found %d disposed assets this month.", disposed_assets.count())

            # Identify fully depreciated assets this month
            fully_depreciated_assets = []
            for asset in Asset.objects.all():
                current_nbv = asset.calculate_depreciation()
                expected_depreciation_end = asset.date_placed_in_service + timedelta(days=365 * asset.economic_life)

                if current_nbv == 0 and first_day_of_month <= expected_depreciation_end <= today:
                    fully_depreciated_assets.append({
                        'asset': asset,
                        'depreciation_end_date': expected_depreciation_end
                    })
            logger.info("Found %d fully depreciated assets this month.", len(fully_depreciated_assets))

            # Create a CSV report
            file_name = 'monthly_report.csv'
            file_path = os.path.join(settings.REPORTS_ROOT, file_name)

            with open(file_path, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Report Type', 'Asset Code', 'Barcode', 'Description',
                                'Date Placed in Service', 'Economic Life',
                                'Depreciation Method', 'Disposal Date', 'Disposed By'])

                # Write new assets to CSV
                writer.writerow(['New Assets This Month'])
                for asset in new_assets:
                    writer.writerow([
                        'New Asset', asset.asset_code, asset.barcode, asset.description,
                        asset.date_placed_in_service, asset.economic_life,
                        asset.get_depreciation_method_display(), 'N/A'
                    ])

                # Write disposed assets to CSV
                writer.writerow(['Disposed Assets This Month'])
                for asset in disposed_assets:
                    writer.writerow([
                        'Disposed Asset', asset.asset_code, asset.barcode, asset.description,
                        asset.date_placed_in_service, asset.economic_life,
                        asset.get_depreciation_method_display(), asset.disposed_at,
                        asset.disposed_by.username if asset.disposed_by else 'N/A'
                    ])

                # Write fully depreciated assets to CSV
                writer.writerow(['Fully Depreciated Assets This Month'])
                for entry in fully_depreciated_assets:
                    asset = entry['asset']
                    depreciation_end_date = entry['depreciation_end_date']
                    writer.writerow([
                        'Fully Depreciated', asset.asset_code, asset.barcode, asset.description,
                        asset.date_placed_in_service, asset.economic_life,
                        asset.get_depreciation_method_display(), depreciation_end_date,
                        'N/A'
                    ])
            
            logger.info("Monthly report successfully written to CSV at %s.", file_path)

            # Send the email with the CSV attached
            email = EmailMessage(
                subject="Monthly Asset Report",
                body="Please find attached the monthly asset report.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['recipient@example.com'],  # Change to actual recipients
            )
            email.attach_file(file_path)
            email.send(fail_silently=False)

            logger.info("Monthly report email sent to recipients.")
            return "Monthly report sent."
        else:
            logger.info("Today is not the last day of the month. No report generated.")
            return "No report sent. Not the last day of the month."
    except Exception as e:
        # Log any exceptions during the report generation or email sending
        logger.error("Error generating or sending the monthly report: %s", str(e))
        return f"Failed to send report: {str(e)}"

@shared_task
def send_fully_depreciated_assets_email():
    """
    Sends a notification email listing all fully depreciated assets.

    Fully depreciated assets are those whose net book value (NBV) reaches 0
    on the current day. If no assets reach 0 NBV, no email is sent.

    The email contains a CSV attachment with details of the fully depreciated assets.

    Returns:
        str: A message indicating whether the notification was sent or not.
    """
    today = datetime.now().date()
    fully_depreciated_assets = []

    logger.info("Checking for fully depreciated assets as of %s.", today)

    for asset in Asset.objects.all():
        date_placed = asset.date_placed_in_service
        expected_depreciation_end = date_placed + timedelta(days=asset.economic_life * 365)

        if expected_depreciation_end == today:
            current_nbv = asset.calculate_depreciation()
            if current_nbv == 0:
                fully_depreciated_assets.append(asset)
                logger.info("Asset %s is fully depreciated.", asset.asset_code)

    if fully_depreciated_assets:
        # Create a CSV for fully depreciated assets
        file_name = 'fully_depreciated_assets.csv'
        file_path = os.path.join(settings.REPORTS_ROOT, file_name)

        logger.info("Creating CSV report for %d fully depreciated assets.", len(fully_depreciated_assets))

        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Asset Code', 'Barcode', 'Description',
                             'Date Placed in Service', 'Economic Life (Years)',
                             'Depreciation Method'])

            for asset in fully_depreciated_assets:
                writer.writerow([
                    asset.asset_code, asset.barcode, asset.description,
                    asset.date_placed_in_service, asset.economic_life,
                    asset.get_depreciation_method_display()
                ])

        logger.info("CSV report created at %s.", file_path)

        # Send email with CSV attached
        email = EmailMessage(
            subject="Fully Depreciated Assets Notification",
            body="The following assets have fully depreciated today:",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=['recipient@example.com'],  # Change to actual recipients
        )
        email.attach_file(file_path)
        email.send(fail_silently=False)

        logger.info("Fully depreciated assets notification email sent.")
        return "Fully depreciated assets notification sent."

    logger.info("No assets hit 0 NBV today.")
    return "No assets hit 0 NBV today."

@shared_task
def send_quarterly_summary_report():
    """
    Generates and sends a quarterly asset summary report via email.

    The report is generated as a PDF and includes statistics on the total
    assets, purchase prices, and depreciation summaries, grouped by
    departments, suppliers, locations, and categories.

    Returns:
        str: A message indicating whether the report was sent.
    """
    logger.info("Starting quarterly summary report generation.")

    # Calculate overall summary
    total_assets = Asset.objects.count()
    total_purchase_price = Asset.objects.aggregate(Sum('purchase_price'))['purchase_price__sum'] or 0
    total_nbv = Asset.objects.aggregate(Sum('net_book_value'))['net_book_value__sum'] or 0
    total_accumulated_depreciation = total_purchase_price - total_nbv

    overall_summary = {
        'total_assets': total_assets,
        'total_purchase_price': total_purchase_price,
        'total_nbv': total_nbv,
        'total_accumulated_depreciation': total_accumulated_depreciation,
        'total_employees': Department.objects.count(),  # Example statistic
    }

    logger.info("Overall summary calculated: %s", overall_summary)

    # Prepare summary data
    context = {
        'overall_summary': overall_summary,
        'departments_summary': summarize_by_queryset(Department.objects.all(), 'department'),
        'suppliers_summary': summarize_by_queryset(Supplier.objects.all(), 'supplier'),
        'locations_summary': summarize_by_queryset(Location.objects.all(), 'location'),
        'major_categories_summary': summarize_by_queryset(MajorCategory.objects.all(), 'major_category'),
        'minor_categories_summary': summarize_by_queryset(MinorCategory.objects.all(), 'minor_category'),
    }

    # Generate PDF from HTML
    html_content = render_to_string('reports/quarterly_asset_summary.html', context)
    file_name = 'quarterly_asset_summary.pdf'
    file_path = os.path.join(settings.REPORTS_ROOT, file_name)
    HTML(string=html_content).write_pdf(file_path)

    logger.info("PDF report generated at: %s", file_path)

    # Send the email with PDF attached
    email = EmailMessage(
        subject="Quarterly Asset Summary Report",
        body="Please find attached the quarterly summary report.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['recipient1@example.com', 'recipient2@example.com'],  # Change to actual recipients
    )
    email.attach_file(file_path)
    email.send(fail_silently=False)

    logger.info("Quarterly asset summary report sent to recipients.")
    return "Quarterly asset summary report sent."

def summarize_by_queryset(queryset, name_field: str):
    """
    Summarizes assets by a given queryset and name field.

    Args:
        queryset: A Django QuerySet of objects to summarize.
        name_field (str): The field name to filter assets by.

    Returns:
        list: A list of dictionaries containing the summary of assets for each instance.
    """
    logger.info("Summarizing assets by field: %s", name_field)
    summaries = []

    for instance in queryset:
        assets = Asset.objects.filter(**{name_field: instance})
        total_assets = assets.count()
        total_purchase_price = assets.aggregate(Sum('purchase_price'))['purchase_price__sum'] or 0
        total_nbv = assets.aggregate(Sum('net_book_value'))['net_book_value__sum'] or 0
        total_accumulated_depreciation = total_purchase_price - total_nbv

        summaries.append({
            'instance': str(instance),
            'total_assets': total_assets,
            'total_purchase_price': total_purchase_price,
            'total_nbv': total_nbv,
            'total_accumulated_depreciation': total_accumulated_depreciation,
        })

    logger.info("Summarization complete. Total summaries generated: %d", len(summaries))
    return summaries
