import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Integration, Task, ChatMessage } from "@/types";
import appsCatalog from "@/apps_catalog.json";

const formattedIntegrations: Integration[] = (appsCatalog as any[]).map((app) => ({
  ...app,
  id: app.slug,
  supportsRealtime: false,
}));

// Conversation state for step-by-step chat flows
interface ConversationState {
  currentTree: string | null;
  currentStepIndex: number;
  collectedData: Record<string, string>;
  waitingForInput: boolean;
}

interface AppState {
  // UI State
  showIntegrationModal: boolean;
  selectedIntegration: Integration | null;
  setShowIntegrationModal: (
    show: boolean,
    integration?: Integration | null
  ) => void;

  // Current selections
  currentTaskId: string | null;
  setCurrentTask: (id: string | null) => void;

  // Pending messages (before sessionId is created)
  pendingMessages: ChatMessage[];
  addPendingMessage: (message: ChatMessage) => void;
  clearPendingMessages: () => void;

  // Conversations (stored in Zustand for persistence)
  conversations: Task[];
  setConversations: (conversations: Task[]) => void;
  addConversation: (conversation: Task) => void;
  removeConversation: (id: string) => void;
  updateConversation: (id: string, updates: Partial<Task>) => void;
  updateConversationId: (oldId: string, newId: string) => void;
  updateConversationName: (id: string, name: string) => void;
  addMessageToConversation: (id: string, message: ChatMessage) => void;

  // Conversation State (for step-by-step flows)
  conversationState: ConversationState;
  setConversationState: (state: Partial<ConversationState>) => void;
  resetConversationState: () => void;

  // Integrations (static list, connection status local)
  allIntegrations: Integration[];
  connectedIntegrationIds: string[];
  connectIntegration: (id: string) => void;
  disconnectIntegration: (id: string) => void;
  isIntegrationConnected: (id: string) => boolean;

  // Onboarding
  hasCompletedOnboarding: boolean;
  setHasCompletedOnboarding: (completed: boolean) => void;

  // Loading States
  isAppLoading: boolean;
  setIsAppLoading: (loading: boolean) => void;
  isChatLoading: boolean;
  setIsChatLoading: (loading: boolean) => void;

  // Credits
  creditsRefreshTrigger: number;
  triggerCreditsRefresh: () => void;
}

const initialConversationState: ConversationState = {
  currentTree: null,
  currentStepIndex: 0,
  collectedData: {},
  waitingForInput: false,
};

