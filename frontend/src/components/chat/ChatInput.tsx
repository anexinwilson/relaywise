import { Input } from "@/components/ui/input";
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
  return (
    <div className="p-4 border-t border-border bg-card/50">
      <form onSubmit={onSubmit} className="max-w-3xl mx-auto">
        <div className="flex gap-2">
          <Input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 h-12 bg-background"
            data-testid="chat-input"
            disabled={disabled}
          />
          <Button
            type="submit"
            className="h-12 px-6 gradient-primary hover:opacity-90"
            data-testid="chat-submit-btn"
            disabled={disabled}
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