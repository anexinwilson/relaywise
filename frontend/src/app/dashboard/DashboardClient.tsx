"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useLazyQuery, useApolloClient } from "@apollo/client/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Send,
  Plus,
  Settings,
  Plug,
  Wrench,
  BarChart3,
  Play,
  Pause,
  Copy,
  Check,
  ChevronRight,
  User,
} from "lucide-react";
import { useAppStore, useConnectedIntegrations } from "@/store/appStore";
import {
  ASK_AGENT_QUERY,
  TASK_COMPLETE_SUBSCRIPTION,
  GET_USER_CONVERSATIONS,
  GET_CONVERSATION_MESSAGES,
} from "@/lib/graphql-queries";
import { cn } from "@/lib/utils";
import type {
  AgentResponse,
  ChatMessage,
  Task,
  TaskComplete,
  TaskLog,
} from "@/types";

type TaskStatus = "running" | "paused" | "failed" | "completed";

const statusColors: Record<TaskStatus, string> = {
  running: "bg-success",
  paused: "bg-muted-foreground",
  failed: "bg-destructive",
  completed: "bg-primary",
};

const statusIcons: Record<TaskStatus, string> = {
  running: "🟢",
  paused: "⏸️",
  failed: "🔴",
  completed: "✅",
};

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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const apolloClient = useApolloClient();
  
  // Use user from props
  const [UserButtonComponent, setUserButtonComponent] = useState<React.ComponentType<{ afterSignOutUrl?: string }> | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    // Load UserButton component if user is authenticated
    if (user) {
      import("@clerk/nextjs").then((clerk) => {
        setUserButtonComponent(() => clerk.UserButton);
      }).catch(() => {
        // Clerk not available
      });
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
  } = useAppStore();

  // Local state for tasks and chat
  const [tasks, setTasks] = useState<Task[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [copiedWorkflow, setCopiedWorkflow] = useState(false);
  const [currentSubscriptionTaskId, setCurrentSubscriptionTaskId] = useState<string | null>(null);

  const [askAgent] = useLazyQuery<{ askAgent: AgentResponse }, { message: string }>(
    ASK_AGENT_QUERY
  );

  const [loadConversations, { data: conversationsData }] = useLazyQuery(GET_USER_CONVERSATIONS);
  const [loadMessages] = useLazyQuery(GET_CONVERSATION_MESSAGES);

  useEffect(() => {
    if (user) {
      loadConversations();
    }
  }, [user, loadConversations]);

  useEffect(() => {
    if (conversationsData?.getUserConversations) {
      console.log('Loaded conversations:', conversationsData.getUserConversations);
      
      // Convert AgentCore conversations to Task format
      const conversationTasks: Task[] = conversationsData.getUserConversations.map((conv: any) => ({
        id: conv.sessionId,
        name: conv.chatName || 'New Conversation',
        status: 'paused' as TaskStatus,
        type: 'automation' as const,
        createdAt: conv.createdAt,
        lastRun: '',
        connectedApps: [],
        description: conv.chatName || 'Conversation',
        chatHistory: [],
        compiledWorkflow: {
          trigger: { type: 'polling', interval: '', app: '' },
          steps: [],
          errorHandling: {},
        },
        logs: [],
        stats: { totalRuns: 0 },
      }));
      
      setTasks(conversationTasks);
      
      // Set the first conversation as current if none selected
      if (conversationTasks.length > 0 && !currentTaskId) {
        setCurrentTask(conversationTasks[0].id);
      }
    }
  }, [conversationsData]);

  // Handle pre-filled message from landing page
  useEffect(() => {
    const msg = searchParams.get("msg");
    if (!msg) return;

    // Clear the query param
    router.replace("/dashboard");

    // Create a new task and send the message
    handleNewTaskWithMessage(msg);
  }, [searchParams]);

  const currentTask = tasks.find((t) => t.id === currentTaskId) || tasks[0];

  // Subscribe to task completion using Apollo client directly
  useEffect(() => {
    if (!currentSubscriptionTaskId || !currentTask) return;

    const subscription = apolloClient.subscribe<{ onTaskComplete: TaskComplete }>({
      query: TASK_COMPLETE_SUBSCRIPTION,
      variables: { taskId: currentSubscriptionTaskId },
    }).subscribe({
      next: ({ data }) => {
        if (!data?.onTaskComplete) return;

        const { status, result, error, executionTime, timestamp } = data.onTaskComplete;
        const isSuccess = status === 'COMPLETED';

        // Parse the result JSON string
        let parsedResult: any = null;
        try {
          parsedResult = result ? JSON.parse(result) : null;
        } catch (err) {
          console.error('Failed to parse result JSON:', err);
        }

        // Add assistant message with the result
        const assistantMessage: ChatMessage = {
          id: `msg_${Date.now() + 1}`,
          role: "assistant",
          content: isSuccess
            ? (parsedResult?.response || 'Task completed')
            : 'Agent Error: ' + (error || 'Unknown error'),
          timestamp: new Date().toISOString(),
        };

        setTasks((prev) =>
          prev.map((task) =>
            task.id === currentTask.id
              ? {
                  ...task,
                  name: parsedResult?.chatName ?? task.name,
                  chatHistory: [...task.chatHistory, assistantMessage],
                  status: isSuccess ? "completed" : "failed",
                  lastRun: timestamp,
                }
              : task
          )
        );

        setCurrentSubscriptionTaskId(null);
        setIsTyping(false);
      },
      error: (err) => {
        console.error('Subscription error:', err);
        
        const errorMessage: ChatMessage = {
          id: `msg_${Date.now() + 1}`,
          role: "assistant",
          content: `Subscription Error: ${err.message || 'Lost connection to real-time updates'}`,
          timestamp: new Date().toISOString(),
        };

        setTasks((prev) =>
          prev.map((task) =>
            task.id === currentTask.id
              ? { ...task, chatHistory: [...task.chatHistory, errorMessage] }
              : task
          )
        );

        setCurrentSubscriptionTaskId(null);
        setIsTyping(false);
      }
    });

    return () => subscription.unsubscribe();
  }, [currentSubscriptionTaskId, currentTask, apolloClient]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentTask?.chatHistory]);

  // Send message to agent via Apollo
  const sendMessageToAgent = async (message: string): Promise<{ response: string; hasTaskId: boolean }> => {
    try {
      const { data, error } = await askAgent({
        variables: { message },
      });

      const result = data?.askAgent;

      if (error) {
        console.error("askAgent GraphQL error:", error);

        const graphQLErrors = (error as any).graphQLErrors;
        const networkError = (error as any).networkError;

        if (graphQLErrors && graphQLErrors.length > 0) {
          const messages = graphQLErrors.map((e: any) => e.message).join("; ");
          return { response: `AgentCore GraphQL error: ${messages}`, hasTaskId: false };
        }

        if (networkError) {
          const status = networkError.statusCode || networkError.status;
          const messageText =
            networkError.message || "Network error contacting AppSync/AgentCore.";
          return { response: `Network error (${status ?? "unknown"}): ${messageText}`, hasTaskId: false };
        }
      }

      if (!result) {
        console.error("askAgent returned no data");
        return { response: "AgentCore did not return any data. Please try again in a moment.", hasTaskId: false };
      }

      if (!result.success) {
        console.error("askAgent error:", result.error);
        return {
          response: result.error || "The agent could not process your request. Check that AgentCore is running and reachable from AppSync.",
          hasTaskId: false
        };
      }

      // If a task was started, subscribe to its updates
      if (result.taskId) {
        setCurrentSubscriptionTaskId(result.taskId);
        return { response: result.response || "", hasTaskId: true };
      }

      return { response: result.response || "The agent did not return a response.", hasTaskId: false };
    } catch (error) {
      // Surface a concise but informative error back into the chat
      console.error("Error sending message to agent:", error);

      const anyError = error as any;
      const graphQLErrors = anyError?.graphQLErrors;
      const networkError = anyError?.networkError;

      if (graphQLErrors && graphQLErrors.length > 0) {
        const messages = graphQLErrors.map((e: any) => e.message).join("; ");
        return { response: `AgentCore GraphQL error: ${messages}`, hasTaskId: false };
      }

      if (networkError) {
        const status = networkError.statusCode || networkError.status;
        const message = networkError.message || "Network error contacting AppSync/AgentCore.";
        return { response: `Network error (${status ?? "unknown"}): ${message}`, hasTaskId: false };
      }

      if (anyError?.message) {
        return { response: `Error contacting agent: ${anyError.message}`, hasTaskId: false };
      }

      return { response: "I'm having trouble connecting to the backend. Please check that AgentCore and AppSync are reachable, then try again.", hasTaskId: false };
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !currentTask) return;

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: "user",
      content: chatInput,
      timestamp: new Date().toISOString(),
    };

    // Add user message to chat
    setTasks((prev) =>
      prev.map((task) =>
        task.id === currentTask.id
          ? { ...task, chatHistory: [...task.chatHistory, userMessage] }
          : task
      )
    );

    const messageText = chatInput;
    setChatInput("");
    setIsTyping(true);

    try {
      // Send to agent and get response
      const { response, hasTaskId } = await sendMessageToAgent(messageText);

      // If a task was started, don't add a message yet
      // The subscription will handle adding the final response
      if (hasTaskId) {
        // Keep isTyping true, subscription will set it to false
        // Don't run the finally block by returning
        return;
      }

      const assistantMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: "assistant",
        content: response,
        timestamp: new Date().toISOString(),
      };

      setTasks((prev) =>
        prev.map((task) =>
          task.id === currentTask.id
            ? { ...task, chatHistory: [...task.chatHistory, assistantMessage] }
            : task
        )
      );
      
      setIsTyping(false);
    } catch (error) {
      console.error("Error:", error);
      setIsTyping(false);
    }
  };

  const handleOptionClick = (optionValue: string, optionLabel: string) => {
    if (!currentTask) return;

    if (optionValue === "integrations") {
      router.push("/integrations");
      return;
    }

    // Add user selection as message
    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: "user",
      content: optionLabel,
      timestamp: new Date().toISOString(),
    };

    setTasks((prev) =>
      prev.map((task) =>
        task.id === currentTask.id
          ? { ...task, chatHistory: [...task.chatHistory, userMessage] }
          : task
      )
    );

    setIsTyping(true);

    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: "assistant",
        content:
          optionValue === "search"
            ? "What would you like to search for? I can look across Gmail, Slack, Discord, Google Drive, and more."
            : "What would you like to automate? Describe what should happen and when.",
        timestamp: new Date().toISOString(),
      };

      setTasks((prev) =>
        prev.map((task) =>
          task.id === currentTask.id
            ? { ...task, chatHistory: [...task.chatHistory, assistantMessage] }
            : task
        )
      );
      setIsTyping(false);
    }, 1000);
  };

  const handleNewTask = () => {
    resetConversationState();
    const newTask: Task = {
      id: `task_${Date.now()}`,
      name: "New Automation",
      status: "paused",
      type: "automation",
      createdAt: new Date().toISOString(),
      lastRun: "",
      connectedApps: [],
      description: "New automation task",
      chatHistory: [
        {
          id: "msg_1",
          role: "assistant",
          content:
            "Hi! I'm ready to help you create a new automation. What would you like to automate?",
          timestamp: new Date().toISOString(),
          options: [
            { label: "🔍 Search across apps", value: "search" },
            { label: "⚡ Set up automation", value: "automate" },
            { label: "🔌 Connect more apps", value: "integrations" },
          ],
        },
      ],
      compiledWorkflow: {
        trigger: { type: "polling", interval: "", app: "" },
        steps: [],
        errorHandling: {},
      },
      logs: [],
      stats: { totalRuns: 0 },
    };
    setTasks((prev) => [newTask, ...prev]);
    setCurrentTask(newTask.id);
  };

  const handleNewTaskWithMessage = async (message: string) => {
    resetConversationState();
    const newTask: Task = {
      id: `task_${Date.now()}`,
      name: "New Automation",
      status: "paused",
      type: "automation",
      createdAt: new Date().toISOString(),
      lastRun: "",
      connectedApps: [],
      description: message,
      chatHistory: [
        {
          id: "msg_1",
          role: "assistant",
          content:
            "Hi! I'm ready to help you create a new automation. What would you like to automate?",
          timestamp: new Date().toISOString(),
        },
        {
          id: `msg_${Date.now()}`,
          role: "user",
          content: message,
          timestamp: new Date().toISOString(),
        },
      ],
      compiledWorkflow: {
        trigger: { type: "polling", interval: "", app: "" },
        steps: [],
        errorHandling: {},
      },
      logs: [],
      stats: { totalRuns: 0 },
    };
    setTasks((prev) => [newTask, ...prev]);
    setCurrentTask(newTask.id);

    // Send message to agent
    setIsTyping(true);
    try {
      const { response, hasTaskId } = await sendMessageToAgent(message);
      
      // If a task was started, don't add a message yet
      // The subscription will handle adding the final response
      if (hasTaskId) {
        // Keep isTyping true, subscription will set it to false
        return;
      }
      
      const assistantMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: "assistant",
        content: response,
        timestamp: new Date().toISOString(),
      };
      setTasks((prev) =>
        prev.map((task) =>
          task.id === newTask.id
            ? { ...task, chatHistory: [...task.chatHistory, assistantMessage] }
            : task
        )
      );
      
      setIsTyping(false);
    } catch (error) {
      console.error("Error:", error);
      setIsTyping(false);
    }
  };

  const handleTaskClick = async (taskId: string) => {
    resetConversationState();
    setCurrentTask(taskId);
    
    // Load messages for this conversation
    try {
      const { data } = await loadMessages({
        variables: { sessionId: taskId },
      });
      
      if (data?.getConversationMessages) {
        const messages: ChatMessage[] = data.getConversationMessages.map((msg: any) => ({
          id: msg.id,
          role: msg.sender === 'user' ? 'user' : 'assistant',
          content: msg.content,
          timestamp: msg.timestamp,
        }));
        
        // Update the task with loaded messages
        setTasks((prev) =>
          prev.map((task) =>
            task.id === taskId
              ? { ...task, chatHistory: messages }
              : task
          )
        );
      }
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const handleToggleStatus = () => {
    if (!currentTask) return;
    const newStatus: TaskStatus =
      currentTask.status === "running" ? "paused" : "running";
    setTasks((prev) =>
      prev.map((task) =>
        task.id === currentTask.id ? { ...task, status: newStatus } : task
      )
    );
  };

  const handleCopyWorkflow = () => {
    if (currentTask?.compiledWorkflow) {
      navigator.clipboard.writeText(
        JSON.stringify(currentTask.compiledWorkflow, null, 2)
      );
      setCopiedWorkflow(true);
      setTimeout(() => setCopiedWorkflow(false), 2000);
    }
  };

  // Initialize with a default task if none exist
  useEffect(() => {
    if (tasks.length === 0) {
      handleNewTask();
    }
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="dashboard-page">
      {/* Top Bar */}
      <header className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/cognive-logo.svg"
            alt="Cognive"
            width={32}
            height={32}
            className="rounded-lg"
          />
          <span className="text-lg font-bold text-foreground hidden sm:inline">
            Cognive
          </span>
        </Link>

        {/* Connected Apps */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground hidden md:inline">
            <Plug className="w-4 h-4 inline mr-1" />
            CONNECTED ({connectedIntegrations.length})
          </span>
          <div className="flex items-center gap-1">
            {connectedIntegrations.slice(0, 5).map((app) => (
              <Image
                key={app.id}
                src={app.logo}
                alt={app.name}
                width={28}
                height={28}
                className="rounded-lg"
                unoptimized
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.src = `https://ui-avatars.com/api/?name=${app.name}&background=374151&color=fff&size=28`;
                }}
              />
            ))}
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-primary"
              onClick={() => router.push("/integrations")}
            >
              + Add
            </Button>
          </div>
        </div>

        {/* User Menu */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/settings")}
          >
            <Settings className="w-5 h-5" />
          </Button>
          {UserButtonComponent ? <UserButtonComponent afterSignOutUrl="/" /> : (
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <User className="w-4 h-4 text-primary" />
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Task List */}
        <aside className="w-64 border-r border-border bg-card hidden md:flex flex-col">
          <div className="p-4 border-b border-border">
            <h2 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
              📋 MY TASKS
            </h2>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {tasks.map((task) => (
                <button
                  key={task.id}
                  onClick={() => handleTaskClick(task.id)}
                  className={cn(
                    "w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors",
                    currentTaskId === task.id
                      ? "bg-primary/20 text-foreground"
                      : "hover:bg-muted text-muted-foreground hover:text-foreground"
                  )}
                  data-testid={`task-item-${task.id}`}
                >
                  <span>{statusIcons[task.status] || "⚪"}</span>
                  <span className="flex-1 truncate text-sm">{task.name}</span>
                  <ChevronRight className="w-4 h-4 opacity-50" />
                </button>
              ))}
            </div>
          </ScrollArea>
          <div className="p-4 border-t border-border">
            <Button
              variant="outline"
              className="w-full gap-2"
              onClick={handleNewTask}
              data-testid="new-task-btn"
            >
              <Plus className="w-4 h-4" />
              New Task
            </Button>
          </div>
        </aside>

        {/* Center - Chat Area */}
        <main className="flex-1 flex flex-col">
          {currentTask ? (
            <>
              {/* Task Header */}
              <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-card/50">
                <div className="flex items-center gap-3">
                  <span className="text-xl">💬</span>
                  <h1 className="font-semibold text-foreground">
                    {currentTask.name}
                  </h1>
                  <span
                    className={cn(
                      "w-2 h-2 rounded-full",
                      statusColors[currentTask.status]
                    )}
                  />
                </div>
                <div className="flex items-center gap-2">
                  {currentTask.type === "automation" &&
                    currentTask.compiledWorkflow?.steps &&
                    currentTask.compiledWorkflow.steps.length > 0 && (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-2"
                          onClick={() => setShowCompiledModal(true)}
                        >
                          <Wrench className="w-4 h-4" />
                          <span className="hidden sm:inline">Workflow</span>
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-2"
                          onClick={() => setShowLogsModal(true)}
                        >
                          <BarChart3 className="w-4 h-4" />
                          <span className="hidden sm:inline">Logs</span>
                        </Button>
                      </>
                    )}
                </div>
              </div>

              {/* Messages */}
              <ScrollArea className="flex-1 p-4">
                <div className="max-w-3xl mx-auto space-y-4">
                  <AnimatePresence mode="popLayout">
                    {currentTask.chatHistory.map((message) => (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className={cn(
                          "flex gap-3",
                          message.role === "user"
                            ? "justify-end"
                            : "justify-start"
                        )}
                      >
                        {message.role === "assistant" && (
                          <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center flex-shrink-0">
                            <span className="text-white text-sm font-bold">
                              C
                            </span>
                          </div>
                        )}
                        <div
                          className={cn(
                            "max-w-md rounded-2xl p-4",
                            message.role === "user"
                              ? "bg-primary text-primary-foreground"
                              : "bg-card border border-border"
                          )}
                        >
                          <p className="text-sm whitespace-pre-line">
                            {message.content}
                          </p>
                          {message.options && message.role === "assistant" && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {message.options.map((option, i) => (
                                <Button
                                  key={i}
                                  variant="outline"
                                  size="sm"
                                  className="h-8"
                                  onClick={() =>
                                    handleOptionClick(option.value, option.label)
                                  }
                                >
                                  {option.label}
                                </Button>
                              ))}
                            </div>
                          )}
                        </div>
                        {message.role === "user" && (
                          <Avatar className="w-8 h-8 flex-shrink-0">
                            <AvatarImage src={user?.imageUrl} />
                            <AvatarFallback>
                              {user?.firstName?.charAt(0) || "U"}
                            </AvatarFallback>
                          </Avatar>
                        )}
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {isTyping && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex gap-3"
                    >
                      <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                        <span className="text-white text-sm font-bold">C</span>
                      </div>
                      <div className="bg-card border border-border rounded-2xl p-4">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                          <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:0.1s]" />
                          <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:0.2s]" />
                        </div>
                      </div>
                    </motion.div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {/* Chat Input */}
              <div className="p-4 border-t border-border bg-card/50">
                <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto">
                  <div className="flex gap-2">
                    <Input
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Type a message..."
                      className="flex-1 h-12 bg-background"
                      data-testid="chat-input"
                    />
                    <Button
                      type="submit"
                      className="h-12 px-6 gradient-primary hover:opacity-90"
                      data-testid="chat-submit-btn"
                    >
                      <Send className="w-4 h-4" />
                    </Button>
                  </div>
                  {/* Quick Actions */}
                  <div className="flex gap-2 mt-3">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground"
                      onClick={() => router.push("/integrations")}
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Integration
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground"
                      onClick={() => setShowCompiledModal(true)}
                    >
                      <Wrench className="w-4 h-4 mr-1" />
                      Workflow
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground"
                      onClick={() => setShowLogsModal(true)}
                    >
                      <BarChart3 className="w-4 h-4 mr-1" />
                      Logs
                    </Button>
                  </div>
                </form>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <p className="text-muted-foreground mb-4">No tasks yet</p>
                <Button onClick={handleNewTask} className="gradient-primary">
                  Create Your First Task
                </Button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Compiled Workflow Modal */}
      <Dialog open={showCompiledModal} onOpenChange={setShowCompiledModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              📋 Compiled Workflow
            </DialogTitle>
          </DialogHeader>
          {currentTask && (
            <div className="space-y-6">
              {/* Meta */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-foreground">
                    {currentTask.name}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Status:{" "}
                    <span
                      className={cn(
                        "capitalize",
                        currentTask.status === "running" && "text-success"
                      )}
                    >
                      {currentTask.status}
                    </span>
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleToggleStatus}
                >
                  {currentTask.status === "running" ? (
                    <>
                      <Pause className="w-4 h-4 mr-1" /> Pause
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-1" /> Resume
                    </>
                  )}
                </Button>
              </div>

              {/* Trigger */}
              <div>
                <h4 className="text-sm font-semibold text-muted-foreground mb-2">
                  📡 TRIGGER
                </h4>
                <div className="bg-background rounded-lg p-4 font-mono text-sm">
                  <p>
                    Type:{" "}
                    {currentTask.compiledWorkflow?.trigger?.type || "manual"}
                  </p>
                  {currentTask.compiledWorkflow?.trigger?.interval && (
                    <p>
                      Interval: {currentTask.compiledWorkflow.trigger.interval}
                    </p>
                  )}
                  {currentTask.compiledWorkflow?.trigger?.app && (
                    <p>App: {currentTask.compiledWorkflow.trigger.app}</p>
                  )}
                </div>
              </div>

              {/* Steps */}
              {currentTask.compiledWorkflow?.steps &&
                currentTask.compiledWorkflow.steps.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-muted-foreground mb-2">
                      🔄 WORKFLOW STEPS
                    </h4>
                    <div className="space-y-2">
                      {currentTask.compiledWorkflow.steps.map((step, i) => (
                        <div
                          key={i}
                          className="bg-background rounded-lg p-4 font-mono text-sm"
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <span className="w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs">
                              {i + 1}
                            </span>
                            <span className="text-foreground">
                              {step.app}.{step.action}
                            </span>
                          </div>
                          {step.config && (
                            <div className="pl-8 text-muted-foreground">
                              {Object.entries(step.config).map(
                                ([key, value]) => (
                                  <p key={key}>
                                    └─ {key}: {JSON.stringify(value)}
                                  </p>
                                )
                              )}
                            </div>
                          )}
                          {step.condition && (
                            <p className="pl-8 text-primary">
                              └─ condition: {step.condition}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Copy Button */}
              <Button
                variant="outline"
                className="w-full gap-2"
                onClick={handleCopyWorkflow}
              >
                {copiedWorkflow ? (
                  <>
                    <Check className="w-4 h-4" /> Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" /> Copy to Clipboard
                  </>
                )}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Logs Modal */}
      <Dialog open={showLogsModal} onOpenChange={setShowLogsModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              📊 Live Logs
            </DialogTitle>
          </DialogHeader>
          {currentTask && (
            <div className="space-y-4">
              {/* Stats */}
              {currentTask.stats && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="bg-background rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-foreground">
                      {currentTask.stats.totalRuns}
                    </p>
                    <p className="text-xs text-muted-foreground">Total Runs</p>
                  </div>
                  <div className="bg-background rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-foreground">
                      {(currentTask.stats.mentionsFound as number) || 0}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Mentions Found
                    </p>
                  </div>
                  <div className="bg-background rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-success">
                      {(currentTask.stats.uptime as string) || "100%"}
                    </p>
                    <p className="text-xs text-muted-foreground">Uptime</p>
                  </div>
                  <div className="bg-background rounded-lg p-3 text-center">
                    <p className="text-sm font-medium text-foreground">
                      {currentTask.lastRun
                        ? new Date(currentTask.lastRun).toLocaleTimeString()
                        : "Never"}
                    </p>
                    <p className="text-xs text-muted-foreground">Last Run</p>
                  </div>
                </div>
              )}

              {/* Log Entries */}
              <div className="bg-background rounded-lg p-4 font-mono text-sm max-h-80 overflow-auto">
                {currentTask.logs && currentTask.logs.length > 0 ? (
                  currentTask.logs.map((log: TaskLog, i: number) => (
                    <div
                      key={i}
                      className={cn(
                        "py-1",
                        log.level === "success" && "text-success",
                        log.level === "error" && "text-destructive",
                        log.level === "info" && "text-muted-foreground"
                      )}
                    >
                      <span className="opacity-50">
                        [{new Date(log.timestamp).toLocaleTimeString()}]
                      </span>{" "}
                      {log.message}
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground">No logs yet</p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
