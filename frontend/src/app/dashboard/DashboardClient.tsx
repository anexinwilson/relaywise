"use client";

import { useState, useEffect, useCallback, useRef, useSyncExternalStore } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLazyQuery, useMutation, useApolloClient } from "@apollo/client/react";
import {
  useAppStore,
  useConnectedIntegrations,
  useConversations,
  useCurrentConversation,
} from "@/store/appStore";
import {
  ASK_AGENT_QUERY,
  TASK_COMPLETE_SUBSCRIPTION,
  GET_USER_CONVERSATIONS,
  GET_CONVERSATION_MESSAGES,
  DELETE_CONVERSATION,
  ON_AGENT_EVENT,
} from "@/lib/graphql-queries";
import type {
  AgentResponse,
  ChatMessage,
  Task,
  TaskComplete,
  AgentEvent,
  ConversationMessage,
  ConversationSummary,
} from "@/types";
import { DashboardHeader } from "@/components/chat/DashboardHeader";
import { TaskList } from "@/components/chat/TaskList";
import { TaskHeader } from "@/components/chat/TaskHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";
import { CreditsDisplay } from "@/components/chat/CreditsDisplay";
import { parseAgentTaskResult } from "@/lib/agent-task-result";

type TaskStatus = "running" | "paused" | "failed" | "completed";

