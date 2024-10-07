from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssetViewSet, MajorCategoryViewSet, MinorCategoryViewSet,
    DepartmentViewSet, EmployeeViewSet, SupplierViewSet, LocationViewSet, ReportGenerationView, ImportAssetsView,
    AssetSummaryView, RecentActivityView, DisposedAssetViewSet
)
from django.conf import settings
from django.conf.urls.static import static
from typing import List

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='asset')  # Explicit basename for assets
router.register(r'major_categories', MajorCategoryViewSet, basename='majorcategory')
router.register(r'minor_categories', MinorCategoryViewSet, basename='minorcategory')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'disposed_assets', DisposedAssetViewSet, basename='disposedasset')


urlpatterns: List[path] = [
    path('', include(router.urls)),  # Include all router-generated URLs
    path('reports/', ReportGenerationView.as_view(), name='report-generation'),
    path('import/', ImportAssetsView.as_view(), name='asset-import'),
    path('summary/', AssetSummaryView.as_view(), name='asset-summary'),
    path('recent_activity/', RecentActivityView.as_view(), name='recent-activity')
    # path('disposed_assets/<int:pk>/undo/', DisposedAssetViewSet.as_view({'patch': 'undo_dispose'}))
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
