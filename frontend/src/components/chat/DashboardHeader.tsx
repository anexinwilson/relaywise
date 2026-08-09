import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Settings, Plug, User } from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import type { Integration } from "@/types";

interface DashboardHeaderProps {
  connectedIntegrations: Integration[];
  onIntegrationsClick: () => void;
  onSettingsClick: () => void;
}

export function DashboardHeader({
  connectedIntegrations,
  onIntegrationsClick,
  onSettingsClick,
}: DashboardHeaderProps) {

  return (
    <header className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
      <Link href="/" className="flex items-center gap-2">
        <Image
          src="/cognive-logo.svg"
          alt="Cognive"
          width={32}
          height={32}
          className="rounded-lg"
        />
        <span className="text-lg font-bold text-foreground hidden sm:inline">Cognive</span>
      </Link>
      
      {/* Connected Apps */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground hidden md:inline">
          <Plug className="w-4 h-4 inline mr-1" />
          CONNECTED ({connectedIntegrations.length})
        </span>
        <div className="flex items-center gap-2">
          {connectedIntegrations.slice(0, 5).map((app) => (
            <Link key={app.id} href="/integrations">
              <span className="inline-flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-full border border-border bg-muted/50 text-foreground hover:bg-muted hover:border-primary/40 transition-all cursor-pointer">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
                {app.name}
              </span>
            </Link>
          ))}
          <Button
            size="sm"
            className="h-8 gradient-primary text-white hover:opacity-90 transition-opacity"
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
        <UserButton fallback={<User className="w-4 h-4 text-primary" />} />
      </div>
    </header>
  );
}
