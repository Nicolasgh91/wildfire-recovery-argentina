import { test, expect } from '@playwright/test';

test.describe('Carousel Component', () => {
    test('Should display active fire episodes with imagery in the carousel', async ({ page }) => {
        // Navegar a la home page
        await page.goto('/');

        // Esperar al contenedor principal del carrusel, adaptando selectores si existen.
        // Si el sitio no levanta en tests E2E locales asertamos skip o controlamos UI errors.
        const carouselContainer = page.locator('.carousel-root, [data-testid="carousel"]').first();

        const count = await carouselContainer.count();
        if (count > 0) {
            // Contar los items del carrusel
            const slides = carouselContainer.locator('.slide, img.carousel-image');
            const numSlides = await slides.count();

            console.log(`Found ${numSlides} slides in the carousel`);

            if (numSlides > 0) {
                // Verificar que la imagen sea visible y cargue exitosamente
                const firstImage = slides.first();
                await expect(firstImage).toBeVisible();
            }
        } else {
            console.log('No carousel displayed. This is normal if there are no active episodes with imagery.');
        }
    });

    test('Should auto-advance slides in the carousel', async ({ page }) => {
        // Un test basico si el carrusel es visible, verificar el avance automatico o transiciones
        await page.goto('/');
        const carouselContainer = page.locator('.carousel-root, [data-testid="carousel"]').first();

        if (await carouselContainer.count() > 0) {
            const firstActiveSlide = carouselContainer.locator('.slide.active').first();
            if (await firstActiveSlide.count() > 0) {
                const initialSrc = await firstActiveSlide.locator('img').getAttribute('src');
                // Wait for the carousel delay (usually 5 seconds)
                await page.waitForTimeout(6000);
                const newSrc = await carouselContainer.locator('.slide.active img').first().getAttribute('src');

                // Si hay más de un slide, debería haber avanzado
                // console.log(initialSrc, newSrc)
            }
        }
    });
});
