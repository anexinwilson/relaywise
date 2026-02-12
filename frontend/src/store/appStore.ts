import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Integration } from "@/types";
import integrationsData from "@/data/integrations.json";

// Conversation state for step-by-step chat flows
interface ConversationState {
  currentTree: string | null;
  currentStepIndex: number;
  collectedData: Record<string, string>;
  waitingForInput: boolean;
}

interface AppState {
  // UI State
  showCompiledModal: boolean;
  showLogsModal: boolean;
  showIntegrationModal: boolean;
  selectedIntegration: Integration | null;
  setShowCompiledModal: (show: boolean) => void;
  setShowLogsModal: (show: boolean) => void;
  setShowIntegrationModal: (
    show: boolean,
    integration?: Integration | null
  ) => void;

  // Current selections
  currentTaskId: string | null;
  setCurrentTask: (id: string | null) => void;

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
}

const initialConversationState: ConversationState = {
  currentTree: null,
  currentStepIndex: 0,
  collectedData: {},
  waitingForInput: false,
};

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // UI State
      showCompiledModal: false,
      showLogsModal: false,
      showIntegrationModal: false,
      selectedIntegration: null,
      setShowCompiledModal: (show) => set({ showCompiledModal: show }),
      setShowLogsModal: (show) => set({ showLogsModal: show }),
      setShowIntegrationModal: (show, integration = null) =>
        set({ showIntegrationModal: show, selectedIntegration: integration }),

      // Current selections
      currentTaskId: null,
      setCurrentTask: (id) => set({ currentTaskId: id }),

      // Conversation State
      conversationState: initialConversationState,
      setConversationState: (newState) =>
        set((state) => ({
          conversationState: { ...state.conversationState, ...newState },
        })),
      resetConversationState: () =>
        set({ conversationState: initialConversationState }),

      // Integrations
      allIntegrations: integrationsData.popular as Integration[],
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
    }),
    {
      name: "cognive-storage",
      partialize: (state) => ({
        connectedIntegrationIds: state.connectedIntegrationIds,
        hasCompletedOnboarding: state.hasCompletedOnboarding,
      }),
    }
  )
);

// Selectors
export const useConversationState = () =>
  useAppStore((state) => state.conversationState);
export const useConnectedIntegrations = () => {
  const allIntegrations = useAppStore((state) => state.allIntegrations);
  const connectedIds = useAppStore((state) => state.connectedIntegrationIds);
  return allIntegrations.filter((i) => connectedIds.includes(i.id));
};
