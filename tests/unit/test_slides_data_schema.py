from app.schemas.fire import SlideItem
from pydantic import ValidationError
import pytest

def test_slide_item_valid():
    slide = SlideItem(
        type="image",
        title="True Color",
        url="https://storage.example.com/slide.jpg",
        description="A beautiful satellite image",
        date="2026-02-24"
    )
    assert slide.type == "image"
    assert slide.title == "True Color"
    assert slide.url == "https://storage.example.com/slide.jpg"
    assert slide.description == "A beautiful satellite image"
    assert slide.date == "2026-02-24"

def test_slide_item_missing_required():
    with pytest.raises(ValidationError) as exc_info:
        SlideItem(type="image") # missing title and url
    
    assert "title" in str(exc_info.value)
    assert "url" in str(exc_info.value)

def test_slide_item_optional_fields():
    slide = SlideItem(
        type="image",
        title="True Color",
        url="https://storage.example.com/slide.jpg"
    )
    assert slide.description is None
    assert slide.date is None
