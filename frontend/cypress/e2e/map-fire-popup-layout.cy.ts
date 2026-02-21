const viewports: Array<[string, number, number]> = [
  ['desktop', 1280, 800],
  ['tablet', 768, 1024],
  ['mobile', 375, 667],
]

describe('Map popup layout', () => {
  viewports.forEach(([label, width, height]) => {
    it(`/map keeps popup inside map container on ${label}`, () => {
      cy.viewport(width, height)
      cy.visit('/map')

      cy.get('.leaflet-marker-icon', { timeout: 20000 }).first().click({ force: true })
      cy.get('.leaflet-popup').should('be.visible')

      cy.expectWithinBounds('.leaflet-container', '.leaflet-popup')
      cy.contains('button', /ver más detalles|view details/i).should('be.visible').and('not.be.disabled')
    })
  })
})
