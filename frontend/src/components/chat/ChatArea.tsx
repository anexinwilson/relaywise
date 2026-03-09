import { useRef, useEffect } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";
import { MessageButtons } from "./MessageButtons";

interface ChatAreaProps {
  messages: ChatMessage[];
  isTyping: boolean;
  user: { firstName?: string | null; imageUrl?: string } | null;
  onOptionClick: (value: string, label: string) => void;
  isLoading?: boolean;
}

export function ChatArea({ messages, isTyping, user, onOptionClick, isLoading }: ChatAreaProps) {
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
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.role === "assistant" && (
                  <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-sm font-bold">C</span>
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
            ))}
          </>
        )}
        
        {isTyping && (
          <div className="flex gap-3">
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
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
}