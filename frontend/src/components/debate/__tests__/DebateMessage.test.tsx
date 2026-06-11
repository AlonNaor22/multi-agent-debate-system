import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DebateMessage } from '../DebateMessage'

// DebateMessage renders through the shared SpeakerBubble, so these also cover it.
describe('DebateMessage', () => {
  it('renders the speaker badge, content, and the optional turn label', () => {
    render(
      <DebateMessage
        message={{
          speaker: 'PRO',
          content: 'My opening argument',
          label: 'Opening Statement',
          phase: 'opening_pro',
        }}
      />
    )

    expect(screen.getByText('PRO')).toBeInTheDocument()
    expect(screen.getByText('My opening argument')).toBeInTheDocument()
    expect(screen.getByText('Opening Statement')).toBeInTheDocument()
  })

  it('renders a centered speaker that has no label', () => {
    render(
      <DebateMessage message={{ speaker: 'JUDGE', content: 'My verdict', phase: 'verdict' }} />
    )

    expect(screen.getByText('JUDGE')).toBeInTheDocument()
    expect(screen.getByText('My verdict')).toBeInTheDocument()
  })
})
