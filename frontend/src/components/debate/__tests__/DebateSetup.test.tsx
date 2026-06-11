import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DebateSetup } from '../DebateSetup'
import { useDebateStore } from '../../../stores/debateStore'

beforeEach(() => {
  useDebateStore.getState().reset()
  // DebateSetup fetches the available styles on mount.
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ styles: [{ name: 'passionate', description: 'persuasive' }] }),
    })
  )
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DebateSetup', () => {
  it('renders the heading and disables Start until a topic is entered', () => {
    render(<DebateSetup onStart={vi.fn()} isLoading={false} />)

    expect(screen.getByText('Multi-Agent Debate System')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start debate/i })).toBeDisabled()
  })

  it('calls onStart with the topic and the selected styles', async () => {
    const onStart = vi.fn()
    render(<DebateSetup onStart={onStart} isLoading={false} />)

    await userEvent.type(
      screen.getByPlaceholderText(/should artificial intelligence/i),
      'Cats vs dogs'
    )
    await userEvent.click(screen.getByRole('button', { name: /start debate/i }))

    expect(onStart).toHaveBeenCalledWith('Cats vs dogs', 'passionate', 'passionate')
  })
})
