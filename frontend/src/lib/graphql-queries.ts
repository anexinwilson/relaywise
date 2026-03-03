import { gql } from "@apollo/client";

export const ASK_AGENT_QUERY = gql`
  query AskAgent($message: String!, $sessionId: String) {
    askAgent(message: $message, sessionId: $sessionId) {
      success
      response
      rag_tools_found
      error
      taskId
      sessionId
      chatName
    }
  }
`;

export const TASK_COMPLETE_SUBSCRIPTION = gql`
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

export const CHAT_NAME_CREATE_SUBSCRIPTION = gql`
  subscription OnChatNameUpdate($sessionId: String) {
    onChatNameUpdate(sessionId: $sessionId) {
      userId
      sessionId
      chatName
      timestamp
    }
  }
`;

export const GET_OR_CREATE_USER = gql`
  mutation GetOrCreateUser {
    getOrCreateUser {
      userId
      email
      name
      tier
      apiCallCount
    }
  }
`;

export const DELETE_CONVERSATION = gql`
  mutation DeleteConversation($sessionId: String!) {
    deleteConversation(sessionId: $sessionId) {
      success
      error
      deletedCount
    }
  }
`;

export const GET_USER_CONVERSATIONS = gql`
  query GetUserConversations {
    getUserConversations {
      sessionId
      chatName
      lastModifiedAt
    }
  }
`;

export const GET_CONVERSATION_MESSAGES = gql`
  query GetConversationMessages($sessionId: String!) {
    getConversationMessages(sessionId: $sessionId) {
      id
      sender
      content
      timestamp
      type
    }
  }
`;
