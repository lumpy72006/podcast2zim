describe('Podcast home page', () => {
  beforeEach(() => {
    cy.intercept('GET', '**/podcast.json', { fixture: 'podcast/podcast.json' })
    cy.intercept('GET', '**/config.json', { fixture: 'podcast/config.json' })
    cy.visit('/')
  })

  it('shows the podcast title and episode list', () => {
    cy.contains('h1', 'Uncharted with Hannah Fry').should('be.visible')
    cy.contains('20. The Confidence Trick').should('be.visible')
    cy.contains('1. The Returning Soldier').should('be.visible')
  })

  it('filters episodes by the search box', () => {
    cy.get('input[placeholder="Search episodes"]').type('Confidence')
    cy.contains('20. The Confidence Trick').should('be.visible')
    cy.contains('1. The Returning Soldier').should('not.exist')
  })
})
