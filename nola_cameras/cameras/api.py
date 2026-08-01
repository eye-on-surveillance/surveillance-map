"""
DRF API views for cameras.
"""

import csv

from django.db.models import Exists, OuterRef, Prefetch
from django.http import HttpResponse, JsonResponse
from rest_framework import generics

from .models import Camera, CameraImage
from .serializers import CameraGeoSerializer


def _vetted_cameras_queryset(query_params=None):
    """Shared queryset for vetted cameras with optional filtering."""
    queryset = Camera.objects.filter(status=Camera.Status.VETTED).prefetch_related(
        Prefetch(
            "images",
            queryset=CameraImage.objects.filter(status=CameraImage.Status.APPROVED),
            to_attr="_approved_images",
        )
    )

    if query_params is None:
        return queryset

    facial_recognition = query_params.get("facial_recognition")
    if facial_recognition is not None:
        queryset = queryset.filter(
            facial_recognition=facial_recognition.lower() == "true"
        )

    has_shop = query_params.get("has_shop")
    if has_shop is not None:
        if has_shop.lower() == "true":
            queryset = queryset.exclude(associated_shop="")
        else:
            queryset = queryset.filter(associated_shop="")

    no_photos = query_params.get("no_photos")
    if no_photos and no_photos.lower() == "true":
        has_approved = CameraImage.objects.filter(
            camera=OuterRef("pk"), status=CameraImage.Status.APPROVED
        )
        queryset = queryset.filter(~Exists(has_approved))

    return queryset


class CameraListAPIView(generics.ListAPIView):
    """
    Returns all vetted cameras as GeoJSON for map display.

    Supports filtering via query parameters:
    - facial_recognition: true/false
    - has_shop: true/false
    - no_photos: true
    """

    serializer_class = CameraGeoSerializer

    def get_queryset(self):
        return _vetted_cameras_queryset(self.request.query_params)


def export_csv(request):
    """Export vetted cameras as a CSV download."""
    cameras = _vetted_cameras_queryset(request.GET)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="surveillance-cameras.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "id", "latitude", "longitude", "cross_road", "street_address",
        "camera_type", "associated_business", "facial_recognition",
        "manufacturer", "direction", "reported_at",
    ])

    for camera in cameras.iterator():
        writer.writerow([
            str(camera.pk),
            camera.latitude,
            camera.longitude,
            camera.cross_road,
            camera.street_address,
            camera.get_camera_type_display(),
            camera.associated_shop,
            camera.facial_recognition,
            camera.manufacturer,
            camera.direction,
            camera.reported_at.isoformat() if camera.reported_at else "",
        ])

    return response


def export_geojson(request):
    """Export vetted cameras as a downloadable GeoJSON file."""
    cameras = _vetted_cameras_queryset(request.GET)

    features = []
    for camera in cameras.iterator():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [camera.longitude, camera.latitude],
            },
            "properties": {
                "id": str(camera.pk),
                "cross_road": camera.cross_road,
                "street_address": camera.street_address,
                "camera_type": camera.get_camera_type_display(),
                "associated_business": camera.associated_shop,
                "facial_recognition": camera.facial_recognition,
                "manufacturer": camera.manufacturer,
                "direction": camera.direction,
                "reported_at": camera.reported_at.isoformat() if camera.reported_at else None,
            },
        })

    data = {"type": "FeatureCollection", "features": features}
    response = JsonResponse(data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = 'attachment; filename="surveillance-cameras.geojson"'
    return response
