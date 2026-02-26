import { Button } from "@/components/ui/button";
import { Wrench, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Task } from "@/types";

const statusColors: Record<string, string> = {
  running: "bg-success",
  paused: "bg-muted-foreground",
  failed: "bg-destructive",
  completed: "bg-primary",
};

interface TaskHeaderProps {
  task: Task;
  onShowWorkflow: () => void;
  onShowLogs: () => void;
}

export function TaskHeader({ task, onShowWorkflow, onShowLogs }: TaskHeaderProps) {
  return (
    <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-card/50">
      <div className="flex items-center gap-3">
        <span className="text-xl">💬</span>
        <h1 className="font-semibold text-foreground">{task.name}</h1>
        <span className={cn("w-2 h-2 rounded-full", statusColors[task.status])} />
      </div>
      <div className="flex items-center gap-2">
        {task.type === "automation" &&
          task.compiledWorkflow?.steps &&
          task.compiledWorkflow.steps.length > 0 && (
            <>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={onShowWorkflow}
              >
                <Wrench className="w-4 h-4" />
                <span className="hidden sm:inline">Workflow</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={onShowLogs}
              >
                <BarChart3 className="w-4 h-4" />
                <span className="hidden sm:inline">Logs</span>
              </Button>
            </>
          )}
      </div>
    </div>
  );
}