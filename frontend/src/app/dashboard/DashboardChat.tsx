"use client";

import { useState, useRef, useEffect } from 'react';
import { gql } from '@apollo/client';
import { useApolloClient } from '@apollo/client/react';
import { Send, AlertCircle } from 'lucide-react';
import { UserButton } from "@clerk/nextjs";

const ASK_AGENT_QUERY = gql`
  query AskAgent($message: String!) {
    askAgent(message: $message) {
      success
      response
      rag_tools_found
      error
      taskId
      sessionId
    }
  }
`;

const TASK_COMPLETE_SUBSCRIPTION = gql`
  subscription OnTaskComplete($taskId: String) {
    onTaskComplete(taskId: $taskId) {
      taskId
      userId
      status
      result
      error
      executionTime
      timestamp
    }
  }
`;

interface Message {
  id: string;
  sender: 'user' | 'ai' | 'error';
  content: string;
  timestamp: Date;
  details?: string;
}

interface AskAgentResponse {
  askAgent: {
    success: boolean;
    response: string;
    rag_tools_found: number;
    error: string | null;
    taskId?: string;
    sessionId?: string;
  };
}

interface TaskCompletePayload {
  onTaskComplete: {
    taskId: string;
    userId: string;
    status: string;
    result: string; // Changed from object to string - it's AWSJSON
    error: string | null;
    executionTime: number;
    timestamp: string;
  };
}

interface ParsedResult {
  response?: string;
  rag_tools_found?: number;
  rag_tool_names?: string[];
  success?: boolean;
  awaiting_user?: boolean;
}

interface User {
  firstName?: string | null;
  emailAddresses?: Array<{ emailAddress: string }>;
}

export function DashboardChat({ user }: { user: User | null }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const client = useApolloClient();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!activeTaskId) return;

    const subscription = client.subscribe<TaskCompletePayload>({
      query: TASK_COMPLETE_SUBSCRIPTION,
      variables: { taskId: activeTaskId },
    }).subscribe({
      next: ({ data }) => {
        if (!data?.onTaskComplete) return;

        const { status, result, error, executionTime } = data.onTaskComplete;
        const isSuccess = status === 'COMPLETED';

        // Parse the result JSON string
        let parsedResult: ParsedResult | null = null;
        try {
          parsedResult = result ? JSON.parse(result) : null;
        } catch (err) {
          console.error('Failed to parse result JSON:', err);
        }

        setMessages((prev) => [...prev, {
          id: `msg-${Date.now()}`,
          sender: isSuccess ? 'ai' : 'error',
          content: isSuccess
            ? (parsedResult?.response || 'Task completed')
            : 'Agent Error',
          details: isSuccess
            ? `Found ${parsedResult?.rag_tools_found || 0} tools · ${executionTime}ms`
            : error || 'Unknown error',
          timestamp: new Date(),
        }]);

        setActiveTaskId(null);
        setIsLoading(false);
      },
      error: (err) => {
        console.error('Subscription error:', err);
        setMessages((prev) => [...prev, {
          id: `msg-${Date.now()}`,
          sender: 'error',
          content: 'Subscription Error',
          details: err.message || 'Lost connection to real-time updates',
          timestamp: new Date(),
        }]);
        setActiveTaskId(null);
        setIsLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, [activeTaskId, client]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const messageText = inputValue;
    setMessages((prev) => [...prev, {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content: messageText,
      timestamp: new Date(),
    }]);
    setInputValue('');
    setIsLoading(true);

    try {
      const result = await client.query<AskAgentResponse>({
        query: ASK_AGENT_QUERY,
        variables: { message: messageText },
      });

      if (result.error) {
        const errorMsg = result.error.message || 'Unknown error';
        setMessages((prev) => [...prev, {
          id: `msg-${Date.now()}`,
          sender: 'error',
          content: 'AppSync Error',
          details: errorMsg,
          timestamp: new Date(),
        }]);
        setIsLoading(false);
      } else if (result.data?.askAgent) {
        const { success, response, error, rag_tools_found, taskId } = result.data.askAgent;

        if (taskId) {
          setActiveTaskId(taskId);
        } else {
          setMessages((prev) => [...prev, {
            id: `msg-${Date.now()}`,
            sender: success ? 'ai' : 'error',
            content: success ? response : 'Agent Error',
            details: success ? `Found ${rag_tools_found} tools` : error || 'Unknown error',
            timestamp: new Date(),
          }]);
          setIsLoading(false);
        }
      }
    } catch (error) {
      setMessages((prev) => [...prev, {
        id: `msg-${Date.now()}`,
        sender: 'error',
        content: 'Error',
        details: (error as Error).message,
        timestamp: new Date(),
      }]);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-cognive-dark">
      <div className="border-b border-cognive bg-cognive-card/50 backdrop-blur-sm p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Cognive</h1>
            <p className="text-sm text-cognive-muted">
              {user?.firstName ? `Welcome, ${user.firstName}` : 'Chat with your automation assistant'}
            </p>
          </div>
          <UserButton />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-32">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-5xl mb-4">🤖</div>
              <p className="text-foreground text-lg">Start a conversation</p>
              <p className="text-cognive-muted text-sm mt-2">Ask me to automate anything</p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
              message.sender === 'user'
                ? 'bg-primary text-primary-foreground rounded-br-none'
                : message.sender === 'error'
                ? 'bg-destructive/20 border border-destructive/50 text-destructive rounded-bl-none'
                : 'bg-cognive-card text-foreground rounded-bl-none'
            }`}>
              <div className="flex items-start gap-2">
                {message.sender === 'error' && <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />}
                <div className="flex-1">
                  <p className="text-sm font-semibold">{message.content}</p>
                  {message.details && <p className="text-xs mt-1 opacity-80 whitespace-pre-wrap font-mono">{message.details}</p>}
                  <p className="text-xs mt-2 opacity-70">{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                </div>
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-cognive-card text-foreground px-4 py-3 rounded-lg rounded-bl-none">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-muted rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="fixed bottom-0 left-0 right-0 border-t border-cognive bg-cognive-card/50 backdrop-blur-sm p-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1 bg-input text-foreground px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 placeholder-cognive-muted"
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            className="bg-primary hover:bg-primary/90 disabled:bg-muted text-primary-foreground px-4 py-3 rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}