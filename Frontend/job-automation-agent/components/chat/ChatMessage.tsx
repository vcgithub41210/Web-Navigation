'use client';

import React from 'react';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  isThinking?: boolean;
  timestamp?: Date;
}

function renderContent(text: string) {
  // Split into paragraphs on blank lines, then handle inline bold
  return text.split('\n').map((line, i) => {
    // Render **bold** spans
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    const rendered = parts.map((part, j) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={j}>{part.slice(2, -2)}</strong>
      ) : (
        part
      )
    );
    return (
      <React.Fragment key={i}>
        {rendered}
        {i < text.split('\n').length - 1 && <br />}
      </React.Fragment>
    );
  });
}

export function ChatMessage({ role, content, isThinking, timestamp }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`${isUser ? 'max-w-[75%]' : 'max-w-[85%]'} ${isUser ? 'flex-row-reverse' : ''} flex gap-3`}>
        {/* Avatar */}
        <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
          isUser 
            ? 'bg-accent text-accent-foreground' 
            : 'bg-primary text-primary-foreground'
        }`}>
          {isUser ? '👤' : '🤖'}
        </div>

        {/* Message bubble */}
        <div className="flex flex-col gap-1">
          {isThinking ? (
            <div className={`px-4 py-3 rounded-2xl ${
              isUser 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-card/80 border border-border/40 text-foreground'
            }`}>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-current rounded-full thinking-pulse" />
                <div className="w-2 h-2 bg-current rounded-full thinking-pulse" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-current rounded-full thinking-pulse" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          ) : (
            <div className={`px-4 py-3 rounded-2xl break-words ${
              isUser 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-card/80 border border-border/40 text-foreground'
            }`}>
              {isUser ? content : renderContent(content)}
            </div>
          )}

          {/* Timestamp and actions */}
          <div className={`flex items-center gap-2 text-xs text-foreground/50 ${isUser ? 'justify-end' : 'justify-start'}`}>
            {timestamp && (
              <span>{timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            )}
            {!isUser && !isThinking && (
              <button
                onClick={handleCopy}
                className="hover:text-foreground/70 transition"
                title="Copy message"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
