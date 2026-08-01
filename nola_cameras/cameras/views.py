"""
Views for camera mapping application.
"""

import uuid

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView
from django_ratelimit.decorators import ratelimit

from .forms import CameraReportForm, CorrectionProposalForm, PhotoProposalForm
from .models import AboutSection, Announcement, Camera, CameraImage, CorrectionProposal

_MOBILE_UA_KEYWORDS = ("mobile", "android", "iphone", "ipad", "ipod")

_NOLA_DEFAULT_LAT = 29.9511
_NOLA_DEFAULT_LNG = -90.0715
_NOLA_DEFAULT_ZOOM = 13


def _build_og_context(camera, request):
    location_label = camera.cross_road or camera.street_address or camera.associated_shop or "unknown location"
    title = f"Surveillance camera — {location_label}"

    parts = [f"{camera.get_camera_type_display()} camera"]
    if camera.associated_shop:
        parts.append(f"at {camera.associated_shop}")
    if camera.street_address and camera.street_address != location_label:
        parts.append(f"({camera.street_address})")
    if camera.facial_recognition:
        parts.append("· Facial recognition enabled")
    description = " ".join(parts) + "."

    image_url = None
    first_image = camera.images.filter(status=CameraImage.Status.APPROVED).first()
    if first_image:
        image_url = request.build_absolute_uri(first_image.image.url)

    canonical_url = f"{request.scheme}://{request.get_host()}/?camera={camera.pk}"
    return {"title": title, "description": description, "image_url": image_url, "url": canonical_url}


class MapView(TemplateView):
    """
    Main map view showing all vetted cameras.
    """

    template_name = "map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_count"] = Camera.objects.filter(status=Camera.Status.PENDING).count()
        context["site_info"] = AboutSection.objects.first()
        context["announcements"] = Announcement.objects.filter(is_active=True)

        og = None
        camera_uuid = self.request.GET.get("camera", "").strip()
        if camera_uuid:
            try:
                camera_id = uuid.UUID(camera_uuid)
            except ValueError:
                camera_id = None
            if camera_id:
                camera = Camera.objects.filter(pk=camera_id, status=Camera.Status.VETTED).first()
                if camera:
                    og = _build_og_context(camera, self.request)

        context["og"] = og
        return context


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=False), name="post")
class CameraReportView(FormView):
    """
    Public form for submitting new camera sightings.
    """

    template_name = "report.html"
    form_class = CameraReportForm
    success_url = reverse_lazy("report-success")

    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return HttpResponse("Too many submissions. Please try again later.", status=429)
        return super().post(request, *args, **kwargs)

    def get_template_names(self):
        ua = self.request.META.get("HTTP_USER_AGENT", "").lower()
        if any(kw in ua for kw in _MOBILE_UA_KEYWORDS):
            return ["report_mobile.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            init_lat = float(self.request.GET.get("lat", _NOLA_DEFAULT_LAT))
            init_lng = float(self.request.GET.get("lng", _NOLA_DEFAULT_LNG))
            init_zoom = int(self.request.GET.get("zoom", _NOLA_DEFAULT_ZOOM))
        except (TypeError, ValueError):
            init_lat, init_lng, init_zoom = _NOLA_DEFAULT_LAT, _NOLA_DEFAULT_LNG, _NOLA_DEFAULT_ZOOM
        context["init_lat"] = max(-90.0, min(90.0, init_lat))
        context["init_lng"] = max(-180.0, min(180.0, init_lng))
        context["init_zoom"] = max(1, min(19, init_zoom))
        context["pinned"] = self.request.GET.get("pinned") == "1"
        return context

    def form_valid(self, form):
        camera = form.save()
        type_map = [
            ("image_close_up",          CameraImage.PhotoType.CLOSE_UP),
            ("image_surrounding",       CameraImage.PhotoType.SURROUNDING),
            ("image_project_nola_sign", CameraImage.PhotoType.PROJECT_NOLA_SIGN),
        ]
        for field_name, photo_type in type_map:
            img = form.cleaned_data.get(field_name)
            if img:
                CameraImage.objects.create(
                    camera=camera,
                    image=img,
                    photo_type=photo_type,
                    status=CameraImage.Status.PENDING,
                    proposed_by=form.cleaned_data.get("reported_by", ""),
                )
        return super().form_valid(form)


class ReportSuccessView(TemplateView):
    """
    Success page after camera submission.
    """

    template_name = "report_success.html"


@method_decorator(ratelimit(key="ip", rate="20/h", method="POST", block=False), name="post")
class ProposePhotoView(FormView):
    """
    Public form to propose a photo for an existing vetted camera.
    """

    template_name = "propose_photo.html"
    form_class = PhotoProposalForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.camera = get_object_or_404(Camera, pk=kwargs["camera_id"], status=Camera.Status.VETTED)

    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return HttpResponse("Too many submissions. Please try again later.", status=429)
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("propose-photo-success", kwargs={"camera_id": self.camera.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["camera"] = self.camera
        return context

    def form_valid(self, form):
        form.save(camera=self.camera)
        return super().form_valid(form)


class ProposePhotoSuccessView(TemplateView):
    """
    Success page after photo proposal submission.
    """

    template_name = "propose_photo_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["camera"] = get_object_or_404(
            Camera, pk=kwargs["camera_id"], status=Camera.Status.VETTED
        )
        return context


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=False), name="post")
class ProposeCorrectionView(FormView):
    """
    Public form to propose a correction for an existing vetted camera.
    """

    template_name = "propose_correction.html"
    form_class = CorrectionProposalForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.camera = get_object_or_404(Camera, pk=kwargs["camera_id"], status=Camera.Status.VETTED)

    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return HttpResponse("Too many submissions. Please try again later.", status=429)
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("propose-correction-success", kwargs={"camera_id": self.camera.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["camera"] = self.camera
        return context

    def form_valid(self, form):
        form.save(camera=self.camera)
        return super().form_valid(form)


class ProposeCorrectionSuccessView(TemplateView):
    """
    Success page after correction proposal submission.
    """

    template_name = "propose_correction_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["camera"] = get_object_or_404(
            Camera, pk=kwargs["camera_id"], status=Camera.Status.VETTED
        )
        return context
