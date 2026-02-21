const viewports: Array<[string, number, number]> = [
  ['desktop', 1280, 800],
  ['tablet', 768, 1024],
  ['mobile', 375, 667],
]

describe('Fire popup containment', () => {
  viewports.forEach(([label, width, height]) => {
    describe(`${label} (${width}x${height})`, () => {
      beforeEach(() => {
        cy.viewport(width, height)
      })

      describe('/map — popup visible after marker click', () => {
        it('opens a popup fully contained within the map', () => {
          cy.visit('/map')

          // Wait for markers to render
          cy.get('.custom-fire-marker', { timeout: 20000 }).should('have.length.at.least', 1)

          // Click the first marker
          cy.get('.custom-fire-marker').first().click({ force: true })

          // Popup should appear
          cy.get('.fire-popup', { timeout: 5000 }).should('be.visible')

          // Popup must be contained within the map container
          cy.get('.fire-popup').isContainedWithin('.leaflet-container')

          // CTA button should be visible
          cy.get('.fire-popup').find('button').should('be.visible')
        })
      })

      describe('/fires/:id — initial render correct', () => {
        it('shows popup fully contained within the map on load', () => {
          // Use the map page to discover a real fire ID, then navigate to its detail
          cy.visit('/map')
          cy.get('.custom-fire-marker', { timeout: 20000 }).should('have.length.at.least', 1)

          // Click a marker and capture the detail link
          cy.get('.custom-fire-marker').first().click({ force: true })
          cy.get('.fire-popup', { timeout: 5000 }).should('be.visible')
          cy.get('.fire-popup').find('button').first().click()

          // Now on /fires/:id
          cy.url().should('match', /\/fires\/.+/)

          // Wait for the map and popup to render
          cy.get('.leaflet-container', { timeout: 15000 }).should('be.visible')
          cy.get('.fire-popup', { timeout: 10000 }).should('be.visible')

          // Popup must be contained within the map
          cy.get('.fire-popup').isContainedWithin('.leaflet-container')
        })
      })
    })
  })
})
