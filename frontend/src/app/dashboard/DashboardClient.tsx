"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLazyQuery, useMutation, useApolloClient } from "@apollo/client/react";
import { useAppStore, useConnectedIntegrations, useConversations, useCurrentConversation } from "@/store/appStore";
import { ASK_AGENT_QUERY, TASK_COMPLETE_SUBSCRIPTION, GET_USER_CONVERSATIONS, GET_CONVERSATION_MESSAGES, DELETE_CONVERSATION, ON_AGENT_EVENT } from "@/lib/graphql-queries";
import type { AgentResponse, ChatMessage, Task, TaskComplete, AgentEvent } from "@/types";
import { DashboardHeader } from "@/components/chat/DashboardHeader";
import { TaskList } from "@/components/chat/TaskList";
import { TaskHeader } from "@/components/chat/TaskHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";

type TaskStatus = "running" | "paused" | "failed" | "completed";

interface DashboardClientProps {
  user: {
    firstName?: string | null;
    imageUrl?: string;
    emailAddresses?: { emailAddress: string }[];
  } | null;
}

export function DashboardClient({ user }: DashboardClientProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const apolloClient = useApolloClient();
  
  const [UserButtonComponent, setUserButtonComponent] = useState<React.ComponentType<{ afterSignOutUrl?: string }> | null>(null);
  const [mounted, setMounted] = useState(false);
  const isFirstLoad = useRef(true);

  useEffect(() => {
    setMounted(true);
    if (user) {
      import("@clerk/nextjs").then((clerk) => {
        setUserButtonComponent(() => clerk.UserButton);
      }).catch(() => {});
    }
  }, [user]);

  const connectedIntegrations = useConnectedIntegrations();
  const {
    currentTaskId,
    setCurrentTask,
    resetConversationState,
    setConversations,
    addConversation,
    removeConversation,
    updateConversation,
    updateConversationId,
    updateConversationName,
    addMessageToConversation,
    addPendingMessage,
    clearPendingMessages,
    setIsAppLoading,
    setIsChatLoading,
    isAppLoading,
    isChatLoading,
  } = useAppStore();

  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [copiedWorkflow, setCopiedWorkflow] = useState(false);
  const [currentSubscriptionTaskId, setCurrentSubscriptionTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [thinkingLogs, setThinkingLogs] = useState<AgentEvent[]>([]);

  const [deleteConversationMutation] = useMutation<{ deleteConversation: { success: boolean; error?: string; deletedCount?: number } }>(DELETE_CONVERSATION);
  const [askAgent] = useLazyQuery<{ askAgent: AgentResponse }, { message: string; sessionId?: string }>(ASK_AGENT_QUERY);
  const [loadConversations, { data: conversationsData, loading: loadingConversations, error: conversationsError }] = useLazyQuery<{ getUserConversations: any[] }>(GET_USER_CONVERSATIONS, {
    fetchPolicy: 'network-only',
  });
  const [loadMessages, { error: messagesError }] = useLazyQuery<{ getConversationMessages: any[] }, { sessionId: string }>(GET_CONVERSATION_MESSAGES, {
    fetchPolicy: 'network-only',
  });

  const tasks = useConversations();
  const currentTask = useCurrentConversation();

  useEffect(() => {
    if (conversationsError) console.error("[Conversations] Load failed:", conversationsError.message);
  }, [conversationsError]);

  useEffect(() => {
    if (messagesError) console.error("[Messages] Load failed:", messagesError.message);
  }, [messagesError]);

  const handleTaskClick = useCallback(async (taskId: string) => {
    // 1. Get the current task immediately from Zustand to check its cache
    const currentTasks = useAppStore.getState().conversations;
    const cachedTask = currentTasks.find(t => t.id === taskId);
    const hasCachedHistory = cachedTask && cachedTask.chatHistory && cachedTask.chatHistory.length > 0;

    resetConversationState();
    setCurrentTask(taskId);
    
    // 2. Only show the loading skeleton if this chat is completely empty in Zustand
    if (!hasCachedHistory) {
      setIsChatLoading(true);
    }
    
    // 3. Background Sync: Fetch fresh data from AWS no matter what
    const { data, error } = await loadMessages({ variables: { sessionId: taskId } });
    
    // 4. Update Zustand silently 
    if (data?.getConversationMessages) {
      const actualMessages = data.getConversationMessages.slice(1);
      const messages: ChatMessage[] = actualMessages.map((msg: any) => ({
        id: msg.id,
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: msg.timestamp,
      }));
      updateConversation(taskId, { chatHistory: messages });
    }
    
    // 5. Turn off loader
    if (!hasCachedHistory) {
      setIsChatLoading(false);
    }
  }, [loadMessages, resetConversationState, setCurrentTask, updateConversation, setIsChatLoading]);

  useEffect(() => {
    if (user) {
      // If we have no cached conversations, then show the loader.
      // E.g., first ever login. Otherwise, we cleanly load in the background.
      if (useAppStore.getState().conversations.length === 0) {
        setIsAppLoading(true);
      } else {
        setIsAppLoading(false);
      }
      loadConversations();
    }
  }, [user, loadConversations, setIsAppLoading]);

  // Fetch connected apps from Redis via API
  const connectIntegration = useAppStore((state) => state.connectIntegration);
  useEffect(() => {
    if (user && mounted) {
      fetch("/api/integrations/connected")
        .then((res) => res.json())
        .then((data) => {
          // Use slugs to update Zustand — the store already maps slugs → catalog entries
          if (data.slugs && Array.isArray(data.slugs)) {
            data.slugs.forEach((slug: string) => connectIntegration(slug));
          }
        })
        .catch((err) => console.error("Failed to fetch connected apps:", err));
    }
  }, [user, mounted, connectIntegration]);

  useEffect(() => {
    if (conversationsData?.getUserConversations) {
      const allConversations = conversationsData.getUserConversations;

      if (process.env.NODE_ENV === 'development') {
        console.groupCollapsed(`Conversations: ${allConversations.length}`);
        
        (async () => {
          for (let i = 0; i < allConversations.length; i++) {
            const conv = allConversations[i];
            try {
              const { data } = await apolloClient.query<{ getConversationMessages: any[] }>({
                query: GET_CONVERSATION_MESSAGES,
                variables: { sessionId: conv.sessionId },
                fetchPolicy: 'network-only'
              });
              const messages = data?.getConversationMessages || [];
              const userMsgs = messages.filter((m: any) => m.sender === 'user');
              const agentMsgs = messages.filter((m: any) => m.sender === 'assistant');
              
              console.groupCollapsed(`${i + 1}. ${conv.chatName || 'Untitled'}`);
              console.log("User:", userMsgs.map((m: any) => m.content.substring(0, 50)));
              console.log("Agent:", agentMsgs.map((m: any) => m.content.substring(0, 50)));
              console.groupEnd();
            } catch (err: any) {
              console.log(`${i + 1}. ${conv.chatName || 'Untitled'} - failed`);
            }
          }
        })();
        
        console.groupEnd();
      }

      const currentStoreTasks = useAppStore.getState().conversations;

      const conversationTasks: Task[] = allConversations
        .filter((conv: any) => conv.chatName && conv.chatName.trim() !== '')
        .map((conv: any) => {
          const existingTask = currentStoreTasks.find(t => t.id === conv.sessionId);
          return {
            id: conv.sessionId,
            name: conv.chatName,
            status: 'paused' as TaskStatus,
            type: 'automation' as const,
            lastModifiedAt: conv.lastModifiedAt,
            lastRun: conv.lastModifiedAt,
            connectedApps: [],
            description: conv.chatName,
            chatHistory: existingTask?.chatHistory || [], // <-- Preserve from persist!
            compiledWorkflow: { trigger: { type: 'polling' as 'polling', interval: '', app: '' }, steps: [], errorHandling: {} },
            stats: { totalRuns: 0 },
          };
        });

      setConversations(conversationTasks);

      if (conversationTasks.length > 0 && currentTaskId === undefined) {
        handleTaskClick(conversationTasks[0].id);
      }

      setIsAppLoading(false);
    }
  }, [conversationsData, currentTaskId, setConversations, handleTaskClick, setIsAppLoading]);

  useEffect(() => {
    const msg = searchParams.get("msg");
    if (!msg) return;
    router.replace("/dashboard");
    handleNewTaskWithMessage(msg);
  }, [searchParams]);

  useEffect(() => {
    if (!currentSubscriptionTaskId || !currentTaskId) return;

    console.log('[Subscription] Starting for taskId:', currentSubscriptionTaskId);
    setThinkingLogs([]);

    const eventSubscription = apolloClient.subscribe<{ onAgentEvent: AgentEvent }>({
      query: ON_AGENT_EVENT,
      variables: { taskId: currentTaskId }
    }).subscribe({
      next: ({ data }) => {
        if (data?.onAgentEvent) {
          setThinkingLogs(prev => [...prev, data.onAgentEvent]);
          // Scroll to bottom when thinking logs update
          setTimeout(() => {
            const chatBox = document.getElementById('chat-scroll-container');
            if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
          }, 50);
        }
      }
    });

    const subscription = apolloClient.subscribe<{ onTaskComplete: TaskComplete }>({
      query: TASK_COMPLETE_SUBSCRIPTION,
      variables: { taskId: currentSubscriptionTaskId },
    }).subscribe({
      next: ({ data }) => {
        console.log('[Subscription] Received data:', data);
        if (!data?.onTaskComplete) return;

        const freshState = useAppStore.getState();
        const freshCurrentTask = freshState.conversations.find(t => t.id === currentTaskId);
        const freshTasks = freshState.conversations;

        const { status, result, error: taskError, timestamp } = data.onTaskComplete;
        const isSuccess = status === 'COMPLETED';

        let parsedResult: any = null;
        try { parsedResult = result ? (typeof result === "string" ? JSON.parse(result) : result) : null; } catch (err) {}

        const chatName = parsedResult?.chatName || "";
        const assistantMessage: ChatMessage = {
          id: `msg_${Date.now() + 1}`,
          role: "assistant",
          content: isSuccess ? (parsedResult?.response || 'Task completed') : 'Agent Error: ' + (taskError || 'Unknown error'),
          timestamp: new Date().toISOString(),
        };

        const existingTask = freshTasks.find(t => t.id === currentTaskId);
        if (!existingTask && chatName) {
          const pendingMsgs = freshState.pendingMessages;
          const newTask: Task = {
            id: currentTaskId,
            name: chatName,
            status: isSuccess ? "completed" as TaskStatus : "failed" as TaskStatus,
            type: "automation" as const,
            lastModifiedAt: new Date().toISOString(),
            lastRun: timestamp,
            connectedApps: [],
            description: chatName,
            chatHistory: [...pendingMsgs, assistantMessage],
            compiledWorkflow: { trigger: { type: "polling" as "polling", interval: "", app: "" }, steps: [], errorHandling: {} },
            stats: { totalRuns: 0 },
          };
          addConversation(newTask);
          freshState.clearPendingMessages();
          setCurrentTask(currentTaskId);
        } else if (freshCurrentTask) {
          updateConversation(currentTaskId, {
            name: chatName || freshCurrentTask.name,
            chatHistory: [...freshCurrentTask.chatHistory, assistantMessage],
            status: isSuccess ? "completed" : "failed",
            lastModifiedAt: new Date().toISOString(),
            lastRun: timestamp
          });
        }

        setCurrentSubscriptionTaskId(null);
        setIsTyping(false);
      },
      error: (err) => {
        console.error("[Subscription] Error:", err);
        const errorMessage: ChatMessage = {
          id: `msg_${Date.now() + 1}`,
          role: "assistant",
          content: `Subscription Error: ${err.message || 'Lost connection to real-time updates'}`,
          timestamp: new Date().toISOString(),
        };
        addMessageToConversation(currentTaskId, errorMessage);
        setCurrentSubscriptionTaskId(null);
        setIsTyping(false);
      },
      complete: () => {
        console.log('[Subscription] Completed');
      }
    });

    return () => {
      console.log('[Subscription] Unsubscribing from taskId:', currentSubscriptionTaskId);
      subscription.unsubscribe();
      eventSubscription.unsubscribe();
    };
  }, [currentSubscriptionTaskId, currentTaskId, apolloClient, addConversation, updateConversation, addMessageToConversation]);

  const sendMessageToAgent = async (message: string, sessionId?: string): Promise<{ response: string; hasTaskId: boolean; sessionId?: string }> => {
    try {
      const { data, error } = await askAgent({ variables: { message, sessionId } });
      const result = data?.askAgent;

      if (error) {
        const graphQLErrors = (error as any).graphQLErrors;
        const networkError = (error as any).networkError;
        if (graphQLErrors?.length > 0) {
          const messages = graphQLErrors.map((e: any) => e.message).join("; ");
          setError(messages);
          return { response: "", hasTaskId: false };
        }
        if (networkError) {
          const status = networkError.statusCode || networkError.status;
          setError(`Network error (${status ?? "unknown"}): ${networkError.message}`);
          return { response: "", hasTaskId: false };
        }
      }

      if (!result) { setError("AgentCore did not return any data."); return { response: "", hasTaskId: false }; }
      if (!result.success) { setError(result.error || "The agent could not process your request."); return { response: "", hasTaskId: false }; }

      if (result.taskId) {
        setCurrentSubscriptionTaskId(result.taskId);
        return { response: result.response || "", hasTaskId: true, sessionId: result.sessionId };
      }
      return { response: result.response || "", hasTaskId: false };
    } catch (error: any) {
      setError(`Error: ${error?.message || "Unknown error"}`);
      return { response: "", hasTaskId: false };
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const messageText = chatInput;
    setChatInput("");
    setError(null);
    setThinkingLogs([]); 

    let taskId = currentTask?.id === 'pending' ? null : currentTask?.id;

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: "user",
      content: messageText,
      timestamp: new Date().toISOString(),
    };

    if (!taskId) {
      addPendingMessage(userMessage);
    } else {
      addMessageToConversation(taskId, userMessage);
    }

    setIsTyping(true);

    try {
      const { response, hasTaskId, sessionId } = await sendMessageToAgent(messageText, taskId || undefined);

      if (sessionId) {
        if (!taskId) {
          setCurrentTask(sessionId);
        } else if (sessionId !== taskId) {
          updateConversationId(taskId, sessionId);
          setCurrentTask(sessionId);
        }
        taskId = sessionId;
      }

      if (hasTaskId) return;

      const assistantMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: "assistant",
        content: response,
        timestamp: new Date().toISOString(),
      };

      if (taskId) addMessageToConversation(taskId, assistantMessage);
      setIsTyping(false);
    } catch (error) {
      setIsTyping(false);
    }
  };

  const handleOptionClick = async (optionValue: string, optionLabel: string) => {
    setIsTyping(true);
    setThinkingLogs([]); // Instantly clear logs

    try {
      const { response, hasTaskId, sessionId } = await sendMessageToAgent(optionLabel, undefined);

      if (sessionId) {
        setCurrentTask(sessionId);
        const userMessage: ChatMessage = { id: `msg_${Date.now()}`, role: "user", content: optionLabel, timestamp: new Date().toISOString() };
        addMessageToConversation(sessionId, userMessage);
        if (hasTaskId) return;
        const assistantMessage: ChatMessage = { id: `msg_${Date.now() + 1}`, role: "assistant", content: response, timestamp: new Date().toISOString() };
        addMessageToConversation(sessionId, assistantMessage);
      }
    } catch (error: any) {
      console.error("[OptionClick] Error:", error.message);
    } finally {
      setIsTyping(false);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    // Optimistic: remove from store immediately
    const wasCurrentTask = currentTaskId === taskId;
    const taskIndex = tasks.findIndex(t => t.id === taskId);
    const deletedTask = tasks[taskIndex];
    removeConversation(taskId);

    // If deleted task was selected, switch to adjacent or clear
    if (wasCurrentTask) {
      const remaining = tasks.filter(t => t.id !== taskId);
      if (remaining.length > 0) {
        const nextIndex = Math.min(taskIndex, remaining.length - 1);
        handleTaskClick(remaining[nextIndex].id);
      } else {
        resetConversationState();
        setCurrentTask(null);
      }
    }

    try {
      const { data } = await deleteConversationMutation({ variables: { sessionId: taskId } });
      if (!data?.deleteConversation?.success) {
        // Rollback: re-add the task
        if (deletedTask) addConversation(deletedTask);
        setError(`Failed to delete conversation: ${data?.deleteConversation?.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      // Rollback on network error
      if (deletedTask) addConversation(deletedTask);
      setError(`Failed to delete conversation: ${err.message || 'Network error'}`);
    }
  };

  const handleNewTask = () => {
    resetConversationState();
    setCurrentTask(null);
  };

  const handleNewTaskWithMessage = async (message: string) => {
    resetConversationState();
    setIsTyping(true);
    setThinkingLogs([]); // Instantly clear logs

    try {
      const { response, hasTaskId, sessionId } = await sendMessageToAgent(message, undefined);

      if (sessionId) {
        setCurrentTask(sessionId);
        const userMessage: ChatMessage = { id: `msg_${Date.now()}`, role: "user", content: message, timestamp: new Date().toISOString() };
        addMessageToConversation(sessionId, userMessage);
      }

      if (hasTaskId) return;

      const assistantMessage: ChatMessage = { id: `msg_${Date.now() + 1}`, role: "assistant", content: response, timestamp: new Date().toISOString() };
      if (sessionId) addMessageToConversation(sessionId, assistantMessage);
      setIsTyping(false);
    } catch (error) {
      setIsTyping(false);
    }
  };



  const handleCopyWorkflow = () => {
    if (currentTask?.compiledWorkflow) {
      navigator.clipboard.writeText(JSON.stringify(currentTask.compiledWorkflow, null, 2));
      setCopiedWorkflow(true);
      setTimeout(() => setCopiedWorkflow(false), 2000);
    }
  };

  useEffect(() => {
    if (isFirstLoad.current) {
      isFirstLoad.current = false;
    }
  }, []);

  if (!mounted) {
    return null; 
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden" data-testid="dashboard-page">
      <DashboardHeader
        connectedIntegrations={connectedIntegrations}
        onIntegrationsClick={() => router.push("/integrations")}
        onSettingsClick={() => router.push("/settings")}
        UserButtonComponent={UserButtonComponent}
      />

      <div className="flex-1 flex min-h-0">
        <TaskList
          tasks={tasks}
          currentTaskId={currentTaskId}
          onTaskClick={handleTaskClick}
          onNewTask={handleNewTask}
          onDeleteTask={handleDeleteTask}
          isLoading={isAppLoading && tasks.length === 0}
        />

        <main className="flex-1 flex flex-col min-h-0">
          {currentTask ? (
            <>
              <TaskHeader
                task={currentTask}
                onShowWorkflow={() => {}}
                onShowLogs={() => {}}
              />
              <ChatArea
                messages={currentTask.chatHistory}
                isTyping={isTyping}
                user={user}
                onOptionClick={handleOptionClick}
                isLoading={isChatLoading}
                thinkingLogs={thinkingLogs}
              />
            </>
          ) : (
            <ChatArea
              messages={[]}
              isTyping={isTyping}
              user={user}
              onOptionClick={handleOptionClick}
              isLoading={isChatLoading}
              thinkingLogs={thinkingLogs}
            />
          )}

          <ChatInput
            value={chatInput}
            onChange={setChatInput}
            onSubmit={handleSendMessage}
            onIntegrationsClick={() => router.push("/integrations")}
            onWorkflowClick={() => {}}
            onLogsClick={() => {}}
            disabled={isTyping}
          />
        </main>
      </div>


      {error && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card p-6 rounded-lg max-w-md mx-4">
            <h3 className="text-lg font-semibold text-destructive mb-2">Something went wrong</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <button onClick={() => setError(null)} className="bg-primary text-primary-foreground px-4 py-2 rounded hover:opacity-90">
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
}