import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DebateProgress } from '../DebateProgress'

const ACTIVE_CLASS = 'bg-blue-500'
const COMPLETED_CLASS = 'bg-green-100'

describe('DebateProgress', () => {
  it('renders all six display steps', () => {
    render(<DebateProgress phase="rebuttal" />)

    for (const label of ['Introduction', 'Openings', 'Rebuttals', 'Closings', 'Verdict', 'Scoring']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })

  it('marks no step active before the debate has a phase', () => {
    render(<DebateProgress phase={null} />)
    for (const label of ['Introduction', 'Openings', 'Rebuttals', 'Closings', 'Verdict', 'Scoring']) {
      expect(screen.getByText(label).className).not.toContain(ACTIVE_CLASS)
    }
  })

  it('highlights the step the current phase belongs to', () => {
    render(<DebateProgress phase="opening_con" />)
    expect(screen.getByText('Openings').className).toContain(ACTIVE_CLASS)
    expect(screen.getByText('Introduction').className).toContain(COMPLETED_CLASS)
    expect(screen.getByText('Rebuttals').className).not.toContain(ACTIVE_CLASS)
  })

  it('keeps Scoring active while the judge computes the scoreboard', () => {
    render(<DebateProgress phase="scoring" />)
    expect(screen.getByText('Scoring').className).toContain(ACTIVE_CLASS)
    expect(screen.getByText('Verdict').className).toContain(COMPLETED_CLASS)
  })

  it('shows every step as completed when the debate is finished', () => {
    render(<DebateProgress phase="finished" />)
    for (const label of ['Introduction', 'Openings', 'Rebuttals', 'Closings', 'Verdict', 'Scoring']) {
      const className = screen.getByText(label).className
      expect(className).toContain(COMPLETED_CLASS)
      expect(className).not.toContain(ACTIVE_CLASS)
    }
  })
})
