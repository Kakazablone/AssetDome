import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver, Signal
from django.core.cache import cache
from .models import Asset, Department, Supplier, Location, MajorCategory, MinorCategory, Employee

# Initialize logger
logger = logging.getLogger(__name__)

# Custom signal for import completion
import_completed = Signal()

@receiver([post_save, post_delete], sender=Asset)
def clear_asset_cache(sender, instance, **kwargs):
    """
    Clear the cache for assets when an Asset is created, updated, or deleted.
    
    This function clears the following caches:
    - `asset_summary_cache`: Always cleared when an asset changes.
    - `active_assets`: Always cleared to reflect up-to-date asset listings.
    - `disposed_assets`: Cleared if the asset is marked as disposed.

    Args:
        sender: The model class that sends the signal (Asset).
        instance: The actual instance of the asset that is being saved or deleted.
        **kwargs: Additional keyword arguments.

    Signals:
        post_save: Triggered when an Asset is created or updated.
        post_delete: Triggered when an Asset is deleted.
    """
    # Always clear the asset summary cache
    logger.info("Clearing 'asset_summary_cache'.")
    cache.delete('asset_summary_cache')

    # Clear the cache for active assets
    logger.info("Clearing 'active_assets'.")
    cache.delete('active_assets')

    # Check if the asset is disposed
    if instance.is_disposed:
        logger.info(f"Asset '{instance.asset_code}' is disposed. Clearing 'disposed_assets' cache.")
        cache.delete('disposed_assets')  # Clear the disposed assets cache

@receiver([post_save, post_delete], sender=Department)
@receiver([post_save, post_delete], sender=Supplier)
@receiver([post_save, post_delete], sender=Location)
@receiver([post_save, post_delete], sender=MajorCategory)
@receiver([post_save, post_delete], sender=MinorCategory)
@receiver([post_save, post_delete], sender=Employee)
def clear_asset_summary_cache(sender, **kwargs):
    """
    Clear the asset summary cache when any related model is created, updated, or deleted.
    
    The cache for the `asset_summary_cache` is cleared whenever any of the following models are
    saved or deleted:
    - Department
    - Supplier
    - Location
    - MajorCategory
    - MinorCategory
    - Employee

    Args:
        sender: The model class that sends the signal.
        **kwargs: Additional keyword arguments.

    Signals:
        post_save: Triggered when a related model is created or updated.
        post_delete: Triggered when a related model is deleted.
    """
    logger.info(f"Clearing 'asset_summary_cache' due to change in {sender.__name__}.")
    cache.delete('asset_summary_cache')

@receiver(import_completed)
def clear_import_cache(sender, **kwargs):
    """
    Clear caches after an asset import is completed.

    This function is triggered when the `import_completed` signal is sent,
    typically after a bulk import of assets.

    The following caches are cleared:
    - `asset_summary_cache`: Summary of assets.
    - `active_assets`: Cache for active assets.
    - `disposed_assets`: Cache for disposed assets.

    Args:
        sender: The object that sent the signal.
        **kwargs: Additional keyword arguments.
    """
    logger.info("Clearing caches after import completion: 'asset_summary_cache', 'active_assets', and 'disposed_assets'.")
    cache.delete('asset_summary_cache')
    cache.delete('active_assets')
    cache.delete('disposed_assets')
