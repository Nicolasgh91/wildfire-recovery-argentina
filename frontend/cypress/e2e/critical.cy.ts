describe('Critical flows', () => {
  const login = () => {
    cy.env(['TEST_USER_EMAIL', 'TEST_USER_PASSWORD']).then((env) => {
      cy.visit('/login')
      cy.get('[data-testid="email"]').clear().type(env.TEST_USER_EMAIL)
      cy.get('[data-testid="password"]').clear().type(env.TEST_USER_PASSWORD, { log: false })
      cy.get('[data-testid="submit"]').click()
      cy.url().should('not.include', '/login')
    })
  }

  before(function () {
    cy.env(['TEST_USER_EMAIL', 'TEST_USER_PASSWORD']).then((env) => {
      if (!env.TEST_USER_EMAIL || !env.TEST_USER_PASSWORD) {
        this.skip()
      }
    })
  })

  it('login flow', () => {
    login()
  })

  it('filter fires by province', () => {
    login()
    cy.visit('/fires/history')
    cy.get('[data-testid="province-filter"]').click()
    cy.contains('[role="option"]', 'Cordoba').click()
    cy.url().should('include', 'province=Cordoba')
  })

  it('submit audit', () => {
    login()
    cy.visit('/audit')
    cy.get('[data-testid="latitude"]').clear().type('-31.4')
    cy.get('[data-testid="longitude"]').clear().type('-64.2')
    cy.get('[data-testid="radius-meters"]').clear().type('500')
    cy.get('[data-testid="audit-submit"]').click()
    cy.get('[data-testid="audit-result"]', { timeout: 20000 }).should('be.visible')
  })
})
