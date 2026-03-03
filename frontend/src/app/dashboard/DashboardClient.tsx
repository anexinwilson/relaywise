"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLazyQuery, useMutation, useApolloClient } from "@apollo/client/react";
import { useAppStore, useConnectedIntegrations, useConversations, useCurrentConversation, useAddLog, useClearLogs, useLogs } from "@/store/appStore";
import { ASK_AGENT_QUERY, TASK_COMPLETE_SUBSCRIPTION, GET_USER_CONVERSATIONS, GET_CONVERSATION_MESSAGES, DELETE_CONVERSATION } from "@/lib/graphql-queries";
import type { AgentResponse, ChatMessage, Task, TaskComplete } from "@/types";
import { DashboardHeader } from "@/components/chat/DashboardHeader";
import { TaskList } from "@/components/chat/TaskList";
import { TaskHeader } from "@/components/chat/TaskHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";
import { WorkflowModal } from "@/components/chat/WorkflowModal";
import { LogsModal } from "@/components/chat/LogsModal";

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
  const addLog = useAddLog();
  const clearLogs = useClearLogs();
  const logs = useLogs();
  
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
    showCompiledModal,
    showLogsModal,
    setShowCompiledModal,
    setShowLogsModal,
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
  } = useAppStore();

  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [copiedWorkflow, setCopiedWorkflow] = useState(false);
  const [currentSubscriptionTaskId, setCurrentSubscriptionTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [deleteConversationMutation] = useMutation<{ deleteConversation: { success: boolean; error?: string; deletedCount?: number } }>(DELETE_CONVERSATION);
  const [askAgent] = useLazyQuery<{ askAgent: AgentResponse }, { message: string; sessionId?: string }>(ASK_AGENT_QUERY);
  const [loadConversations, { data: conversationsData, loading: loadingConversations, error: conversationsError }] = useLazyQuery(GET_USER_CONVERSATIONS, {
    fetchPolicy: 'network-only',
  });
  const [loadMessages, { error: messagesError }] = useLazyQuery(GET_CONVERSATION_MESSAGES, {
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
    resetConversationState();
    setCurrentTask(taskId);
    
    const { data, error } = await loadMessages({ variables: { sessionId: taskId } });
    
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
  }, [loadMessages, resetConversationState, setCurrentTask, updateConversation]);

  useEffect(() => {
    if (user) loadConversations();
  }, [user, loadConversations]);

  useEffect(() => {
    if (conversationsData?.getUserConversations) {
      const allConversations = conversationsData.getUserConversations;

      if (process.env.NODE_ENV === 'development') {
        console.groupCollapsed(`Conversations: ${allConversations.length}`);
        
        (async () => {
          for (let i = 0; i < allConversations.length; i++) {
            const conv = allConversations[i];
            try {
              const { data } = await apolloClient.query({
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

      const conversationTasks: Task[] = allConversations
        .filter((conv: any) => conv.chatName && conv.chatName.trim() !== '')
        .map((conv: any) => ({
          id: conv.sessionId,
          name: conv.chatName,
          status: 'paused' as TaskStatus,
          type: 'automation' as const,
          lastModifiedAt: conv.lastModifiedAt,
          lastRun: conv.lastModifiedAt,
          connectedApps: [],
          description: conv.chatName,
          chatHistory: [],
          compiledWorkflow: { trigger: { type: 'polling', interval: '', app: '' }, steps: [], errorHandling: {} },
          logs: [],
          stats: { totalRuns: 0 },
        }));

      setConversations(conversationTasks);

      if (conversationTasks.length > 0 && currentTaskId === undefined) {
        handleTaskClick(conversationTasks[0].id);
      }
    }
  }, [conversationsData, currentTaskId, setConversations, handleTaskClick, addLog]);

  useEffect(() => {
    const msg = searchParams.get("msg");
    if (!msg) return;
    router.replace("/dashboard");
    handleNewTaskWithMessage(msg);
  }, [searchParams]);

  useEffect(() => {
    if (!currentSubscriptionTaskId || !currentTask) return;

    console.log('[Subscription] Starting for taskId:', currentSubscriptionTaskId);

    const subscription = apolloClient.subscribe<{ onTaskComplete: TaskComplete }>({
      query: TASK_COMPLETE_SUBSCRIPTION,
      variables: { taskId: currentSubscriptionTaskId },
    }).subscribe({
      next: ({ data }) => {
        console.log('[Subscription] Received data:', data);
        if (!data?.onTaskComplete) return;

        const { status, result, error: taskError, timestamp } = data.onTaskComplete;
        const isSuccess = status === 'COMPLETED';

        let parsedResult: any = null;
        try { parsedResult = result ? JSON.parse(result) : null; } catch (err) {}

        const chatName = parsedResult?.chatName || "";
        const assistantMessage: ChatMessage = {
          id: `msg_${Date.now() + 1}`,
          role: "assistant",
          content: isSuccess ? (parsedResult?.response || 'Task completed') : 'Agent Error: ' + (taskError || 'Unknown error'),
          timestamp: new Date().toISOString(),
        };

        const existingTask = tasks.find(t => t.id === currentTask.id);
        if (!existingTask && chatName) {
          const pendingMsgs = useAppStore.getState().pendingMessages;
          const newTask: Task = {
            id: currentTask.id,
            name: chatName,
            status: isSuccess ? "completed" as TaskStatus : "failed" as TaskStatus,
            type: "automation" as const,
            lastModifiedAt: new Date().toISOString(),
            lastRun: timestamp,
            connectedApps: [],
            description: chatName,
            chatHistory: [...pendingMsgs, assistantMessage],
            compiledWorkflow: { trigger: { type: "polling", interval: "", app: "" }, steps: [], errorHandling: {} },
            logs: [],
            stats: { totalRuns: 0 },
          };
          addConversation(newTask);
          clearPendingMessages();
          setCurrentTask(currentTask.id);
        } else {
          updateConversation(currentTask.id, {
            name: chatName || currentTask.name,
            chatHistory: [...currentTask.chatHistory, assistantMessage],
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
        addMessageToConversation(currentTask.id, errorMessage);
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
    };
  }, [currentSubscriptionTaskId, currentTask, apolloClient, loadConversations, tasks, addConversation, updateConversation, addMessageToConversation]);

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
    if (optionValue === "integrations") { router.push("/integrations"); return; }

    addLog("Option clicked", "info", optionLabel);
    setIsTyping(true);

    try {
      const { response, hasTaskId, sessionId } = await sendMessageToAgent(optionLabel, null);

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

    try {
      const { response, hasTaskId, sessionId } = await sendMessageToAgent(message, null);

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

  const handleToggleStatus = () => {
    if (!currentTask) return;
    const newStatus: TaskStatus = currentTask.status === "running" ? "paused" : "running";
    updateConversation(currentTask.id, { status: newStatus });
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

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="dashboard-page">
      <DashboardHeader
        connectedIntegrations={connectedIntegrations}
        onIntegrationsClick={() => router.push("/integrations")}
        onSettingsClick={() => router.push("/settings")}
        UserButtonComponent={UserButtonComponent}
      />

      <div className="flex-1 flex">
        <TaskList
          tasks={tasks}
          currentTaskId={currentTaskId}
          onTaskClick={handleTaskClick}
          onNewTask={handleNewTask}
          onDeleteTask={handleDeleteTask}
        />

        <main className="flex-1 flex flex-col">
          {currentTask ? (
            <>
              <TaskHeader
                task={currentTask}
                onShowWorkflow={() => setShowCompiledModal(true)}
                onShowLogs={() => setShowLogsModal(true)}
              />
              <ChatArea
                messages={currentTask.chatHistory}
                isTyping={isTyping}
                user={user}
                onOptionClick={handleOptionClick}
              />
            </>
          ) : (
            <ChatArea
              messages={[]}
              isTyping={isTyping}
              user={user}
              onOptionClick={handleOptionClick}
            />
          )}

          <ChatInput
            value={chatInput}
            onChange={setChatInput}
            onSubmit={handleSendMessage}
            onIntegrationsClick={() => router.push("/integrations")}
            onWorkflowClick={() => setShowCompiledModal(true)}
            onLogsClick={() => setShowLogsModal(true)}
            disabled={isTyping}
          />
        </main>
      </div>

      <WorkflowModal
        open={showCompiledModal}
        onOpenChange={setShowCompiledModal}
        task={currentTask}
        onToggleStatus={handleToggleStatus}
        onCopyWorkflow={handleCopyWorkflow}
        copiedWorkflow={copiedWorkflow}
      />

      <LogsModal
        open={showLogsModal}
        onOpenChange={setShowLogsModal}
        task={currentTask}
      />

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