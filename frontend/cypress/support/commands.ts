declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Assert that the subject element's bounding box is fully contained
       * within a parent element's bounding box (with optional tolerance in px).
       */
      isContainedWithin(parentSelector: string, tolerance?: number): Chainable<JQuery<HTMLElement>>
    }
  }
}

Cypress.Commands.add(
  'isContainedWithin',
  { prevSubject: 'element' },
  (subject: JQuery<HTMLElement>, parentSelector: string, tolerance = 2) => {
    cy.get(parentSelector).then(($parent) => {
      const parentRect = $parent[0].getBoundingClientRect()
      const childRect = subject[0].getBoundingClientRect()

      expect(childRect.top, 'popup top >= container top').to.be.at.least(
        parentRect.top - tolerance,
      )
      expect(childRect.left, 'popup left >= container left').to.be.at.least(
        parentRect.left - tolerance,
      )
      expect(childRect.bottom, 'popup bottom <= container bottom').to.be.at.most(
        parentRect.bottom + tolerance,
      )
      expect(childRect.right, 'popup right <= container right').to.be.at.most(
        parentRect.right + tolerance,
      )
    })
  },
)

export {}
