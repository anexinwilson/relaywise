export interface Integration {
  id: string;
  name: string;
  description: string;
  logo: string;
  category: string;
  supportsRealtime: boolean;
}

export interface ConnectedIntegration {
  id: string;
  connectedAt: string;
  status: "active" | "inactive" | "error";
}

export interface MessageOption {
  label: string;
  value: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  options?: MessageOption[];
}

export interface WorkflowStep {
  step: number;
  app: string;
  action: string;
  config?: Record<string, unknown>;
  input?: string;
  condition?: string;
}

export interface CompiledWorkflow {
  trigger: {
    type: "polling" | "webhook" | "schedule";
    interval?: string;
    cron?: string;
    timezone?: string;
    event?: string;
    app: string;
  };
  steps: WorkflowStep[];
  errorHandling: Record<string, string>;
}

export interface TaskLog {
  timestamp: string;
  level: "info" | "success" | "warning" | "error";
  message: string;
}

export interface TaskStats {
  totalRuns: number;
  [key: string]: number | string;
}

export interface Task {
  id: string;
  name: string;
  status: "running" | "paused" | "failed" | "completed";
  type: "automation" | "query";
  lastModifiedAt: string;
  lastRun: string;
  connectedApps: string[];
  description: string;
  chatHistory: ChatMessage[];
  compiledWorkflow?: CompiledWorkflow;
  stats: TaskStats;
}

export interface UserUsage {
  thisMonth: {
    llmCalls: number;
    mcpCalls: number;
    activeAutomations: number;
    queries: number;
    storageUsedMB: number;
  };
  limits: {
    activeAutomations: number;
    queries: number;
    storageMB: number;
  };
  dailyLLMCalls: Array<{ date: string; calls: number }>;
  mcpCallsByIntegration: Record<string, number>;
}

export interface UserPreferences {
  theme: "dark" | "light";
  notifications: {
    email: boolean;
    inApp: boolean;
  };
  autoPauseAfterFailures: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar: string;
  tier: "free" | "pro";
  usage: UserUsage;
  connectedIntegrations: ConnectedIntegration[];
  preferences: UserPreferences;
  createdAt: string;
}

export interface IntegrationsData {
  popular: Integration[];
  categories: Record<
    string,
    {
      name: string;
      icon: string;
      apps: string[];
    }
  >;
}

// GraphQL Types
export interface AgentResponse {
  success: boolean;
  response: string;
  error: string | null;
  taskId: string;
  sessionId: string;
}

export interface TaskComplete {
  taskId: string;
  userId: string;
  status: string;
  result: unknown;
  error: string | null;
  executionTime: number;
  timestamp: string;
}

export interface AgentEvent {
  taskId: string;
  category: string;
  message: string;
  timestamp: string;
}

export interface ConversationSummary {
  sessionId: string;
  chatName: string;
  lastModifiedAt: string;
}

export interface ConversationMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  timestamp: string;
  type?: string;
}

export interface UserResponse {
  userId: string;
  email: string;
  name: string;
  tier: string;
  apiCallCount: number;
}
