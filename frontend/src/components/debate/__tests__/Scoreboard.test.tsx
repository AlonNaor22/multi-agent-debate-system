import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Scoreboard } from '../Scoreboard'
import type { DebateScores } from '../../../types/debate'

const scores: DebateScores = {
  pro_arguments: [
    { summary: 'Pro point one', score: 8, reason: 'well argued' },
    { summary: 'Pro point two', score: 6, reason: 'decent' },
  ],
  con_arguments: [{ summary: 'Con point one', score: 4, reason: 'weak' }],
  pro_average: 7,
  con_average: 4,
  winner: 'PRO',
  strongest_argument: 'Pro point one is compelling',
  weakest_argument: 'Con point one is thin',
}

describe('Scoreboard', () => {
  it('renders each argument, the winner, and the strongest/weakest picks', () => {
    render(<Scoreboard scores={scores} />)

    expect(screen.getByText('Argument Scores')).toBeInTheDocument()
    expect(screen.getByText('PRO wins')).toBeInTheDocument()

    expect(screen.getByText('Pro point one')).toBeInTheDocument()
    expect(screen.getByText('Pro point two')).toBeInTheDocument()
    expect(screen.getByText('Con point one')).toBeInTheDocument()

    expect(screen.getByText('Pro point one is compelling')).toBeInTheDocument()
    expect(screen.getByText('Con point one is thin')).toBeInTheDocument()
  })

  it('shows the tie label when the debate is tied', () => {
    render(<Scoreboard scores={{ ...scores, winner: 'TIE' }} />)
    expect(screen.getByText("It's a tie")).toBeInTheDocument()
  })

  it('shows an empty state for a side with no scored arguments', () => {
    render(<Scoreboard scores={{ ...scores, con_arguments: [] }} />)
    expect(screen.getByText('No arguments scored.')).toBeInTheDocument()
  })
})
