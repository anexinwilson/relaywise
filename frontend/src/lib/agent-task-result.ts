export interface AgentTaskResult {
  chatName?: string;
  response?: string;
}

export function parseAgentTaskResult(result: unknown): AgentTaskResult | null {
  if (!result) return null;

  const parsed: unknown = typeof result === "string" ? JSON.parse(result) : result;
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return null;
  }

  const record = parsed as Record<string, unknown>;
  if (record.chatName !== undefined && typeof record.chatName !== "string") {
    throw new TypeError("Agent task chatName must be a string");
  }
  if (record.response !== undefined && typeof record.response !== "string") {
    throw new TypeError("Agent task response must be a string");
  }

  return {
    ...(typeof record.chatName === "string" ? { chatName: record.chatName } : {}),
    ...(typeof record.response === "string" ? { response: record.response } : {}),
  };
}
