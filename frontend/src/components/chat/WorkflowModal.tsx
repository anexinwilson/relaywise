import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Play, Pause, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Task } from "@/types";

interface WorkflowModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | undefined;
  onToggleStatus: () => void;
  onCopyWorkflow: () => void;
  copiedWorkflow: boolean;
}

export function WorkflowModal({
  open,
  onOpenChange,
  task,
  onToggleStatus,
  onCopyWorkflow,
  copiedWorkflow,
}: WorkflowModalProps) {
  if (!task) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">📋 Compiled Workflow</DialogTitle>
        </DialogHeader>
        <div className="space-y-6">
          {/* Meta */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-foreground">{task.name}</h3>
              <p className="text-sm text-muted-foreground">
                Status:{" "}
                <span
                  className={cn(
                    "capitalize",
                    task.status === "running" && "text-success"
                  )}
                >
                  {task.status}
                </span>
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={onToggleStatus}>
              {task.status === "running" ? (
                <>
                  <Pause className="w-4 h-4 mr-1" /> Pause
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-1" /> Resume
                </>
              )}
            </Button>
          </div>

          {/* Trigger */}
          <div>
            <h4 className="text-sm font-semibold text-muted-foreground mb-2">📡 TRIGGER</h4>
            <div className="bg-background rounded-lg p-4 font-mono text-sm">
              <p>Type: {task.compiledWorkflow?.trigger?.type || "manual"}</p>
              {task.compiledWorkflow?.trigger?.interval && (
                <p>Interval: {task.compiledWorkflow.trigger.interval}</p>
              )}
              {task.compiledWorkflow?.trigger?.app && (
                <p>App: {task.compiledWorkflow.trigger.app}</p>
              )}
            </div>
          </div>

          {/* Steps */}
          {task.compiledWorkflow?.steps && task.compiledWorkflow.steps.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-muted-foreground mb-2">🔄 WORKFLOW STEPS</h4>
              <div className="space-y-2">
                {task.compiledWorkflow.steps.map((step, i) => (
                  <div key={i} className="bg-background rounded-lg p-4 font-mono text-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs">
                        {i + 1}
                      </span>
                      <span className="text-foreground">
                        {step.app}.{step.action}
                      </span>
                    </div>
                    {step.config && (
                      <div className="pl-8 text-muted-foreground">
                        {Object.entries(step.config).map(([key, value]) => (
                          <p key={key}>└─ {key}: {JSON.stringify(value)}</p>
                        ))}
                      </div>
                    )}
                    {step.condition && (
                      <p className="pl-8 text-primary">└─ condition: {step.condition}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Copy Button */}
          <Button variant="outline" className="w-full gap-2" onClick={onCopyWorkflow}>
            {copiedWorkflow ? (
              <>
                <Check className="w-4 h-4" /> Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" /> Copy to Clipboard
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}