describe('Map regression', () => {
  const visitMap = () => {
    cy.visit('/map')
    cy.get('.leaflet-container', { timeout: 20000 }).should('be.visible')
  }

  it('loads map page without errors', () => {
    visitMap()
    cy.contains('Mapa Interactivo').should('be.visible')
  })

  it('displays fire markers on the map', () => {
    visitMap()
    cy.get('.custom-fire-marker', { timeout: 20000 }).should('have.length.greaterThan', 0)
  })

  it('clicking a marker shows the details link', () => {
    visitMap()
    cy.get('.custom-fire-marker').first().click({ force: true })
    cy.get('.leaflet-popup').should('be.visible')
    cy.contains('Ver Detalles').should('be.visible')
    cy.get('.leaflet-popup a[href^="/fires/"]').should('have.attr', 'href')
  })

  it('supports pan and zoom controls', () => {
    visitMap()
    cy.get('.leaflet-control-zoom-in').should('be.visible').click({ force: true })
    cy.get('.leaflet-control-zoom-out').should('be.visible').click({ force: true })

    cy.window()
      .its('__leafletMap')
      .should('exist')
      .then((map: any) => {
        const before = map.getCenter()

        return new Cypress.Promise<void>((resolve) => {
          map.once('moveend', () => {
            const after = map.getCenter()
            expect(after.lat).to.not.equal(before.lat)
            expect(after.lng).to.not.equal(before.lng)
            resolve()
          })

          map.panBy([120, 120], { animate: false })
        })
      })
  })

  it('renders on mobile viewport', () => {
    cy.viewport(375, 667)
    visitMap()
    cy.get('.leaflet-container').should('be.visible')
  })

  it.skip('can toggle satellite layer', () => {
    // Enable when LayerControl UI is implemented
  })

  it.skip('loads heatmap when enabled', () => {
    // Enable when Heatmap toggle UI is implemented
  })
})
