from datetime import datetime
from uuid import uuid4
from app.schemas.fire import FireEventDetail, FireStatus

def reproduce():
    # Data mimicking what is stored in DB
    slides_data = [
        {
            "type": "swir",
            "thumbnail_url": "https://example.com/swir.png",
            "satellite_image_id": "123",
            "generated_at": datetime.now().isoformat()
        },
        {
            "type": "rgb",
            "thumbnail_url": "https://example.com/rgb.png",
            "satellite_image_id": "456",
            "generated_at": datetime.now().isoformat()
        }
    ]

    try:
        detail = FireEventDetail(
            id=uuid4(),
            start_date=datetime.now(),
            end_date=datetime.now(),
            total_detections=10,
            is_significant=False,
            has_satellite_imagery=True,
            has_climate_data=False,
            created_at=datetime.now(),
            slides_data=slides_data # This should fail
        )
        print("Success!")
    except Exception as e:
        print(f"Caught expected error: {e}")

if __name__ == "__main__":
    reproduce()
