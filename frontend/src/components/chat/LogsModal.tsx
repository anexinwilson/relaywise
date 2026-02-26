import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useLogs, useClearLogs } from "@/store/appStore";
import type { Task } from "@/types";

interface LogsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | undefined;
}

export function LogsModal({ open, onOpenChange, task }: LogsModalProps) {
  const logs = useLogs();
  const clearLogs = useClearLogs();

  const getLevelStyles = (level: string) => {
    switch (level) {
      case "success": return "text-green-500";
      case "error": return "text-red-500";
      case "warning": return "text-yellow-500";
      default: return "text-muted-foreground";
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">📊 Live Logs</DialogTitle>
            {logs.length > 0 && (
              <button
                onClick={clearLogs}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Clear logs
              </button>
            )}
          </div>
        </DialogHeader>
        <div className="space-y-4">
          {/* Task Info */}
          {task && (
            <div className="bg-background rounded-lg p-3 text-sm">
              <p className="text-muted-foreground">
                <span className="font-medium text-foreground">Task:</span> {task.name || "New conversation"}
              </p>
              <p className="text-muted-foreground">
                <span className="font-medium text-foreground">Session:</span> {task.id?.substring(0, 8)}...
              </p>
            </div>
          )}

          {/* Log Entries */}
          <div className="bg-background rounded-lg p-4 font-mono text-sm max-h-96 overflow-auto">
            {logs.length > 0 ? (
              logs.map((log) => (
                <div
                  key={log.id}
                  className={cn("py-1", getLevelStyles(log.level))}
                >
                  <span className="opacity-50">
                    [{new Date(log.timestamp).toLocaleTimeString()}]
                  </span>{" "}
                  <span className="font-medium">[{log.level.toUpperCase()}]</span>{" "}
                  {log.message}
                  {log.details && (
                    <div className="ml-4 text-xs opacity-70 mt-0.5">
                      {log.details}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="text-muted-foreground">No logs yet. Start a conversation to see logs here.</p>
            )}
          </div>

          {/* Log count */}
          {logs.length > 0 && (
            <p className="text-xs text-muted-foreground text-right">
              {logs.length} log{logs.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}