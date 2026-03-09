import { useRef, useEffect } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { ChatMessage, AgentEvent } from "@/types";
import { MessageButtons } from "./MessageButtons";
import { ThinkingBox } from "./ThinkingBox";

interface ChatAreaProps {
  messages: ChatMessage[];
  isTyping: boolean;
  user: { firstName?: string | null; imageUrl?: string } | null;
  onOptionClick: (value: string, label: string) => void;
  isLoading?: boolean;
  thinkingLogs?: AgentEvent[];
}

export function ChatArea({ messages, isTyping, user, onOptionClick, isLoading, thinkingLogs = [] }: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ScrollArea className="flex-1 p-4">
      <div className="max-w-3xl mx-auto space-y-4">
        {isLoading ? (
          <div className="space-y-6 animate-pulse">
             <div className="flex gap-3 justify-end">
               <div className="max-w-md rounded-2xl p-4 bg-muted w-64 h-16" />
               <div className="w-8 h-8 rounded-full bg-muted shrink-0" />
             </div>
             <div className="flex gap-3 justify-start">
               <div className="w-8 h-8 rounded-lg bg-muted shrink-0" />
               <div className="max-w-md rounded-2xl p-4 bg-muted w-72 h-24" />
             </div>
             <div className="flex gap-3 justify-end">
               <div className="max-w-md rounded-2xl p-4 bg-muted w-48 h-12" />
               <div className="w-8 h-8 rounded-full bg-muted shrink-0" />
             </div>
          </div>
        ) : messages.length === 0 && !isTyping ? (
          <MessageButtons onOptionClick={onOptionClick} />
        ) : (
          <>
            {messages.map((message, index) => {
              const isLastMessage = index === messages.length - 1;
              const isAssistant = message.role === "assistant";
              return (
              <div key={message.id} className="flex flex-col gap-4">
                <div
                  className={cn(
                    "flex gap-3",
                    message.role === "user" ? "justify-end" : "justify-start w-full min-w-0"
                  )}
                >
                {message.role === "assistant" && (
                  <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center flex-shrink-0 shrink-0">
                    <span className="text-white text-sm font-bold">C</span>
                  </div>
                )}
                <div
                  className={cn(
                    "rounded-2xl p-4 flex-1 min-w-0 flex-shrink",
                    message.role === "assistant" ? "max-w-2xl" : "max-w-md flex-none",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-card border border-border"
                  )}
                >
                  {thinkingLogs.length > 0 && !isTyping && isLastMessage && isAssistant && (
                    <div className="mb-4">
                      <ThinkingBox logs={thinkingLogs} isComplete={true} />
                    </div>
                  )}
                  <p className="text-sm whitespace-pre-line">{message.content}</p>
                  {message.options && message.role === "assistant" && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {message.options.map((option, i) => (
                        <Button
                          key={i}
                          variant="outline"
                          size="sm"
                          className="h-8"
                          onClick={() => onOptionClick(option.value, option.label)}
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
                    <AvatarFallback>{user?.firstName?.charAt(0) || "U"}</AvatarFallback>
                  </Avatar>
                )}
              </div>
            </div>
            )})}
          </>
        )}
        
        {isTyping && (
          <div className="flex gap-3 justify-start w-full min-w-0">
            <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center shrink-0">
              <span className="text-white text-sm font-bold">C</span>
            </div>
            {thinkingLogs.length > 0 ? (
              <div className="flex-1 min-w-0 max-w-2xl">
                <ThinkingBox logs={thinkingLogs} isComplete={false} />
              </div>
            ) : (
              <div className="bg-card border border-border rounded-2xl p-4 w-fit">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:0.1s]" />
                  <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:0.2s]" />
                </div>
              </div>
            )}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
}