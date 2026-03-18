"use client";

import { Button } from "@/components/ui/button";
import { MoreVertical, Trash2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useRef, useEffect } from "react";
import type { Task } from "@/types";

const statusIcons: Record<string, string> = {
  running: "",
  paused: "",
  failed: "",
  completed: "",
};

interface TaskListProps {
  tasks: Task[];
  currentTaskId: string | null;
  onTaskClick: (taskId: string) => void;
  onNewTask: () => void;
  onDeleteTask?: (taskId: string) => void;
  isLoading?: boolean;
  creditsUsed?: number;
  creditsTotal?: number;
  children?: React.ReactNode;
}

export function TaskList({
  tasks,
  currentTaskId,
  onTaskClick,
  onNewTask,
  onDeleteTask,
  isLoading,
  creditsUsed = 0,
  creditsTotal = 100,
  children,
}: TaskListProps) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuId(null);
      }
    };
    if (openMenuId) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [openMenuId]);

  const handleDeleteClick = (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    setConfirmDeleteId(taskId);
    setOpenMenuId(null);
  };

  const handleConfirmDelete = (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    if (onDeleteTask) onDeleteTask(taskId);
    setConfirmDeleteId(null);
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirmDeleteId(null);
  };

  const toggleMenu = (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    setOpenMenuId(openMenuId === taskId ? null : taskId);
  };

  const creditsPercent = Math.min((creditsUsed / creditsTotal) * 100, 100);
  const creditsRemaining = creditsTotal - creditsUsed;
  const isCritical = creditsPercent > 80;

  return (
    <aside className="w-64 shrink-0 flex flex-col border-r border-border bg-card">

      {/* Header */}
      <div className="p-3 pt-4">
        <Button className="w-full gap-2 bg-foreground text-background hover:bg-foreground/90" onClick={onNewTask}>
          <Plus className="w-4 h-4" />
          New Task
        </Button>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto px-2">
        <div className="space-y-0.5">
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={`skeleton-${i}`} className="flex items-center gap-3 px-3 py-2.5 rounded-lg">
                <div className="w-1.5 h-1.5 rounded-full bg-muted animate-pulse shrink-0" />
                <div className="h-3.5 bg-muted animate-pulse rounded w-3/4" />
              </div>
            ))
          ) : tasks.length === 0 ? (
            <div className="px-3 py-8 text-center">
              <p className="text-xs text-muted-foreground/60">No tasks yet</p>
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                className="relative"
                ref={openMenuId === task.id ? menuRef : null}
              >
                <div
                  className={cn(
                    "flex items-center gap-1.5 px-2 py-2 rounded-lg transition-all duration-150 group",
                    currentTaskId === task.id
                      ? "bg-primary/10 text-foreground"
                      : "hover:bg-muted/60 text-muted-foreground hover:text-foreground"
                  )}
                >
                  {/* Active indicator */}
                  <div
                    className={cn(
                      "shrink-0 w-1 h-5 rounded-full transition-all duration-200",
                      currentTaskId === task.id
                        ? "bg-primary"
                        : "bg-transparent group-hover:bg-border"
                    )}
                  />

                  <div
                    onClick={() => onTaskClick(task.id)}
                    className="flex items-center gap-2 min-w-0 flex-1 cursor-pointer overflow-hidden"
                  >
                    <span className="truncate text-sm leading-tight">{task.name}</span>
                  </div>

                  <button
                    onClick={(e) => toggleMenu(e, task.id)}
                    className="shrink-0 w-7 h-7 flex items-center justify-center rounded cursor-pointer bg-transparent border-none hover:bg-gray-700 transition-colors"
                  >
                    <MoreVertical className="w-4 h-4 text-gray-500" />
                  </button>
                </div>

                {/* Dropdown menu */}
                {openMenuId === task.id && (
                  <div className="absolute right-1 top-full mt-1 z-50 w-28 rounded-lg border border-border bg-popover shadow-md">
                    <div className="p-1">
                      <button
                        onClick={(e) => handleDeleteClick(e, task.id)}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-destructive hover:bg-destructive/10 rounded-md cursor-pointer border-none bg-transparent transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete
                      </button>
                    </div>
                  </div>
                )}

                {/* Confirm delete */}
                {confirmDeleteId === task.id && (
                  <div className="absolute right-1 top-full mt-1 z-50 w-48 rounded-lg border border-border bg-popover shadow-md p-3">
                    <p className="text-xs text-muted-foreground mb-2.5">
                      Delete this conversation?
                    </p>
                    <div className="flex gap-1.5">
                      <button
                        onClick={(e) => handleConfirmDelete(e, task.id)}
                        className="flex-1 px-2 py-1.5 text-xs font-medium text-white bg-destructive hover:bg-destructive/90 rounded-md cursor-pointer border-none transition-colors"
                      >
                        Delete
                      </button>
                      <button
                        onClick={handleCancelDelete}
                        className="flex-1 px-2 py-1.5 text-xs font-medium text-muted-foreground bg-muted hover:bg-muted/80 rounded-md cursor-pointer border-none transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Credits - render children if provided, otherwise show default */}
      {children || (
        <div className="p-4 border-t border-border">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Credits</span>
              <span className={cn("font-semibold tabular-nums", isCritical ? "text-destructive" : "text-foreground")}>
                {creditsUsed}/{creditsTotal}
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-300",
                  isCritical ? "bg-destructive" : "bg-primary"
                )}
                style={{ width: `${creditsPercent}%` }}
              />
            </div>
          </div>
        </div>
      )}

    </aside>
  );
}