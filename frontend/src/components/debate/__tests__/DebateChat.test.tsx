import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DebateChat } from '../DebateChat'
import { useDebateStore } from '../../../stores/debateStore'
import { strings } from '../../../constants/strings'

beforeEach(() => {
  useDebateStore.getState().reset()
})

describe('DebateChat – mid-debate error recovery', () => {
  it('surfaces the error message and exposes the New Debate reset action', async () => {
    // A mid-debate error: the debate is still "active" (not finished) but failed.
    useDebateStore.setState({ isDebating: true, phase: 'rebuttal', topic: 'AI safety' })
    useDebateStore.getState().setError('The AI service is temporarily unavailable.')

    const onNewDebate = vi.fn()
    render(<DebateChat onVote={() => {}} onNewDebate={onNewDebate} />)

    // The message is visible (in an alert region).
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent(strings.chat.errorTitle)
    expect(alert).toHaveTextContent('The AI service is temporarily unavailable.')

    // The way out is offered even though the debate never reached 'finished'.
    const newDebate = screen.getByRole('button', { name: strings.chat.newDebate })
    await userEvent.click(newDebate)
    expect(onNewDebate).toHaveBeenCalledTimes(1)
  })

  it('clears the streaming indicator and vote modal when an error occurs', () => {
    // Set up a debate that is streaming and awaiting a vote, then error out.
    useDebateStore.setState({ isDebating: true, phase: 'rebuttal', topic: 'AI safety' })
    useDebateStore.getState().startStreaming('PRO')
    useDebateStore.getState().setIsWaitingForVote(true)
    useDebateStore.getState().setError('boom')

    render(<DebateChat onVote={() => {}} onNewDebate={() => {}} />)

    // No dangling "typing…" indicator and no voting dialog left on screen.
    expect(screen.queryByText(strings.chat.typing)).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows no error banner and no footer button during a normal in-flight debate', () => {
    useDebateStore.setState({ isDebating: true, phase: 'rebuttal', topic: 'AI safety' })

    render(<DebateChat onVote={() => {}} onNewDebate={() => {}} />)

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: strings.chat.newDebate })
    ).not.toBeInTheDocument()
  })
})
