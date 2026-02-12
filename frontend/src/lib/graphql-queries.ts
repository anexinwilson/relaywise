import { gql } from "@apollo/client";

export const ASK_AGENT_QUERY = gql`
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
