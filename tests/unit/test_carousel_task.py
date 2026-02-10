from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from geoalchemy2.elements import WKTElement

import app.services.imagery_service as imagery_service_module
from app.models.evidence import SatelliteImage
from app.models.fire import FireEvent
from app.services.gee_service import GEEImageNotFoundError
from app.services.imagery_service import ImageryService
from app.services.storage_service import UploadResult


class DummyImage:
    def __init__(self, image_id: str):
        self.image_id = image_id


@dataclass
class DummyMetadata:
    image_id: str
    acquisition_date: date
    cloud_cover_percent: float
    satellite: str = "Sentinel-2"
    tile_id: str = "T20HNH"
    sun_elevation: float = 45.0
    processing_level: str = "L2A"


class DummyGEE:
    def __init__(self, image_id: str = "IMG-1"):
        self._image = DummyImage(image_id)
        self._last_cloud = None

    def authenticate(self):
        return True

    def get_sentinel_collection(self, bbox, start_date, end_date, max_cloud_cover=20):
        self._last_cloud = max_cloud_cover
        return {"bbox": bbox, "start": start_date, "end": end_date}

    def get_best_image(self, collection, target_date=None, prefer_low_cloud=True):
        if self._last_cloud is not None and float(self._last_cloud) < 30:
            raise GEEImageNotFoundError("No image for threshold")
        return self._image

    def get_image_metadata(self, image):
        return DummyMetadata(
            image_id=image.image_id,
            acquisition_date=date.today(),
            cloud_cover_percent=12.5,
        )

    def download_thumbnail(
        self, image, bbox, vis_type="RGB", dimensions=256, format="png"
    ):
        return f"{vis_type}-bytes".encode("utf-8")


class DummyStorage:
    def upload_bytes(self, data, key, bucket=None, content_type=None, metadata=None):
        return UploadResult(
            success=True,
            key=key,
            url=f"https://storage.local/{key}",
            size_bytes=len(data),
            content_hash="hash",
        )


def _make_fire():
    start_date = datetime.now(timezone.utc) - timedelta(days=1)
    return FireEvent(
        id=uuid4(),
        start_date=start_date,
        end_date=start_date + timedelta(hours=2),
        total_detections=1,
        is_significant=False,
        province="Test",
        status="active",
        centroid=WKTElement("POINT(0 0)", srid=4326),
    )


def test_carousel_updates_slides_and_images(db_session, monkeypatch):
    fire = _make_fire()
    db_session.add(fire)
    db_session.commit()

    monkeypatch.setattr(
        imagery_service_module, "apply_watermark", lambda *args, **kwargs: args[0]
    )
    monkeypatch.setattr(
        ImageryService,
        "_fetch_priority_fires",
        lambda self, limit, weights: [
            imagery_service_module.CarouselFireRow(
                id=str(fire.id),
                lat=0.0,
                lon=0.0,
                start_date=fire.start_date,
                last_gee_image_id=None,
                max_frp=None,
                estimated_area_hectares=None,
                h3_index=None,
                priority_score=1.0,
            )
        ],
    )

    service = ImageryService(
        db_session,
        gee_service=DummyGEE(),
        storage_service=DummyStorage(),
    )

    result = service.run_carousel(max_fires=1, force_refresh=True)

    db_session.expire_all()
    refreshed = db_session.query(FireEvent).filter(FireEvent.id == fire.id).first()
    assert refreshed is not None
    assert refreshed.last_gee_image_id == "IMG-1"
    assert refreshed.slides_data
    assert len(refreshed.slides_data) == 3
    assert result["updated"] == 1

    count = (
        db_session.query(SatelliteImage)
        .filter(
            SatelliteImage.fire_event_id == fire.id,
            SatelliteImage.image_type == "carousel",
        )
        .count()
    )
    assert count == 3
