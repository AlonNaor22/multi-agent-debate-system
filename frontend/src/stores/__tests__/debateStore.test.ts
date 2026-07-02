import { describe, it, expect, beforeEach } from 'vitest'
import { useDebateStore } from '../debateStore'
import { strings } from '../../constants/strings'

beforeEach(() => {
  useDebateStore.getState().reset()
})

describe('debateStore – startDebate', () => {
  it('sets isDebating, debateId, topic and styles', () => {
    useDebateStore.getState().startDebate('d1', 'AI safety', 'passionate', 'aggressive')
    const s = useDebateStore.getState()
    expect(s.isDebating).toBe(true)
    expect(s.debateId).toBe('d1')
    expect(s.topic).toBe('AI safety')
    expect(s.proStyle).toBe('passionate')
    expect(s.conStyle).toBe('aggressive')
  })

  it('clears messages and errors from a previous debate', () => {
    useDebateStore.setState({ messages: [{ speaker: 'PRO', content: 'old', phase: 'introduction' }], error: 'prev' })
    useDebateStore.getState().startDebate('d2', 'topic', 'academic', 'humorous')
    const s = useDebateStore.getState()
    expect(s.messages).toHaveLength(0)
    expect(s.error).toBeNull()
  })
})

describe('debateStore – streaming', () => {
  it('startStreaming sets the streaming speaker and clears content', () => {
    useDebateStore.getState().startStreaming('PRO')
    const s = useDebateStore.getState()
    expect(s.streamingSpeaker).toBe('PRO')
    expect(s.streamingContent).toBe('')
  })

  it('appendStreamingChunk accumulates text', () => {
    useDebateStore.getState().startStreaming('CON')
    useDebateStore.getState().appendStreamingChunk('Hello')
    useDebateStore.getState().appendStreamingChunk(', world')
    expect(useDebateStore.getState().streamingContent).toBe('Hello, world')
  })

  it('finishStreaming commits a message and clears stream state', () => {
    useDebateStore.setState({ phase: 'opening_pro' })
    useDebateStore.getState().startStreaming('PRO')
    useDebateStore.getState().appendStreamingChunk('Opening argument')
    useDebateStore.getState().finishStreaming('Opening')
    const s = useDebateStore.getState()
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].content).toBe('Opening argument')
    expect(s.messages[0].speaker).toBe('PRO')
    expect(s.messages[0].label).toBe('Opening')
    expect(s.streamingContent).toBe('')
    expect(s.streamingSpeaker).toBeNull()
  })

  it('finishStreaming still finalizes an empty message, so no typing indicator is left dangling', () => {
    useDebateStore.setState({ phase: 'rebuttal' })
    useDebateStore.getState().startStreaming('CON')
    // no chunks appended — e.g. the backend streamed a zero-length response
    useDebateStore.getState().finishStreaming('Rebuttal')

    const s = useDebateStore.getState()
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0]).toMatchObject({ speaker: 'CON', content: '', label: 'Rebuttal' })
    expect(s.streamingSpeaker).toBeNull()
    expect(s.streamingContent).toBe('')
  })

  it('finishStreaming is a no-op when there is no active streaming speaker', () => {
    useDebateStore.getState().finishStreaming('nothing to finish')
    const s = useDebateStore.getState()
    expect(s.messages).toHaveLength(0)
    expect(s.streamingSpeaker).toBeNull()
  })
})

describe('debateStore – setError', () => {
  it('surfaces the message and clears any dangling streaming/typing indicator', () => {
    // Simulate an error arriving mid-stream, while a speaker is "typing".
    useDebateStore.getState().startStreaming('PRO')
    useDebateStore.getState().appendStreamingChunk('half a sentence')
    useDebateStore.getState().setError('The AI service is temporarily unavailable.')

    const s = useDebateStore.getState()
    expect(s.error).toBe('The AI service is temporarily unavailable.')
    expect(s.streamingSpeaker).toBeNull()
    expect(s.streamingContent).toBe('')
  })

  it('dismisses the vote modal when an error arrives during voting', () => {
    useDebateStore.getState().setIsWaitingForVote(true)
    useDebateStore.getState().setError('boom')
    expect(useDebateStore.getState().isWaitingForVote).toBe(false)
  })

  it('setError(null) clears the message', () => {
    useDebateStore.getState().setError('boom')
    useDebateStore.getState().setError(null)
    expect(useDebateStore.getState().error).toBeNull()
  })
})

describe('debateStore – connection lost (ws.onclose)', () => {
  // App.tsx's ws.onclose handler calls setError with this message whenever
  // the socket drops before the debate reached the 'finished' phase.
  it('surfaces a connection-lost error and clears the dangling streaming/typing state', () => {
    useDebateStore.getState().startStreaming('PRO')
    useDebateStore.getState().appendStreamingChunk('mid-sentence when the socket drops')
    useDebateStore.getState().setIsWaitingForVote(true)

    useDebateStore.getState().setError(strings.errors.connectionLost)

    const s = useDebateStore.getState()
    expect(s.error).toBe(strings.errors.connectionLost)
    expect(s.streamingSpeaker).toBeNull()
    expect(s.streamingContent).toBe('')
    expect(s.isWaitingForVote).toBe(false)
  })
})

describe('debateStore – reset', () => {
  it('restores all initial state', () => {
    useDebateStore.getState().startDebate('d3', 'topic', 'aggressive', 'academic')
    useDebateStore.getState().startStreaming('JUDGE')
    useDebateStore.getState().appendStreamingChunk('text')
    useDebateStore.getState().reset()
    const s = useDebateStore.getState()
    expect(s.isDebating).toBe(false)
    expect(s.debateId).toBeNull()
    expect(s.messages).toHaveLength(0)
    expect(s.streamingContent).toBe('')
    expect(s.streamingSpeaker).toBeNull()
    expect(s.error).toBeNull()
  })
})
