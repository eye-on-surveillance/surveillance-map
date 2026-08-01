"""
API URL configuration for cameras.
"""

from django.urls import path

from . import api

urlpatterns = [
    path("cameras/", api.CameraListAPIView.as_view(), name="camera-list"),
    path("cameras/export.csv", api.export_csv, name="camera-export-csv"),
    path("cameras/export.geojson", api.export_geojson, name="camera-export-geojson"),
]
