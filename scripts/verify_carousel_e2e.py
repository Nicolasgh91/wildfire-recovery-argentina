#!/usr/bin/env python
"""
E2E Script to verify the carousel using Playwright.
Usage: 
    pip install playwright
    playwright install chromium
    python scripts/verify_carousel_e2e.py
"""
import sys
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_carousel")

def main():
    url = "http://localhost:3000"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        logger.info(f"Navigating to {url}")
        try:
            response = page.goto(url, wait_until="networkidle")
            if not response or not response.ok:
                logger.error(f"Failed to load page: HTTP {response.status if response else 'Unknown'}")
            
            # Wait for carousel component
            # Assuming the frontend uses a specific class for the carousel container
            logger.info("Waiting for carousel container to appear...")
            carousel = page.wait_for_selector(".carousel-root, [data-testid='carousel']", timeout=15000)
            
            if carousel:
                logger.info("Carousel component found. Checking for slides...")
                # Note: Adjust these selectors based on the actual implementation
                slides_count = page.locator("img[alt*='satellite'], .slide, .carousel-image").count()
                logger.info(f"Found {slides_count} slides in the carousel.")
                
                if slides_count == 0:
                    logger.warning("No slides found. This could be due to no active fire episodes with imagery.")
                else:
                    logger.info("SUCCESS: Carousel verified and contains slides.")
            else:
                logger.error("FAILED: Carousel component not found on the page.")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"FAILED: Error verifying carousel: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
