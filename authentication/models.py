import os
import logging
from typing import Any, Optional, List
from PIL import Image
from django.contrib.auth.models import AbstractUser
from django.db import models

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

        logger.debug(f"Attempting to delete old image: {old_image} for field '{field_name}'")

        # Proceed if there is an old image and it's a valid file
        if old_image and os.path.isfile(old_image.path):
            # Check if the old image's name is not in the list of default images
            if not any(default_image in old_image.name for default_image in default_images):
                os.remove(old_image.path)  # Delete the old image file
                logger.info(f"Deleted old image: {old_image.path}")  # Log the deletion
            else:
                logger.info(f"Skipped deletion for default image: {old_image.name}")

    except Exception as e:
        logger.error(f"Error deleting old image for {instance}: {e}", exc_info=True)  # Log error with stack trace

class CustomUser(AbstractUser):
    """
    Custom user model extending the default Django user with additional fields.

    Attributes:
        email (EmailField): User's email address, must be unique.
        profile_image (ImageField): User's profile image with a default image set.
    """
    email = models.EmailField(unique=True)
    profile_image = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        default='profile_pictures/default_profile.png'  # Default image
    )

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Overrides the save method to handle profile image resizing and deletion of old images.

        If the user already exists, deletes the old profile image before saving the new one.
        Resizes the uploaded image to a maximum of 300x300 pixels.

        Args:
            *args (Any): Positional arguments passed to the superclass's save method.
            **kwargs (Any): Keyword arguments passed to the superclass's save method.

        Returns:
            None: This function does not return a value.

        Raises:
            Exception: Any exceptions raised during image processing will be caught and logged.
        """
        if self.pk:
            logger.debug(f"User {self.username} exists. Attempting to delete old profile image.")
            delete_old_image(self, 'profile_image')

        super().save(*args, **kwargs)

        if self.profile_image:
            try:
                img = Image.open(self.profile_image.path)

                # Resize the image if it's too large
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.profile_image.path, quality=85)  # Slight compression for better performance
                    logger.info(f"Resized image for user {self.username} to {output_size}.")
            except Exception as e:
                logger.error(f"Error processing image for user '{self.username}': {e}", exc_info=True)

    def __str__(self) -> str:
        """
        Returns a string representation of the CustomUser instance.

        Returns:
            str: The username of the user.
        """
        return self.username
