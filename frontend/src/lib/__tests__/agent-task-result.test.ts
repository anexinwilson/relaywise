import { describe, expect, it } from "vitest";
import { parseAgentTaskResult } from "../agent-task-result";

describe("parseAgentTaskResult", () => {
  it("parses the serialized AppSync task payload", () => {
    expect(
      parseAgentTaskResult('{"chatName":"Inbox cleanup","response":"Done"}'),
    ).toEqual({
      chatName: "Inbox cleanup",
      response: "Done",
    });
  });

  it("accepts an object payload", () => {
    const payload = { response: "Complete" };
    expect(parseAgentTaskResult(payload)).toEqual(payload);
  });

  it("treats empty task results as absent", () => {
    expect(parseAgentTaskResult(null)).toBeNull();
    expect(parseAgentTaskResult("")).toBeNull();
  });

  it("rejects malformed serialized payloads", () => {
    expect(() => parseAgentTaskResult("not-json")).toThrow(SyntaxError);
  });

  it("rejects fields with unexpected types", () => {
    expect(() => parseAgentTaskResult({ response: 42 })).toThrow(TypeError);
  });
});
