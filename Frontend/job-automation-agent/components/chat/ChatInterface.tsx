'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Plus, Paperclip } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ThinkingAnimation } from './ThinkingAnimation';
import { sendChatMessage } from '@/app/actions/chat';
import { useAuth } from '@/context/AuthContext';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isThinking?: boolean;
}

export function ChatInterface() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hi! I\'m your JobAgent AI assistant. I can help you fill out job applications, analyze forms, and automate your job search. Just share a job application link or form, and I\'ll handle the rest!',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() && !selectedFile) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input || (selectedFile ? `Attached file: ${selectedFile.name}` : ''),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setSelectedFile(null);
    setIsLoading(true);

    try {
      // Add thinking animation message
      const thinkingId = (Date.now() + 1).toString();
      setMessages(prev => [...prev, {
        id: thinkingId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isThinking: true
      }]);

      let response = '';

      try {
        if (!user) {
          throw new Error('Please log in to use the chat.');
        }
        response = await sendChatMessage(userMessage.content, user.uid); // PASS user.uid
      } catch (error: any) {
        console.error('Backend error:', error);
        response = 'Sorry, the server is currently unavailable. Please try again.';
      }

      // Remove thinking message and add response
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== thinkingId);
        return [...filtered, {
          id: (Date.now() + 2).toString(),
          role: 'assistant',
          content: response,
          timestamp: new Date()
        }];
      });
    } catch (error) {
      console.error('Error in chat:', error);
      // Add error message
      setMessages(prev => [...prev, {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }]);
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
    setMessages([{
      id: '1',
      role: 'assistant',
      content: 'Hi! I\'m your JobAgent AI assistant. I can help you fill out job applications, analyze forms, and automate your job search. Just share a job application link or form, and I\'ll handle the rest!',
      timestamp: new Date()
    }]);
  };

  return (
    <div className="flex flex-col h-full bg-background rounded-2xl border border-border/40 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border/40 bg-card/50">
        <h2 className="text-lg font-semibold">JobAgent Assistant</h2>
        <button
          onClick={handleNewChat}
          className="p-2 hover:bg-card rounded-lg transition"
          title="New chat"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
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
            onChange={(e) => setInput(e.target.value)}
            placeholder="Share a job form link or ask for help..."
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
          Tip: Share job application URLs or forms, and I'll fill them out using your resume information.
        </p>
      </div>
    </div>
  );
}
