import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PastDebates } from '../PastDebates'

const summary = {
  id: 'abc',
  topic: 'Cats vs dogs',
  pro_style: 'passionate',
  con_style: 'academic',
  winner: 'PRO',
  message_count: 3,
  created_at: '2026-01-01T10:00:00',
  completed_at: '2026-01-01T10:05:00',
}

const detail = {
  ...summary,
  transcript: [
    { speaker: 'MODERATOR', content: 'Welcome to the debate', phase: 'introduction' },
    { speaker: 'PRO', content: 'Cats are independent', phase: 'opening_pro' },
  ],
  argument_scores: null,
}

function mockFetch(handler: (url: string) => { ok: boolean; body: unknown }) {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    const { ok, body } = handler(url)
    return Promise.resolve({ ok, json: async () => body })
  }))
}

beforeEach(() => {
  mockFetch((url) => {
    if (url === '/api/debates') return { ok: true, body: [summary] }
    if (url === '/api/debates/abc') return { ok: true, body: detail }
    return { ok: false, body: {} }
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('PastDebates', () => {
  it('lists saved debates and opens a detail view with the transcript', async () => {
    render(<PastDebates onBack={() => {}} />)

    // List renders the saved debate's topic.
    expect(await screen.findByText('Cats vs dogs')).toBeInTheDocument()

    // Clicking it loads and renders the full transcript.
    await userEvent.click(screen.getByText('Cats vs dogs'))
    expect(await screen.findByText('Cats are independent')).toBeInTheDocument()
    expect(screen.getByText('Welcome to the debate')).toBeInTheDocument()
  })

  it('calls onBack when "New Debate" is clicked', async () => {
    const onBack = vi.fn()
    render(<PastDebates onBack={onBack} />)
    await screen.findByText('Cats vs dogs')

    await userEvent.click(screen.getByRole('button', { name: /new debate/i }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('shows an empty state when there are no past debates', async () => {
    mockFetch(() => ({ ok: true, body: [] }))
    render(<PastDebates onBack={() => {}} />)
    expect(await screen.findByText(/no debates yet/i)).toBeInTheDocument()
  })
})
