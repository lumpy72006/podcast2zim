describe('Episode view page', () => {
  beforeEach(() => {
    cy.intercept('GET', '**/podcast.json', { fixture: 'podcast/podcast.json' })
    cy.intercept('GET', '**/config.json', { fixture: 'podcast/config.json' })
    cy.intercept('GET', '**/episodes/ep-20.json', { fixture: 'podcast/episode.json' })
    cy.visit('/#/episode/ep-20')
  })

  it('shows the episode title and an audio player', () => {
    cy.contains('h1', '20. The Confidence Trick').should('be.visible')
    cy.get('audio').should('have.attr', 'src').and('include', 'audios/ep-20/audio.mp3')
  })
})
