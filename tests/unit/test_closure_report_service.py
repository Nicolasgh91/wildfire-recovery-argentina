from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from geoalchemy2.elements import WKTElement

from app.models.episode import FireEpisode, FireEpisodeEvent
from app.models.fire import FireEvent
from app.services.closure_report_service import ClosureFireRow, ClosureReportService
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
    def __init__(self):
        self._counter = 0

    def authenticate(self):
        return True

    def get_sentinel_collection(self, bbox, start_date, end_date, max_cloud_cover=20):
        return {"bbox": bbox, "start": start_date, "end": end_date}

    def get_best_image(
        self,
        collection,
        target_date=None,
        prefer_low_cloud=True,
        max_cloud_cover=None,
    ):
        self._counter += 1
        if self._counter == 1:
            return DummyImage("PRE-1")
        return DummyImage("POST-1")

    def get_image_metadata(self, image):
        if image.image_id == "PRE-1":
            return DummyMetadata(
                image_id=image.image_id,
                acquisition_date=date.today() - timedelta(days=10),
                cloud_cover_percent=12.0,
            )
        return DummyMetadata(
            image_id=image.image_id,
            acquisition_date=date.today() - timedelta(days=2),
            cloud_cover_percent=8.0,
        )

    def calculate_nbr(self, image, bbox):
        if image.image_id == "PRE-1":
            return {"mean": 0.5}
        return {"mean": 0.1}

    def apply_cloud_mask(self, image):
        return image

    def download_thumbnail(
        self, image, bbox, vis_type="RGB", dimensions=256, format="png"
    ):
        return f"{image.image_id}-{vis_type}".encode("utf-8")

    def download_dnbr_thumbnail(
        self, pre_image, post_image, bbox, dimensions=256, format="png"
    ):
        return b"dnbr-bytes"


class DummyStorage:
    def upload_bytes(self, data, key, bucket=None, content_type=None, metadata=None):
        return UploadResult(
            success=True,
            key=key,
            url=f"https://storage.local/{key}",
            size_bytes=len(data),
            content_hash="hash",
        )


def test_closure_report_updates_episode_and_fire(db_session, monkeypatch):
    fire_id = uuid4()
    start_date = datetime.now(timezone.utc) - timedelta(days=12)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)

    fire = FireEvent(
        id=fire_id,
        start_date=start_date,
        end_date=end_date,
        total_detections=1,
        is_significant=True,
        province="Test",
        status="extinct",
        extinct_at=end_date,
        estimated_area_hectares=15,
        centroid=WKTElement("POINT(0 0)", srid=4326),
    )

    episode = FireEpisode(
        id=uuid4(),
        start_date=start_date,
        end_date=end_date,
        status="extinct",
    )

    link = FireEpisodeEvent(episode_id=episode.id, event_id=fire.id)

    db_session.add_all([fire, episode, link])
    db_session.commit()

    service = ClosureReportService(
        db_session,
        gee_service=DummyGEE(),
        storage_service=DummyStorage(),
    )

    monkeypatch.setattr(
        ClosureReportService,
        "_fetch_candidates",
        lambda self, limit, min_area, max_retry_days: [
            ClosureFireRow(
                id=str(fire.id),
                lat=0.0,
                lon=0.0,
                start_date=start_date,
                extinct_at=end_date,
                estimated_area_hectares=15.0,
            )
        ],
    )

    result = service.run(max_fires=1)

    db_session.expire_all()
    refreshed_fire = db_session.query(FireEvent).filter(FireEvent.id == fire.id).first()
    refreshed_episode = (
        db_session.query(FireEpisode).filter(FireEpisode.id == episode.id).first()
    )

    assert result["updated"] == 1
    assert refreshed_fire is not None
    assert refreshed_fire.has_historic_report is True
    assert refreshed_episode is not None
    assert refreshed_episode.severity_class == "moderate_low"
    assert refreshed_episode.dnbr_severity is not None
