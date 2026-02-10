describe('Fire detail flow', () => {
  before(function () {
    cy.env(['TEST_USER_EMAIL', 'TEST_USER_PASSWORD', 'API_KEY']).then(function (env) {
      if (!env.TEST_USER_EMAIL || !env.TEST_USER_PASSWORD || !env.API_KEY) {
        this.skip()
      }
    })
  })

  it('loads fire detail after login', () => {
    cy.env(['TEST_USER_EMAIL', 'TEST_USER_PASSWORD', 'API_KEY', 'API_BASE_URL']).then((env) => {
      const email = env.TEST_USER_EMAIL
      const password = env.TEST_USER_PASSWORD
      const apiKey = env.API_KEY
      const apiBase = env.API_BASE_URL

      cy.request({
        url: `${apiBase}/fires`,
        qs: { page: 1, page_size: 1 },
        headers: { 'X-API-Key': apiKey },
      }).then((response) => {
        expect(response.status).to.eq(200)
        const fireId = response.body?.fires?.[0]?.id
        expect(fireId, 'fire id').to.be.a('string')

        cy.visit('/login')
        cy.get('#email').clear().type(email)
        cy.get('#password').clear().type(password, { log: false })
        cy.get('button[type="submit"]').click()
        cy.url().should('not.include', '/login')

        cy.visit(`/fires/${fireId}`)
        cy.contains('Calidad de datos', { timeout: 15000 }).should('be.visible')
        cy.contains('Reportar Actividad Sospechosa').should('be.visible')
      })
    })
  })
})
