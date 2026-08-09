"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Check, Loader2, ArrowLeft, Plug } from "lucide-react";
import { useAppStore, useConnectedIntegrations } from "@/store/appStore";
import appsCatalog from "@/apps_catalog.json";
import { cn } from "@/lib/utils";
import type { Integration } from "@/types";

interface CatalogApp {
  slug: string;
  name: string;
  description: string;
  logo: string;
  category: string;
}

const formattedApps: Integration[] = (appsCatalog as CatalogApp[]).map((app) => ({
  ...app,
  id: app.slug,
  supportsRealtime: false,
}));

const subscribeToHydration = () => () => undefined;

export default function IntegrationsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const mounted = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false,
  );
  const router = useRouter();
  const connectedIntegrations = useConnectedIntegrations();
  const connectIntegration = useAppStore((state) => state.connectIntegration);
  const disconnectIntegration = useAppStore(
    (state) => state.disconnectIntegration
  );

  useEffect(() => {
    const fetchConnected = async () => {
      try {
        const res = await fetch("/api/integrations/connected");
        const data = await res.json();
        if (data.slugs && Array.isArray(data.slugs)) {
          data.slugs.forEach((slug: string) => connectIntegration(slug));
        }
      } catch (err) {
        console.error("Failed to fetch connected apps:", err);
      }
    };
    
    fetchConnected();
    
    const handleFocus = () => {
      fetchConnected();
    };
    
    window.addEventListener('focus', handleFocus);
    
    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, [connectIntegration]);

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

    // Check 5-app limit
    if (connectedApps.length >= 5) {
      alert("You can connect only upto 5 apps. Please disconnect existing apps.");
      return;
    }

    setConnectingId(appId);

    try {
      const res = await fetch("/api/integrations/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug: appId }),
      });

      if (!res.ok) {
        throw new Error("Failed to start connection");
      }

      const data = await res.json();
      if (data?.url) {
        window.open(data.url, "_blank", "noopener,noreferrer");
      } else {
        throw new Error("No auth URL returned");
      }
    } catch (err) {
      console.error("Connect Error:", err);
      alert("Failed to start connection. Please try again.");
    } finally {
      setConnectingId(null);
    }
  };

  const handleDisconnect = async (appId: string) => {
    try {
      disconnectIntegration(appId);
      
      const res = await fetch("/api/integrations/disconnect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug: appId }),
      });
      
      if (!res.ok) {
        throw new Error("Failed to disconnect");
      }

      const verifyRes = await fetch("/api/integrations/connected");
      const data = await verifyRes.json();
      if (data.slugs && Array.isArray(data.slugs)) {
        data.slugs.forEach((slug: string) => {
          if (slug !== appId) connectIntegration(slug);
        });
      }
      
    } catch (err) {
      console.error("Disconnect Error:", err);
      connectIntegration(appId);
    }
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
            <Image
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
          <p className="text-muted-foreground">
            Connect {allApps.length} apps to Cognive. When you click Connect, we&apos;ll open a new
            tab to complete the app&apos;s authorization, and your connections will appear here
            once finished.
          </p>
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
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {connectedApps.map((app) => (
                <motion.div
                  key={app.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="bg-white/9 border border-success/30 rounded-xl p-4 flex flex-col justify-between h-full"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl flex-shrink-0 flex items-center justify-center p-1">
                      <Image
                        src={app.logo}
                        alt={app.name}
                        width={64}
                        height={64}
                        unoptimized
                        className="w-full h-full object-contain"
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.src = getFallbackLogo(app.name);
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-foreground truncate text-base">{app.name}</h3>
                    </div>
                  </div>
                  <div className="mt-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full text-xs text-destructive hover:text-destructive hover:bg-destructive/10 border border-destructive/30"
                      onClick={() => handleDisconnect(app.id)}
                    >
                      Disconnect
                    </Button>
                  </div>
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
                      <Image
                        src={app.logo}
                        alt={app.name}
                        width={64}
                        height={64}
                        unoptimized
                        className="w-full h-full object-contain"
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.src = getFallbackLogo(app.name);
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
                            Opening
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
