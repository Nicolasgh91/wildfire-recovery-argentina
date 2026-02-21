export {}

declare global {
  namespace Cypress {
    interface Chainable {
      getBounds(selector: string): Chainable<DOMRect>
      expectWithinBounds(parentSelector: string, childSelector: string, tolerance?: number): Chainable<void>
    }
  }
}

Cypress.Commands.add('getBounds', (selector: string) => {
  return cy.get(selector).then(($el) => {
    const rect = $el[0].getBoundingClientRect()
    return rect
  })
})

Cypress.Commands.add('expectWithinBounds', (parentSelector: string, childSelector: string, tolerance = 2) => {
  cy.getBounds(parentSelector).then((parent) => {
    cy.getBounds(childSelector).then((child) => {
      expect(child.left).to.be.gte(parent.left - tolerance)
      expect(child.top).to.be.gte(parent.top - tolerance)
      expect(child.right).to.be.lte(parent.right + tolerance)
      expect(child.bottom).to.be.lte(parent.bottom + tolerance)
    })
  })
})
