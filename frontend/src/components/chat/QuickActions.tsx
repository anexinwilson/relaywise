import { Button } from "@/components/ui/button";
import { Plus, Wrench, BarChart3 } from "lucide-react";

interface QuickActionsProps {
  onIntegrationsClick: () => void;
  onWorkflowClick: () => void;
  onLogsClick: () => void;
}

export function QuickActions({
  onIntegrationsClick,
  onWorkflowClick,
  onLogsClick,
}: QuickActionsProps) {
  return (
    <div className="flex gap-2 mt-3">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-muted-foreground hover:text-foreground"
        onClick={onIntegrationsClick}
      >
        <Plus className="w-4 h-4 mr-1" />
        Integration
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-muted-foreground hover:text-foreground"
        onClick={onWorkflowClick}
      >
        <Wrench className="w-4 h-4 mr-1" />
        Workflow
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-muted-foreground hover:text-foreground"
        onClick={onLogsClick}
      >
        <BarChart3 className="w-4 h-4 mr-1" />
        Logs
      </Button>
    </div>
  );
}
