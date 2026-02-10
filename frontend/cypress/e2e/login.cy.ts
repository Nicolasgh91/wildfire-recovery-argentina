// cypress/e2e/login.cy.ts
// E2E tests for Login Page

describe('Login Page', () => {
    beforeEach(() => {
        cy.visit('/login')
    })

    it('should display the hero title with correct text', () => {
        cy.get('[data-testid="hero-title"]')
            .should('be.visible')
            .and('contain.text', 'La huella del fuego')
    })

    it('should display all form elements', () => {
        cy.get('[data-testid="login-form"]').should('be.visible')
        cy.get('[data-testid="login-email"]').should('be.visible')
        cy.get('[data-testid="login-password"]').should('be.visible')
        cy.get('[data-testid="login-google"]').should('be.visible')
        cy.get('[data-testid="login-submit"]').should('be.visible')
        cy.get('[data-testid="login-guest"]').should('be.visible')
    })

    it('should allow typing in email and password fields', () => {
        cy.get('[data-testid="login-email"]')
            .type('test@example.com')
            .should('have.value', 'test@example.com')

        cy.get('[data-testid="login-password"]')
            .type('password123')
            .should('have.value', 'password123')
    })

    it('should show error when submitting empty form', () => {
        cy.get('[data-testid="login-submit"]').click()
        cy.get('[data-testid="login-error"]')
            .should('be.visible')
            .and('have.attr', 'role', 'alert')
    })

    it('should navigate to home when clicking guest access', () => {
        cy.get('[data-testid="login-guest"]').click()
        cy.url().should('eq', Cypress.config('baseUrl') + '/')
    })

    it('should have correct tab order for keyboard navigation', () => {
        // Focus should move through form elements in order
        cy.get('[data-testid="login-email"]').focus().should('be.focused')
        cy.realPress('Tab')
        cy.get('[data-testid="login-password"]').should('be.focused')
        cy.realPress('Tab')
        cy.get('[data-testid="login-google"]').should('be.focused')
        cy.realPress('Tab')
        cy.get('[data-testid="login-submit"]').should('be.focused')
    })
})
