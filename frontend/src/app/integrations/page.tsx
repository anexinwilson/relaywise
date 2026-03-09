"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Check, Loader2, ArrowLeft, Plug } from "lucide-react";
import { useAppStore, useConnectedIntegrations } from "@/store/appStore";
import appsCatalog from "@/apps_catalog.json";
import { cn } from "@/lib/utils";

const formattedApps = (appsCatalog as any[]).map((app) => ({
  ...app,
  id: app.slug,
}));

export default function IntegrationsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
  }, []);

  const connectedIntegrations = useConnectedIntegrations();
  const connectIntegration = useAppStore((state) => state.connectIntegration);
  const disconnectIntegration = useAppStore(
    (state) => state.disconnectIntegration
  );

  const allApps = formattedApps;
  const categories = Array.from(new Set(formattedApps.map(app => app.category))).sort();

  // Filter apps
  const filteredApps = allApps.filter((app) => {
    const matchesSearch =
      app.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      !selectedCategory || app.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Connected apps
  const connectedApps = connectedIntegrations;

  const handleConnect = async (appId: string) => {
    if (typeof window === "undefined") return;

    setConnectingId(appId);
    // Simulate connection delay
    await new Promise((resolve) => setTimeout(resolve, 2000));
    connectIntegration(appId);
    setConnectingId(null);
  };

  const handleDisconnect = (appId: string) => {
    disconnectIntegration(appId);
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  const getFallbackLogo = (name: string) => 
    `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=1f2937&color=ffffff&size=48&bold=true&format=svg`;

  return (
    <div className="min-h-screen bg-background" data-testid="integrations-page">
      {/* Header */}
      <header className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.back()}
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <Link href="/" className="flex items-center gap-2">
            <img
              src="/cognive-logo.svg"
              alt="Cognive"
              width={32}
              height={32}
              className="rounded-lg"
              loading="lazy"
            />
            <span className="text-lg font-bold text-foreground hidden sm:inline">
              Cognive
            </span>
          </Link>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            className="gradient-primary text-white hover:opacity-90 transition-opacity"
            onClick={() => router.push("/dashboard")}
          >
            Dashboard
          </Button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2 flex items-center gap-3">
            <Plug className="w-8 h-8 text-primary" />
            Integrations
          </h1>
          <p className="text-muted-foreground">Connect {allApps.length} apps to Cognive</p>
        </div>

        {/* Search */}
        <div className="relative mb-8">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search apps..."
            className="pl-12 h-12 bg-card"
            data-testid="integrations-search"
          />
        </div>

        {/* Connected Apps */}
        {connectedApps.length > 0 && (
          <section className="mb-12">
            <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
              <Check className="w-5 h-5 text-success" />
              CONNECTED ({connectedApps.length})
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {connectedApps.map((app) => (
                <motion.div
                  key={app.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="bg-white/5 border border-success/30 rounded-xl p-4 text-center group"
                >
                  <div className="w-16 h-16 mx-auto mb-3 rounded-2xl flex items-center justify-center p-1">
                    <img
                      src={app.logo}
                      alt={app.name}
                      className="w-full h-full object-contain"
                      loading="lazy"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = getFallbackLogo(app.name);
                      }}
                    />
                  </div>
                  <p className="text-sm font-medium text-foreground mb-2 truncate px-1">
                    {app.name}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleDisconnect(app.id)}
                  >
                    Disconnect
                  </Button>
                </motion.div>
              ))}
            </div>
          </section>
        )}

        <div className="flex flex-wrap items-center gap-2 mb-6">
          <Button
            variant={selectedCategory === null ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedCategory(null)}
            className={cn(
              "h-9 px-4 rounded-xl transition-all duration-200 border-border/50 hover:border-primary/50",
              selectedCategory === null ? "gradient-primary text-white border-transparent shadow-sm" : "bg-card/50 text-muted-foreground hover:bg-accent/50 hover:text-foreground"
            )}
          >
            All
          </Button>
          {categories.map((cat) => (
            <Button
              key={cat}
              variant={selectedCategory === cat ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(cat)}
              className={cn(
                "h-9 px-4 rounded-xl transition-all duration-200 border-border/50 hover:border-primary/50",
                selectedCategory === cat ? "gradient-primary text-white border-transparent shadow-sm" : "bg-card/50 text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              {cat}
            </Button>
          ))}
        </div>

        {/* Apps Grid */}
        <section>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredApps.map((app, i) => {
              const isConnected = connectedIntegrations.some(
                (int) => int.id === app.id
              );
              const isConnecting = connectingId === app.id;

              return (
                <motion.div
                  key={app.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.02 }}
                  className={cn(
                    "bg-white/9 border rounded-xl p-4 flex flex-col justify-between h-full",
                    isConnected
                      ? "border-success/30"
                      : "border-border hover:border-primary/50"
                  )}
                  data-testid={`integration-card-${app.id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl flex-shrink-0 flex items-center justify-center p-1">
                      <img
                        src={app.logo}
                        alt={app.name}
                        className="w-full h-full object-contain"
                        loading="lazy"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = getFallbackLogo(app.name);
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-foreground truncate text-base">
                        {app.name}
                      </h3>
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-0.5 leading-relaxed">
                        {app.description}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 pt-2 border-t border-border/50">
                    {isConnected ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full text-success hover:text-destructive group relative border border-success/20 overflow-hidden"
                        onClick={() => handleDisconnect(app.id)}
                      >
                        <span className="group-hover:opacity-0 transition-opacity flex items-center justify-center">
                          <Check className="w-4 h-4 mr-1" />
                          Connected
                        </span>
                        <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-destructive">
                          Disconnect
                        </span>
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full hover:bg-primary hover:text-primary-foreground transition-all duration-300"
                        onClick={() => handleConnect(app.id)}
                        disabled={isConnecting}
                        data-testid={`connect-btn-${app.id}`}
                      >
                        {isConnecting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Connecting
                          </>
                        ) : (
                          "Connect"
                        )}
                      </Button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </section>

        {filteredApps.length === 0 && (
          <div className="text-center py-16 bg-card/30 rounded-3xl border border-dashed border-border mt-8">
            <p className="text-lg font-medium text-foreground">No apps found</p>
            <p className="text-muted-foreground mt-1">
              Try searching for something else or clear filters
            </p>
            <Button 
              variant="link" 
              className="mt-2 text-primary"
              onClick={() => {
                setSearchQuery("");
                setSelectedCategory(null);
              }}
            >
              Clear all filters
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
