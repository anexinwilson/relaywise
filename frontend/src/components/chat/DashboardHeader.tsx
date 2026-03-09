import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Settings, Plug, User } from "lucide-react";
import type { Integration } from "@/types";

interface DashboardHeaderProps {
  connectedIntegrations: Integration[];
  onIntegrationsClick: () => void;
  onSettingsClick: () => void;
  UserButtonComponent: React.ComponentType<{ afterSignOutUrl?: string }> | null;
}

export function DashboardHeader({
  connectedIntegrations,
  onIntegrationsClick,
  onSettingsClick,
  UserButtonComponent,
}: DashboardHeaderProps) {

  return (
    <header className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
      <Link href="/" className="flex items-center gap-2">
        <img
          src="/cognive-logo.svg"
          alt="Cognive"
          width={32}
          height={32}
          className="rounded-lg"
        />
        <span className="text-lg font-bold text-foreground hidden sm:inline">Cognive</span>
      </Link>
      
      {/* Connected Apps */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground hidden md:inline">
          <Plug className="w-4 h-4 inline mr-1" />
          CONNECTED ({connectedIntegrations.length})
        </span>
        <div className="flex items-center gap-1">
          {connectedIntegrations.slice(0, 5).map((app) => (
            <img
              key={app.id}
              src={app.logo}
              alt={app.name}
              width={28}
              height={28}
              className="rounded-lg object-contain"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(app.name)}&background=1f2937&color=ffffff&size=28&bold=true&format=svg`;
              }}
            />
          ))}
          <Button
            size="sm"
            className="h-7 gradient-primary text-white hover:opacity-90 transition-opacity"
            onClick={onIntegrationsClick}
          >
            + Add
          </Button>
        </div>
      </div>
      
      {/* User Menu */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={onSettingsClick}
        >
          <Settings className="w-5 h-5" />
        </Button>
        {UserButtonComponent ? (
          <UserButtonComponent afterSignOutUrl="/" />
        ) : (
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
            <User className="w-4 h-4 text-primary" />
          </div>
        )}
      </div>
    </header>
  );
}