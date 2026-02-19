/**
 * Global Branding Configuration
 * 
 * This file serves as the single source of truth for the application's branding.
 * To rebrand the application, modify the constants below.
 */

export const BRAND = {
    /**
     * The visible name of the application.
     * Displayed in the Navbar, Page Titles, and Footer.
     */
    name: "Vestigia",

    /**
     * The application's tagline or short description.
     */
    tagline: "Wildfire Recovery & Monitoring",

    /**
     * URLs for the application logos.
     * Ideally these should be SVGs for best scaling.
     */
    logos: {
        // For now using placeholders or existing assets logic
        // You can update these paths when new assets are available
        light: "/assets/branding/logo-light.svg",
        dark: "/assets/branding/logo-dark.svg",
        // Fallback to text if logo is missing? Handled in component.
    },

    /**
     * Paths to favicon and other meta images.
     */
    assets: {
        favicon: "/favicon.ico",
        ogImage: "/assets/branding/og-image.jpg",
    },

    /**
     * External links related to the brand.
     */
    links: {
        publicUrl: "https://forestguard.freedynamicdns.org", // Keeping domain for now
        github: "https://github.com/Nicolasgh91/wildfire-recovery-argentina", // Assuming this stays
    },

    /**
     * Internal identifiers (do not change unless you know what you are doing)
     */
    slug: "vestigia"
} as const;
