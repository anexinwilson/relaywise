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
}

export function TaskHeader({ task }: TaskHeaderProps) {
  return (
    <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-card/50">
      <div className="flex items-center gap-3">
        <h1 className="font-semibold text-foreground">{task.name}</h1>
        <span className={cn("w-2 h-2 rounded-full", statusColors[task.status])} />
      </div>
    </div>
  );
}
