import { useRef, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";
import { QuickActions } from "./QuickActions";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onIntegrationsClick: () => void;
  onWorkflowClick: () => void;
  onLogsClick: () => void;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  onIntegrationsClick,
  onWorkflowClick,
  onLogsClick,
  disabled,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea to fit content
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim()) {
        onSubmit(e as unknown as React.FormEvent);
      }
    }
  };

  return (
    <div className="p-4 border-t border-border bg-card/50">
      <form onSubmit={onSubmit} className="max-w-3xl mx-auto">
        <div className="flex gap-2 items-end">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="flex-1 min-h-[48px] max-h-[200px] bg-background resize-none py-3"
            data-testid="chat-input"
            disabled={disabled}
            rows={1}
          />
          <Button
            type="submit"
            className="h-12 px-6 gradient-primary hover:opacity-90 shrink-0"
            data-testid="chat-submit-btn"
            disabled={disabled || !value.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>

        <QuickActions
          onIntegrationsClick={onIntegrationsClick}
          onWorkflowClick={onWorkflowClick}
          onLogsClick={onLogsClick}
        />
      </form>
    </div>
  );
}
