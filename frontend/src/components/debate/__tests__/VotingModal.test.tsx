import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VotingModal } from '../VotingModal'

describe('VotingModal', () => {
  it('renders as an accessible dialog with the prompt', () => {
    render(<VotingModal onVote={() => {}} />)

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByText('Audience Vote')).toBeInTheDocument()
  })

  it('calls onVote with the side the user picks', async () => {
    const onVote = vi.fn()
    render(<VotingModal onVote={onVote} />)

    await userEvent.click(screen.getByRole('button', { name: /pro is winning/i }))
    await userEvent.click(screen.getByRole('button', { name: /con is winning/i }))
    await userEvent.click(screen.getByRole('button', { name: /it's a tie/i }))

    expect(onVote.mock.calls.map((call) => call[0])).toEqual(['PRO', 'CON', 'TIE'])
  })
})
