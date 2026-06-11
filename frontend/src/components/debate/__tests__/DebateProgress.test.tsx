import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DebateProgress } from '../DebateProgress'

describe('DebateProgress', () => {
  it('renders all six display steps', () => {
    render(<DebateProgress phase="rebuttal" />)

    for (const label of ['Introduction', 'Openings', 'Rebuttals', 'Closings', 'Verdict', 'Scoring']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })

  it('renders safely before the debate has a phase', () => {
    render(<DebateProgress phase={null} />)
    expect(screen.getByText('Introduction')).toBeInTheDocument()
  })
})
