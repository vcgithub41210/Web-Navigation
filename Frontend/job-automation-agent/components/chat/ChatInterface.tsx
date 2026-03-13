'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Plus, Paperclip, ChevronDown } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ThinkingAnimation } from './ThinkingAnimation';
import { sendChatMessage, sendCustomFormMessage } from '@/app/actions/chat';
import { useAuth } from '@/context/AuthContext';

type AgentMode = 'autoapply' | 'customform';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isThinking?: boolean;
}

const MODE_LABELS: Record<AgentMode, string> = {
  autoapply: 'Auto Apply',
  customform: 'Custom URL',
};

const MODE_PLACEHOLDERS: Record<AgentMode, string> = {
  autoapply: 'Type a job search query (e.g. "Apply to top 5 React developer jobs")...',
  customform: 'Paste a form URL with instructions (e.g. "Open https://... and fill the form")...',
};

const MODE_WELCOME: Record<AgentMode, string> = {
  autoapply:
    "Hi! I'm your JobAgent AI assistant. I'll search LinkedIn for jobs and auto-apply using your resume. Just tell me what kind of roles to target!",
  customform:
    "Hi! I'm your Form-Filler assistant. Paste a Google Form (or any form) URL with any extra instructions and I'll fill and submit it using your resume details.",
};

export function ChatInterface() {
  const { user } = useAuth();
  const [agentMode, setAgentMode] = useState<AgentMode>('autoapply');
  const [modeDropdownOpen, setModeDropdownOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: MODE_WELCOME['autoapply'],
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const scrollToBottom = () => {
    const container = scrollContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleModeChange = (mode: AgentMode) => {
    setAgentMode(mode);
    setModeDropdownOpen(false);
    setMessages([
      {
        id: Date.now().toString(),
        role: 'assistant',
        content: MODE_WELCOME[mode],
        timestamp: new Date(),
      },
    ]);
    setInput('');
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() && !selectedFile) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input || (selectedFile ? `Attached file: ${selectedFile.name}` : ''),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setSelectedFile(null);
    setIsLoading(true);

    try {
      const thinkingId = (Date.now() + 1).toString();
      setMessages(prev => [
        ...prev,
        { id: thinkingId, role: 'assistant', content: '', timestamp: new Date(), isThinking: true },
      ]);

      let response = '';

      try {
        if (!user) {
          throw new Error('Please log in to use the chat.');
        }

        if (agentMode === 'autoapply') {
          response = await sendChatMessage(userMessage.content, user.uid);
        } else {
          response = await sendCustomFormMessage(userMessage.content, user.uid);
        }
      } catch (error: any) {
        console.error('Backend error:', error);
        response = 'Sorry, the server is currently unavailable. Please try again.';
      }

      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== thinkingId);
        return [
          ...filtered,
          {
            id: (Date.now() + 2).toString(),
            role: 'assistant',
            content: response,
            timestamp: new Date(),
          },
        ];
      });
    } catch (error) {
      console.error('Error in chat:', error);
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 2).toString(),
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleNewChat = () => {
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content: MODE_WELCOME[agentMode],
        timestamp: new Date(),
      },
    ]);
  };

  return (
    <div className="flex flex-col h-full bg-background rounded-2xl border border-border/40 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border/40 bg-card/50">
        <h2 className="text-lg font-semibold">JobAgent Assistant</h2>

        <div className="flex items-center gap-2">
          {/* Agent mode dropdown */}
          <div className="relative">
            <button
              onClick={() => setModeDropdownOpen(prev => !prev)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary/10 border border-primary/30 text-primary rounded-lg hover:bg-primary/20 transition"
            >
              {MODE_LABELS[agentMode]}
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
            {modeDropdownOpen && (
              <div className="absolute right-0 mt-1 w-36 bg-card border border-border/60 rounded-lg shadow-lg z-10">
                {(Object.keys(MODE_LABELS) as AgentMode[]).map(mode => (
                  <button
                    key={mode}
                    onClick={() => handleModeChange(mode)}
                    className={`w-full text-left px-3 py-2 text-sm rounded-lg transition hover:bg-primary/10 ${
                      agentMode === mode ? 'text-primary font-medium' : 'text-foreground/80'
                    }`}
                  >
                    {MODE_LABELS[mode]}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleNewChat}
            className="p-2 hover:bg-card rounded-lg transition"
            title="New chat"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(message => (
          <div key={message.id}>
            {message.isThinking ? (
              <ThinkingAnimation />
            ) : (
              <ChatMessage
                role={message.role}
                content={message.content}
                timestamp={message.timestamp}
              />
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-border/40 bg-card/50">
        {selectedFile && (
          <div className="mb-3 flex items-center gap-2 p-2 bg-primary/10 rounded-lg border border-primary/20">
            <Paperclip className="w-4 h-4 text-primary" />
            <span className="text-sm text-foreground/70">{selectedFile.name}</span>
            <button
              onClick={() => setSelectedFile(null)}
              className="ml-auto text-foreground/60 hover:text-foreground"
            >
              ×
            </button>
          </div>
        )}

        <form onSubmit={handleSendMessage} className="flex gap-3">
          <label className="cursor-pointer hover:opacity-70 transition">
            <Paperclip className="w-5 h-5 text-foreground/60" />
            <input
              type="file"
              onChange={handleFileSelect}
              accept=".pdf,.jpg,.jpeg,.png,.gif,.mp4,.webm"
              className="hidden"
            />
          </label>

          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={MODE_PLACEHOLDERS[agentMode]}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-input border border-border/40 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 transition disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={isLoading || (!input.trim() && !selectedFile)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Send className="w-5 h-5" />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>

        <p className="text-xs text-foreground/40 mt-3">
          {agentMode === 'autoapply'
            ? 'Tip: Tell me the type of roles and I\'ll find and apply to LinkedIn Easy Apply jobs using your resume.'
            : 'Tip: Paste a form URL with any instructions and I\'ll fill and submit it for you.'}
        </p>
      </div>
    </div>
  );
}

