import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { useDebateStore } from '../stores/debateStore'

// Mock child components so we don't render their full UI in unit tests
vi.mock('../components/debate', () => ({
  DebateSetup: ({ onStart }: { onStart: (t: string, p: string, c: string) => void }) => (
    <button
      data-testid="start-btn"
      onClick={() => onStart('AI safety', 'passionate', 'aggressive')}
    >
      Start
    </button>
  ),
  DebateChat: () => <div data-testid="chat">Chat</div>,
}))

// --- WebSocket mock --------------------------------------------------------
let mockWs: MockWebSocket | null = null

class MockWebSocket {
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  readyState = 1
  send = vi.fn()
  close = vi.fn().mockImplementation(() => { this.onclose?.() })

  constructor(_url: string) {
    mockWs = this
  }
}

// Preserve the real WebSocket so we can restore it
const OriginalWebSocket = (global as Record<string, unknown>).WebSocket

beforeEach(() => {
  useDebateStore.getState().reset()
  mockWs = null
  ;(global as Record<string, unknown>).WebSocket = MockWebSocket
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ debate_id: 'test-debate-id' }),
  }))
})

afterEach(() => {
  ;(global as Record<string, unknown>).WebSocket = OriginalWebSocket
  vi.restoreAllMocks()
})

// Render App, click Start, wait for WS to be created, then open the connection
async function renderAndStart() {
  render(<App />)
  await userEvent.click(screen.getByTestId('start-btn'))
  await waitFor(() => expect(mockWs).not.toBeNull())
  await act(async () => { mockWs!.onopen?.() })
}

// Fire a WebSocket message at the App
function fireMessage(type: string, data: Record<string, unknown> = {}) {
  return act(async () => {
    mockWs?.onmessage?.({ data: JSON.stringify({ type, debate_id: 'test-debate-id', data }) })
  })
}

describe('App – WebSocket message handling', () => {
  it('debate_started sets isDebating in the store', async () => {
    await renderAndStart()
    await fireMessage('debate_started')
    expect(useDebateStore.getState().isDebating).toBe(true)
  })

  it('phase_change updates the phase', async () => {
    await renderAndStart()
    await fireMessage('debate_started')
    await fireMessage('phase_change', { phase: 'opening_pro' })
    expect(useDebateStore.getState().phase).toBe('opening_pro')
  })

  it('message_start / message_chunk / message_complete produce a streamed message', async () => {
    await renderAndStart()
    await fireMessage('debate_started')
    await fireMessage('phase_change', { phase: 'opening_pro' })
    await fireMessage('message_start', { speaker: 'PRO' })
    await fireMessage('message_chunk', { chunk: 'Hello ' })
    await fireMessage('message_chunk', { chunk: 'world' })
    await fireMessage('message_complete', { label: 'Opening' })
    const s = useDebateStore.getState()
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].content).toBe('Hello world')
    expect(s.messages[0].speaker).toBe('PRO')
    expect(s.messages[0].label).toBe('Opening')
  })

  it('vote_required sets isWaitingForVote', async () => {
    await renderAndStart()
    await fireMessage('debate_started')
    await fireMessage('vote_required')
    expect(useDebateStore.getState().isWaitingForVote).toBe(true)
  })

  it('debate_complete ends the debate', async () => {
    await renderAndStart()
    await fireMessage('debate_started')
    await fireMessage('debate_complete')
    expect(useDebateStore.getState().isDebating).toBe(false)
  })

  it('error message stores the error', async () => {
    await renderAndStart()
    await fireMessage('error', { message: 'Something went wrong' })
    expect(useDebateStore.getState().error).toBe('Something went wrong')
  })
})
