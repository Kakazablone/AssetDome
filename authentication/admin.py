from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from typing import Tuple, Dict, Any

class CustomUserAdmin(UserAdmin):
    """
    Admin interface for the CustomUser model, allowing management of users in the admin panel.

    This admin class customizes the user management interface to include specific fields and options
    for creating and editing users, along with filtering and searching capabilities.
    """

    model: CustomUser

    # Define the fields to display in the admin interface
    list_display: Tuple[str, ...] = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')

    # Define the sections and fields displayed when adding or changing a user
    fieldsets: Tuple[Tuple[str, Dict[str, Any]], ...] = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Add fields that should be required when creating a new user
    add_fieldsets: Tuple[Tuple[str, Dict[str, Any]], ...] = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )

    # Enable searching by these fields in the admin panel
    search_fields: Tuple[str, ...] = ('email', 'username', 'first_name', 'last_name')

    # Add filters for the list display
    list_filter: Tuple[str, ...] = ('is_active', 'is_staff', 'is_superuser')

    # Set the ordering of the users
    ordering: Tuple[str, ...] = ('username',)

# Register the custom user and its admin model
admin.site.register(CustomUser, CustomUserAdmin)
