import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Task } from "@/types";

const statusIcons: Record<string, string> = {
  running: "🟢",
  paused: "⏸️",
  failed: "🔴",
  completed: "✅",
};

interface TaskListProps {
  tasks: Task[];
  currentTaskId: string | null;
  onTaskClick: (taskId: string) => void;
  onNewTask: () => void;
}

export function TaskList({ tasks, currentTaskId, onTaskClick, onNewTask }: TaskListProps) {
  return (
    <aside className="w-64 border-r border-border bg-card hidden md:flex flex-col">
      <div className="p-4 border-b border-border">
        <h2 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">📋 MY TASKS</h2>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {tasks.map((task) => (
            <button
              key={task.id}
              onClick={() => onTaskClick(task.id)}
              className={cn(
                "w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors",
                currentTaskId === task.id
                  ? "bg-primary/20 text-foreground"
                  : "hover:bg-muted text-muted-foreground hover:text-foreground"
              )}
              data-testid={`task-item-${task.id}`}
            >
              <span>{statusIcons[task.status] || "⚪"}</span>
              <span className="flex-1 truncate text-sm">{task.name}</span>
              <ChevronRight className="w-4 h-4 opacity-50" />
            </button>
          ))}
        </div>
      </ScrollArea>
      <div className="p-4 border-t border-border">
        <Button
          variant="outline"
          className="w-full gap-2"
          onClick={onNewTask}
          data-testid="new-task-btn"
        >
          <Plus className="w-4 h-4" />
          New Task
        </Button>
      </div>
    </aside>
  );
}