const subscribeToHydration = () => () => undefined;

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown error";
}

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

  const mounted = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false,
  );
  const isFirstLoad = useRef(true);
  // Whether the landing conversation has already been opened for this mount.
  const autoOpenedRef = useRef(false);
  // Track IDs we've just deleted so they don't re-appear via loadConversations
  const recentlyDeletedIds = useRef<Set<string>>(new Set());

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
    addMessageToConversation,
    addPendingMessage,
    setIsAppLoading,
    setIsChatLoading,
    isAppLoading,
    isChatLoading,
    creditsRefreshTrigger,
    triggerCreditsRefresh,
  } = useAppStore();

  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [currentSubscriptionTaskId, setCurrentSubscriptionTaskId] = useState<
    string | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [thinkingLogs, setThinkingLogs] = useState<AgentEvent[]>([]);

  const [deleteConversationMutation] = useMutation<{
    deleteConversation: { success: boolean; error?: string; deletedCount?: number };
  }>(DELETE_CONVERSATION);
  const [askAgent] = useLazyQuery<
    { askAgent: AgentResponse },
    { message: string; sessionId?: string }
  >(ASK_AGENT_QUERY);
  const [loadConversations, { data: conversationsData, error: conversationsError }] =
    useLazyQuery<{ getUserConversations: ConversationSummary[] }>(
      GET_USER_CONVERSATIONS,
      {
        fetchPolicy: "network-only",
      },
    );
  const [loadMessages, { error: messagesError }] = useLazyQuery<
    { getConversationMessages: ConversationMessage[] },
    { sessionId: string }
  >(GET_CONVERSATION_MESSAGES, {
    fetchPolicy: "network-only",
  });

  const tasks = useConversations();
  const currentTask = useCurrentConversation();

  useEffect(() => {
    if (conversationsError)
      console.error("[Conversations] Load failed:", conversationsError.message);
  }, [conversationsError]);

  useEffect(() => {
    if (messagesError) console.error("[Messages] Load failed:", messagesError.message);
  }, [messagesError]);

  const handleTaskClick = useCallback(
    async (taskId: string) => {
      // 1. Get the current task immediately from Zustand to check its cache
      const currentTasks = useAppStore.getState().conversations;
      const cachedTask = currentTasks.find((t) => t.id === taskId);
      const hasCachedHistory =
        cachedTask && cachedTask.chatHistory && cachedTask.chatHistory.length > 0;

      resetConversationState();
      setCurrentTask(taskId);

      // 2. Only show the loading skeleton if this chat is completely empty in Zustand
      if (!hasCachedHistory) {
        setIsChatLoading(true);
      }

      // 3. Background Sync: Fetch fresh data from AWS no matter what
      const { data } = await loadMessages({ variables: { sessionId: taskId } });

      // 4. Update Zustand silently
      if (data?.getConversationMessages) {
        const messages: ChatMessage[] = data.getConversationMessages.map((msg) => ({
          id: msg.id,
          role: msg.sender === "user" ? "user" : "assistant",
          content: msg.content,
          timestamp: msg.timestamp,
        }));
        updateConversation(taskId, { chatHistory: messages });
      }

      // 5. Turn off loader
      if (!hasCachedHistory) {
        setIsChatLoading(false);
      }
    },
    [
      loadMessages,
      resetConversationState,
      setCurrentTask,
      updateConversation,
      setIsChatLoading,
    ],
  );

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

      const currentStoreTasks = useAppStore.getState().conversations;

      const conversationTasks: Task[] = allConversations
        .filter((conv) => conv.chatName && conv.chatName.trim() !== "")
        // Filter out any IDs we recently deleted (Bedrock eventual consistency may return them)
        .filter((conv) => !recentlyDeletedIds.current.has(conv.sessionId))
        .map((conv) => {
          const existingTask = currentStoreTasks.find((t) => t.id === conv.sessionId);
          return {
            id: conv.sessionId,
            name: conv.chatName,
            status: "paused" as TaskStatus,
            type: "automation" as const,
            lastModifiedAt: conv.lastModifiedAt,
            lastRun: conv.lastModifiedAt,
            connectedApps: [],
            description: conv.chatName,
            chatHistory: existingTask?.chatHistory || [], // <-- Preserve from persist!
            compiledWorkflow: {
              trigger: { type: "polling", interval: "", app: "" },
              steps: [],
              errorHandling: {},
            },
            stats: { totalRuns: 0 },
          };
        });

      setConversations(conversationTasks);

      // Open the most recent conversation on arrival, once.
      //
      // Without the ref this re-fires whenever currentTaskId becomes null,
      // which is exactly what "New Task" does: the click cleared the
      // selection, this effect saw null and reopened the first conversation,
      // so the button appeared dead.
      if (
        autoOpenedRef.current === false &&
        conversationTasks.length > 0 &&
        currentTaskId === null
      ) {
        autoOpenedRef.current = true;
        handleTaskClick(conversationTasks[0].id);
      }

      setIsAppLoading(false);
    }
  }, [
    conversationsData,
    currentTaskId,
    setConversations,
    handleTaskClick,
    setIsAppLoading,
  ]);

  // Live progress events, subscribed for as long as a conversation is open.
  //
  // This used to share the effect below, gated on currentSubscriptionTaskId —
  // an id that exists only after askAgent returns, and is cleared again on
  // completion. But the worker starts broadcasting the moment it takes the
  // task off the queue, and AppSync does not replay what a subscriber missed.
  // A warm worker could therefore publish its entire run before the client
  // finished subscribing, which looked like no streaming at all: a spinner,
  // then the finished answer in one jump.
  //
  // onAgentEvent filters on the conversation id, so it never needed the task
  // id. Subscribing on currentTaskId alone puts the listener in place before
  // any run starts, which is the only way it cannot miss the opening events.
  useEffect(() => {
    if (!currentTaskId) return;

    console.log("[AgentEvents] Subscribing with taskId:", currentTaskId);
    const eventSubscription = apolloClient
      .subscribe<{ onAgentEvent: AgentEvent }>({
        query: ON_AGENT_EVENT,
        variables: { taskId: currentTaskId },
      })
      .subscribe({
        next: ({ data }) => {
          if (data?.onAgentEvent) {
            console.log("[AgentEvents] Received:", data.onAgentEvent);
            setThinkingLogs((prev) => [...prev, data.onAgentEvent]);
            // Scroll to bottom when thinking logs update
            setTimeout(() => {
              const chatBox = document.getElementById("chat-scroll-container");
              if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
            }, 50);
          }
        },
      });

    return () => eventSubscription.unsubscribe();
  }, [currentTaskId, apolloClient]);

  useEffect(() => {
    if (!currentSubscriptionTaskId || !currentTaskId) return;

    console.log("[Subscription] Starting for taskId:", currentSubscriptionTaskId);
    const subscription = apolloClient
      .subscribe<{ onTaskComplete: TaskComplete }>({
        query: TASK_COMPLETE_SUBSCRIPTION,
        variables: { taskId: currentSubscriptionTaskId },
      })
      .subscribe({
        next: ({ data }) => {
          console.log("[Subscription] Received data:", data);
          if (!data?.onTaskComplete) return;

          const freshState = useAppStore.getState();
          const freshCurrentTask = freshState.conversations.find(
            (t) => t.id === currentTaskId,
          );
          const freshTasks = freshState.conversations;

          const { status, result, error: taskError, timestamp } = data.onTaskComplete;
          const isSuccess = status === "COMPLETED";

          let parsedResult = null;
          try {
            parsedResult = parseAgentTaskResult(result);
          } catch {
            console.error("[Subscription] Agent returned invalid JSON");
          }

          const chatName = parsedResult?.chatName || "";
          const assistantMessage: ChatMessage = {
            id: `msg_${Date.now() + 1}`,
            role: "assistant",
            content: isSuccess
              ? parsedResult?.response || "Task completed"
              : "Agent Error: " + (taskError || "Unknown error"),
            timestamp: new Date().toISOString(),
          };

          const existingTask = freshTasks.find((t) => t.id === currentTaskId);
          if (!existingTask && chatName) {
            const pendingMsgs = freshState.pendingMessages;
            const newTask: Task = {
              id: currentTaskId,
              name: chatName,
              status: isSuccess ? ("completed" as TaskStatus) : ("failed" as TaskStatus),
              type: "automation" as const,
              lastModifiedAt: new Date().toISOString(),
              lastRun: timestamp,
              connectedApps: [],
              description: chatName,
              chatHistory: [...pendingMsgs, assistantMessage],
              compiledWorkflow: {
                trigger: { type: "polling", interval: "", app: "" },
                steps: [],
                errorHandling: {},
              },
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
              lastRun: timestamp,
            });
          }

          setCurrentSubscriptionTaskId(null);
          setIsTyping(false);
          triggerCreditsRefresh(); // Refresh credits after agent execution completes
        },
        error: (err) => {
          console.error("[Subscription] Error:", err);
          const errorMessage: ChatMessage = {
            id: `msg_${Date.now() + 1}`,
            role: "assistant",
            content: `Subscription Error: ${err.message || "Lost connection to real-time updates"}`,
            timestamp: new Date().toISOString(),
          };
          addMessageToConversation(currentTaskId, errorMessage);
          setCurrentSubscriptionTaskId(null);
          setIsTyping(false);
        },
        complete: () => {
          console.log("[Subscription] Completed");
        },
      });

    return () => {
      console.log("[Subscription] Unsubscribing from taskId:", currentSubscriptionTaskId);
      subscription.unsubscribe();
    };
  }, [
    currentSubscriptionTaskId,
    currentTaskId,
    apolloClient,
    addConversation,
    updateConversation,
    addMessageToConversation,
    setCurrentTask,
    triggerCreditsRefresh,
  ]);

  const sendMessageToAgent = useCallback(
    async (
      message: string,
      sessionId?: string,
    ): Promise<{ response: string; hasTaskId: boolean; sessionId?: string }> => {
      try {
        fetch("/api/integrations/connected")
          .then((res) => res.json())
          .then((data) => {
            if (data.slugs && Array.isArray(data.slugs)) {
              const currentIds = useAppStore.getState().connectedIntegrationIds;
              const newIds = data.slugs.filter(
                (slug: string) => !currentIds.includes(slug),
              );
              newIds.forEach((slug: string) => connectIntegration(slug));
            }
          })
          .catch(() => {});

        const { data, error } = await askAgent({ variables: { message, sessionId } });
        const result = data?.askAgent;

        if (error) {
          setError(error.message);
          return { response: "", hasTaskId: false };
        }

        if (!result) {
          setError("The agent did not return any data.");
          return { response: "", hasTaskId: false };
        }
        if (!result.success) {
          setError(result.error || "The agent could not process your request.");
          return { response: "", hasTaskId: false };
        }

        if (result.taskId) {
          setCurrentSubscriptionTaskId(result.taskId);
          return {
            response: result.response || "",
            hasTaskId: true,
            sessionId: result.sessionId,
          };
        }
        return { response: result.response || "", hasTaskId: false };
      } catch (error: unknown) {
        setError(`Error: ${getErrorMessage(error)}`);
        return { response: "", hasTaskId: false };
      }
    },
    [askAgent, connectIntegration],
  );

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const messageText = chatInput;
    setChatInput("");
    setError(null);
    setThinkingLogs([]);

    let taskId = currentTask?.id === "pending" ? null : currentTask?.id;

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
      const { response, hasTaskId, sessionId } = await sendMessageToAgent(
        messageText,
        taskId || undefined,
      );

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

      // A refused request (no credits, a rejected input) reports itself
      // through setError and returns an empty response. Appending that as a
      // message left an empty bubble sitting in the conversation once the
      // dialog was dismissed, which read as the agent having replied with
      // nothing.
      if (response.trim() && taskId) {
        addMessageToConversation(taskId, {
          id: `msg_${Date.now() + 1}`,
          role: "assistant",
          content: response,
          timestamp: new Date().toISOString(),
        });
      }
      setIsTyping(false);
    } catch {
      setIsTyping(false);
    }
  };

  const handleOptionClick = async (optionValue: string, optionLabel: string) => {
    setIsTyping(true);
    setThinkingLogs([]); // Instantly clear logs

    try {
      const { response, hasTaskId, sessionId } = await sendMessageToAgent(
        optionLabel,
        undefined,
      );

      if (sessionId) {
        setCurrentTask(sessionId);
        const userMessage: ChatMessage = {
          id: `msg_${Date.now()}`,
          role: "user",
          content: optionLabel,
          timestamp: new Date().toISOString(),
        };
        addMessageToConversation(sessionId, userMessage);
        if (hasTaskId) return;
        // Same guard as handleSendMessage: a refusal returns an empty
        // response, and an empty bubble is not a reply.
        if (response.trim()) {
          addMessageToConversation(sessionId, {
            id: `msg_${Date.now() + 1}`,
            role: "assistant",
            content: response,
            timestamp: new Date().toISOString(),
          });
        }
      }
    } catch (error: unknown) {
      console.error("[OptionClick] Error:", getErrorMessage(error));
    } finally {
      setIsTyping(false);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    const wasCurrentTask = currentTaskId === taskId;
    const taskIndex = tasks.findIndex((t) => t.id === taskId);
    const deletedTask = tasks[taskIndex];

    // Mark as deleted immediately so loadConversations refetches don't re-add it
    recentlyDeletedIds.current.add(taskId);
    removeConversation(taskId);

    if (wasCurrentTask) {
      const remaining = tasks.filter((t) => t.id !== taskId);
      if (remaining.length > 0) {
        const nextIndex = Math.min(taskIndex, remaining.length - 1);
        handleTaskClick(remaining[nextIndex].id);
      } else {
        resetConversationState();
        setCurrentTask(null);
      }
    }

    try {
      const { data } = await deleteConversationMutation({
        variables: { sessionId: taskId },
      });
      if (!data?.deleteConversation?.success) {
        // Only roll back if truly failed (not a partial success treated as success by backend)
        recentlyDeletedIds.current.delete(taskId);
        if (deletedTask) addConversation(deletedTask);
        setError(
          `Failed to delete conversation: ${data?.deleteConversation?.error || "Unknown error"}`,
        );
      }
      // On success: Zustand already has the correct state (item removed).
      // Do NOT call loadConversations() here — Bedrock eventual consistency
      // may still return the deleted session, causing it to re-appear.
    } catch (err: unknown) {
      recentlyDeletedIds.current.delete(taskId);
      if (deletedTask) addConversation(deletedTask);
      setError(`Failed to delete conversation: ${getErrorMessage(err)}`);
    }
  };

  const handleNewTask = () => {
    resetConversationState();
    setCurrentTask(null);
  };

  const handleNewTaskWithMessage = useCallback(
    async (message: string) => {
      resetConversationState();
      setIsTyping(true);
      setThinkingLogs([]); // Instantly clear logs

      try {
        const { response, hasTaskId, sessionId } = await sendMessageToAgent(
          message,
          undefined,
        );

        if (sessionId) {
          setCurrentTask(sessionId);
          const userMessage: ChatMessage = {
            id: `msg_${Date.now()}`,
            role: "user",
            content: message,
            timestamp: new Date().toISOString(),
          };
          addMessageToConversation(sessionId, userMessage);
        }

        if (hasTaskId) return;

        const assistantMessage: ChatMessage = {
          id: `msg_${Date.now() + 1}`,
          role: "assistant",
          content: response,
          timestamp: new Date().toISOString(),
        };
        if (sessionId) addMessageToConversation(sessionId, assistantMessage);
        setIsTyping(false);
      } catch {
        setIsTyping(false);
      }
    },
    [
      addMessageToConversation,
      resetConversationState,
      sendMessageToAgent,
      setCurrentTask,
    ],
  );

  useEffect(() => {
    const msg = searchParams.get("msg");
    if (!msg) return;
    router.replace("/dashboard");
    const timer = window.setTimeout(() => void handleNewTaskWithMessage(msg), 0);
    return () => window.clearTimeout(timer);
  }, [searchParams, router, handleNewTaskWithMessage]);

  useEffect(() => {
    if (isFirstLoad.current) {
      isFirstLoad.current = false;
    }
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <div
      className="h-screen bg-background flex flex-col overflow-hidden"
      data-testid="dashboard-page"
    >
      <DashboardHeader
        connectedIntegrations={connectedIntegrations}
        onIntegrationsClick={() => router.push("/integrations")}
        onSettingsClick={() => router.push("/settings")}
      />

      <div className="flex-1 flex min-h-0">
        <TaskList
          tasks={tasks}
          currentTaskId={currentTaskId}
          onTaskClick={handleTaskClick}
          onNewTask={handleNewTask}
          onDeleteTask={handleDeleteTask}
          isLoading={isAppLoading && tasks.length === 0}
          creditsUsed={0}
          creditsTotal={100}
        >
          <CreditsDisplay refreshTrigger={creditsRefreshTrigger} />
        </TaskList>

        <main className="flex-1 flex flex-col min-h-0">
          {currentTask ? (
            <>
              <TaskHeader task={currentTask} />
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
            disabled={isTyping}
          />
        </main>
      </div>

      {error && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card p-6 rounded-lg max-w-md mx-4">
            <h3 className="text-lg font-semibold text-destructive mb-2">
              Something went wrong
            </h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <button
              onClick={() => setError(null)}
              className="bg-primary text-primary-foreground cursor-pointer rounded px-4 py-2 hover:opacity-90"
            >
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
