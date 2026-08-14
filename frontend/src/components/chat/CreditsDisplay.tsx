"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

interface CreditsState {
  remainingCredits: number;
  totalCredits: number;
  usedCredits: number;
  loading: boolean;
  error: string | null;
}

interface CreditsDisplayProps {
  refreshTrigger?: number;
}

export function CreditsDisplay({ refreshTrigger }: CreditsDisplayProps) {
  const [credits, setCredits] = useState<CreditsState>({
    remainingCredits: 0,
    totalCredits: 100,
    usedCredits: 0,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const fetchCredits = async () => {
      try {
        setCredits((prev) => ({ ...prev, loading: true }));
        const response = await fetch("/api/credits/balance");

        if (!response.ok) {
          throw new Error("Failed to fetch credits");
        }

        const data = await response.json();
        setCredits({
          remainingCredits: data.remaining_credits || 0,
          totalCredits: data.total_credits || 100,
          usedCredits: data.used_credits || 0,
          loading: false,
          error: null,
        });
      } catch (err) {
        console.error("Error fetching credits:", err);
        setCredits((prev) => ({
          ...prev,
          loading: false,
          error: "Unable to load credits",
        }));
      }
    };

    fetchCredits();
  }, [refreshTrigger]);

  if (credits.loading) {
    return (
      <div className="p-4 border-t border-border">
        <div className="text-sm text-muted-foreground">Loading credits...</div>
      </div>
    );
  }

  if (credits.error) {
    return (
      <div className="p-4 border-t border-border">
        <div className="text-sm text-muted-foreground">{credits.error}</div>
      </div>
    );
  }

  const creditsPercent = Math.min(
    (credits.usedCredits / credits.totalCredits) * 100,
    100,
  );
  const isCritical = creditsPercent > 80;

  return (
    <div className="p-4 border-t border-border">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Credits</span>
          <span
            className={cn(
              "font-semibold tabular-nums",
              isCritical ? "text-destructive" : "text-foreground",
            )}
          >
            {credits.usedCredits.toFixed(2)}/{credits.totalCredits}
          </span>
        </div>
        <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-300",
              isCritical ? "bg-destructive" : "bg-primary",
            )}
            style={{ width: `${creditsPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}
