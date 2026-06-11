import type { DebateMessage as DebateMessageType } from '../../types/debate';
import { SpeakerBubble } from './SpeakerBubble';

interface DebateMessageProps {
  message: DebateMessageType;
}

export function DebateMessage({ message }: DebateMessageProps) {
  return (
    <SpeakerBubble
      speaker={message.speaker}
      headerExtra={
        message.label && (
          <span className="text-sm text-gray-600 font-medium">{message.label}</span>
        )
      }
    >
      {message.content}
    </SpeakerBubble>
  );
}
