import React, { useEffect, useRef, useState } from 'react';
import { ChatResponse, Message, sendChatMessage } from '../services/api';

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  action?: string;
  policyReason?: string;
  confidence?: number;
}

const ChatBox: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [studentId, setStudentId] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const currentInput = inputValue; // capture before clearing
    const userMessage: ChatMessage = { role: 'user', content: currentInput };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const apiMessages: Message[] = messages
        .filter(m => m.role !== 'system')
        .concat([{ role: 'user', content: currentInput }])
        .map(m => ({ role: m.role, content: m.content }));

      const response: ChatResponse = await sendChatMessage(apiMessages, studentId || undefined);

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.output,
        action: response.action,
        policyReason: response.policy_reason,
        confidence: response.agent_confidence,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        role: 'system',
        content: `Error: ${error?.response?.data?.detail || error?.message || 'Failed to send message'}`,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getActionBadge = (action?: string) => {
    if (!action) return null;
    const colors: Record<string, string> = {
      allow: 'bg-green-100 text-green-800',
      redact: 'bg-yellow-100 text-yellow-800',
      block: 'bg-red-100 text-red-800',
      rewrite_review: 'bg-blue-100 text-blue-800',
    };
    return (
      <span className={`inline-block px-2 py-1 text-xs font-semibold rounded ${colors[action] || 'bg-gray-100 text-gray-800'}`}>
        {action.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
      <div className="p-4 border-b border-gray-200">
        <label className="block text-sm font-medium text-gray-700 mb-2">Student ID (optional)</label>
        <input
          type="text"
          value={studentId}
          onChange={e => setStudentId(e.target.value)}
          placeholder="Enter your student ID"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="h-96 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-lg mb-2">Welcome to LMGuard Student Tutor!</p>
            <p className="text-sm">Ask me anything, and I'll help you learn safely.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : msg.role === 'system'
                  ? 'bg-red-100 text-red-800 border border-red-300'
                  : 'bg-gray-200 text-gray-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.action && (
                <div className="mt-2 pt-2 border-t border-gray-300">
                  <div className="flex items-center gap-2 mb-1">
                    {getActionBadge(msg.action)}
                    {msg.confidence !== undefined && (
                      <span className="text-xs text-gray-600">Confidence: {(msg.confidence * 100).toFixed(0)}%</span>
                    )}
                  </div>
                  {msg.policyReason && <p className="text-xs text-gray-600 mt-1">{msg.policyReason}</p>}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <textarea
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your question..."
            rows={2}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBox;