function sortByLastModified(conversations: Task[]): Task[] {
  return [...conversations].sort((a, b) => {
    if (!a.lastModifiedAt || !b.lastModifiedAt) return 0;
    return new Date(b.lastModifiedAt).getTime() - new Date(a.lastModifiedAt).getTime();
  });
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // UI State
      showIntegrationModal: false,
      selectedIntegration: null,
      setShowIntegrationModal: (show, integration = null) =>
        set({ showIntegrationModal: show, selectedIntegration: integration }),

      // Current selections
      currentTaskId: null,
      setCurrentTask: (id) => set({ currentTaskId: id }),

      // Pending messages
      pendingMessages: [],
      addPendingMessage: (message) =>
        set((state) => ({
          pendingMessages: [...state.pendingMessages, message],
        })),
      clearPendingMessages: () => set({ pendingMessages: [] }),

      // Conversations
      conversations: [],
      setConversations: (conversations) =>
        set(() => {
          const byId = new Map<string, Task>();
          conversations.forEach((conv) => {
            byId.set(conv.id, conv);
          });
          return { conversations: sortByLastModified(Array.from(byId.values())) };
        }),
      addConversation: (conversation) =>
        set((state) => {
          const byId = new Map<string, Task>();
          // Existing conversations (latest wins)
          state.conversations.forEach((conv) => {
            byId.set(conv.id, conv);
          });
          // New/updated conversation
          byId.set(conversation.id, conversation);
          return {
            conversations: sortByLastModified(Array.from(byId.values())),
          };
        }),
      removeConversation: (id) =>
        set((state) => ({
          conversations: state.conversations.filter((conv) => conv.id !== id),
        })),
      updateConversation: (id, updates) =>
        set((state) => ({
          conversations: sortByLastModified(state.conversations.map((conv) =>
            conv.id === id ? { ...conv, ...updates } : conv
          )),
        })),
      updateConversationId: (oldId, newId) =>
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === oldId ? { ...conv, id: newId } : conv
          ),
        })),
      updateConversationName: (id, name) =>
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id ? { ...conv, name } : conv
          ),
        })),
      addMessageToConversation: (id, message) =>
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id
              ? { ...conv, chatHistory: [...conv.chatHistory, message] }
              : conv
          ),
        })),

      // Conversation State
      conversationState: initialConversationState,
      setConversationState: (newState) =>
        set((state) => ({
          conversationState: { ...state.conversationState, ...newState },
        })),
      resetConversationState: () =>
        set({ conversationState: initialConversationState }),

      // Integrations
      allIntegrations: formattedIntegrations,
      connectedIntegrationIds: [],
      connectIntegration: (id) =>
        set((state) => ({
          connectedIntegrationIds: [
            ...new Set([...state.connectedIntegrationIds, id]),
          ],
        })),
      disconnectIntegration: (id) =>
        set((state) => ({
          connectedIntegrationIds: state.connectedIntegrationIds.filter(
            (i) => i !== id
          ),
        })),
      isIntegrationConnected: (id) => get().connectedIntegrationIds.includes(id),

      // Onboarding
      hasCompletedOnboarding: false,
      setHasCompletedOnboarding: (completed) =>
        set({ hasCompletedOnboarding: completed }),

      // Loading States
      isAppLoading: true, // true by default so it shows skeleton immediately on refresh
      setIsAppLoading: (loading) => set({ isAppLoading: loading }),
      isChatLoading: false,
      setIsChatLoading: (loading) => set({ isChatLoading: loading }),

      // Credits
      creditsRefreshTrigger: 0,
      triggerCreditsRefresh: () =>
        set((state) => ({ creditsRefreshTrigger: state.creditsRefreshTrigger + 1 })),
    }),
    {
      name: "cognive-storage",
      partialize: (state) => ({
        connectedIntegrationIds: state.connectedIntegrationIds,
        hasCompletedOnboarding: state.hasCompletedOnboarding,
        conversations: state.conversations, // <- Enable localStorage persistence
      }),
    }
  )
);

// Selectors
export const useConversationState = () =>
  useAppStore((state) => state.conversationState);
export const useConversations = () => useAppStore((state) => state.conversations);
export const usePendingMessages = () => useAppStore((state) => state.pendingMessages);
export const useCurrentConversation = () => {
  const conversations = useAppStore((state) => state.conversations);
  const currentTaskId = useAppStore((state) => state.currentTaskId);
  const pendingMessages = useAppStore((state) => state.pendingMessages);
  
  if (!currentTaskId) {
    // No task selected - show pending messages if any
    if (pendingMessages.length > 0) {
      return {
        id: 'pending',
        name: 'New Chat',
        status: 'running' as const,
        type: 'automation' as const,
        lastModifiedAt: new Date().toISOString(),
        lastRun: '',
        connectedApps: [],
        description: 'New Chat',
        chatHistory: pendingMessages,
        compiledWorkflow: { trigger: { type: 'polling' as const, interval: '', app: '' }, steps: [], errorHandling: {} },
        stats: { totalRuns: 0 },
      };
    }
    return null;
  }
  
  // Task selected - try to find it
  const existingConversation = conversations.find((conv) => conv.id === currentTaskId);
  
  if (existingConversation) {
    return existingConversation;
  }
  
  // Task ID set but conversation doesn't exist yet (waiting for subscription)
  // Show pending messages with the real sessionId
  if (pendingMessages.length > 0) {
    return {
      id: currentTaskId,
      name: 'New Chat',
      status: 'running' as const,
      type: 'automation' as const,
      lastModifiedAt: new Date().toISOString(),
      lastRun: '',
      connectedApps: [],
      description: 'New Chat',
      chatHistory: pendingMessages,
      compiledWorkflow: { trigger: { type: 'polling' as const, interval: '', app: '' }, steps: [], errorHandling: {} },
      stats: { totalRuns: 0 },
    };
  }
  
  return null;
};
export const useConnectedIntegrations = () => {
  const allIntegrations = useAppStore((state) => state.allIntegrations);
  const connectedIds = useAppStore((state) => state.connectedIntegrationIds);
  return allIntegrations.filter((i) => connectedIds.includes(i.id));
};

