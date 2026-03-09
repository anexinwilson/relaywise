import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentEvent } from "@/types";

interface ThinkingBoxProps {
  logs: AgentEvent[];
  isComplete: boolean;
}

export function ThinkingBox({ logs, isComplete }: ThinkingBoxProps) {
  // Always expand if actively running, optionally auto-collapse when complete
  const [isExpanded, setIsExpanded] = useState(true);

  const [hasAutoCollapsed, setHasAutoCollapsed] = useState(false);

  // Auto-collapse when complete, but only once
  useEffect(() => {
    if (isComplete && !hasAutoCollapsed) {
      setIsExpanded(false);
      setHasAutoCollapsed(true);
    }
  }, [isComplete, hasAutoCollapsed]);

  if (logs.length === 0) return null;

  const grouped = logs.reduce((acc, log) => {
    acc[log.category] = acc[log.category] || [];
    acc[log.category].push(log);
    return acc;
  }, {} as Record<string, AgentEvent[]>);

  const categories = Object.keys(grouped);

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card/60 backdrop-blur-sm p-4 text-sm w-full max-w-2xl shadow-sm transition-all">
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex justify-between items-center text-muted-foreground hover:text-foreground transition-colors font-medium w-full text-left"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          {isComplete ? (
            <span className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              Agent executed {logs.length} internal steps
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              Agent is thinking...
            </span>
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="flex flex-col gap-5 mt-3">
          {categories.map((category, catIdx) => {
            const isLastCategory = catIdx === categories.length - 1;
            const isCategoryComplete = isComplete || !isLastCategory;
            
            return (
              <div key={category} className="flex flex-col gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  ▼ {category} {isCategoryComplete ? "(Completed)" : "(Running...)"}
                </span>
                
                <div className="flex flex-col gap-3 pl-4 relative before:absolute before:inset-y-1 before:left-1 before:w-[2px] before:bg-border/50">
                  {grouped[category].map((log, logIdx) => {
                    const isLastLog = isLastCategory && logIdx === grouped[category].length - 1;
                    const isFinishedLog = isComplete || !isLastLog;
                    
                    return (
                      <div key={logIdx} className="flex items-start gap-3 relative w-full min-w-0">
                        {isFinishedLog ? (
                          <CheckCircle2 className="w-3.5 h-3.5 mt-[2px] text-emerald-500/80 absolute -left-[14px] bg-card rounded-full shrink-0" />
                        ) : (
                          <Loader2 className="w-3.5 h-3.5 mt-[2px] animate-spin text-primary absolute -left-[14px] bg-card rounded-full shrink-0" />
                        )}
                        <span className={cn("flex-1 min-w-0 leading-snug break-words whitespace-normal", isFinishedLog ? "text-muted-foreground" : "text-foreground font-medium animate-pulse")}>
                          {log.message}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
