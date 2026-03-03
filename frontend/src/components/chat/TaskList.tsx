"use client";

import { Button } from "@/components/ui/button";
import { MoreVertical, Trash2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useRef, useEffect } from "react";
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
  onDeleteTask?: (taskId: string) => void;
}

export function TaskList({ tasks, currentTaskId, onTaskClick, onNewTask, onDeleteTask }: TaskListProps) {
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

  return (
    <aside className="w-64 shrink-0 flex flex-col border-r border-border bg-card">
      <div className="p-4 border-b border-border">
        <h2 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
          📋 MY TASKS
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-1">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="relative"
              ref={openMenuId === task.id ? menuRef : null}
            >
              <div
                className={cn(
                  "flex items-center gap-2 p-3 rounded-lg transition-colors",
                  currentTaskId === task.id
                    ? "bg-primary/20 text-foreground"
                    : "hover:bg-muted text-muted-foreground hover:text-foreground"
                )}
              >
                <div
                  onClick={() => onTaskClick(task.id)}
                  className="flex items-center gap-2 min-w-0 flex-1 cursor-pointer overflow-hidden"
                >
                  <span className="shrink-0">{statusIcons[task.status] || "⚪"}</span>
                  <span className="truncate text-sm">{task.name}</span>
                </div>

                <button
                  onClick={(e) => toggleMenu(e, task.id)}
                  className="shrink-0 w-7 h-7 flex items-center justify-center rounded cursor-pointer bg-transparent border-none hover:bg-gray-700 transition-colors"
                >
                  <MoreVertical className="w-4 h-4 text-gray-500" />
                </button>
              </div>

              {openMenuId === task.id && (
                <div className="absolute right-0 top-full mt-1 z-50 w-28 rounded-md border border-gray-700 bg-gray-800 shadow-lg">
                  <div className="p-1">
                    <button
                      onClick={(e) => handleDeleteClick(e, task.id)}
                      className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-red-500 bg-gray-800 hover:bg-gray-700 rounded cursor-pointer border-none transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </div>
                </div>
              )}

              {confirmDeleteId === task.id && (
                <div className="absolute right-0 top-full mt-1 z-50 w-48 rounded-md border border-gray-700 bg-gray-800 shadow-lg p-3">
                  <p className="text-xs text-gray-300 mb-2">Delete this conversation?</p>
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => handleConfirmDelete(e, task.id)}
                      className="flex-1 px-2 py-1 text-xs text-white bg-red-600 hover:bg-red-700 rounded cursor-pointer border-none transition-colors"
                    >
                      Delete
                    </button>
                    <button
                      onClick={handleCancelDelete}
                      className="flex-1 px-2 py-1 text-xs text-gray-300 bg-gray-700 hover:bg-gray-600 rounded cursor-pointer border-none transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="p-4 border-t border-border">
        <Button variant="outline" className="w-full gap-2" onClick={onNewTask}>
          <Plus className="w-4 h-4" />
          New Task
        </Button>
      </div>
    </aside>
  );
}