const viewports: Array<[string, number, number]> = [
  ['desktop', 1280, 800],
  ['tablet', 768, 1024],
  ['mobile', 375, 667],
]

describe('Fire detail map popup initial render', () => {
  beforeEach(() => {
    cy.fixture('fire-detail.json').then((payload) => {
      cy.intercept('GET', '**/api/v1/fires/test-fire-id', payload)
      cy.intercept('GET', '**/api/v1/quality/**', { statusCode: 200, body: {} })
    })
  })

  viewports.forEach(([label, width, height]) => {
    it(`/fires/:id keeps opened detail popup visible on ${label}`, () => {
      cy.viewport(width, height)
      cy.visit('/fires/test-fire-id')

      cy.get('.leaflet-popup', { timeout: 20000 }).should('be.visible')
      cy.expectWithinBounds('.leaflet-container', '.leaflet-popup')

      if (label !== 'desktop') {
        cy.get('.leaflet-popup-content').should('be.visible')
      }
    })
  })
})
