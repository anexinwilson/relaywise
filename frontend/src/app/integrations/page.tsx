"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Check, Loader2, ArrowLeft, Plug } from "lucide-react";
import { useAppStore, useConnectedIntegrations } from "@/store/appStore";
import integrationsData from "@/data/integrations.json";
import { cn } from "@/lib/utils";

const categoryNames: Record<string, string> = {
  communication: "Communication",
  productivity: "Productivity",
  email: "Email",
  social: "Social Media",
  developer: "Developer Tools",
  storage: "Cloud Storage",
  crm: "CRM",
};

export default function IntegrationsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [isSignedIn, setIsSignedIn] = useState(true); // Default to signed in for demo
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
  }, []);

  const connectedIntegrations = useConnectedIntegrations();
  const connectIntegration = useAppStore((state) => state.connectIntegration);
  const disconnectIntegration = useAppStore(
    (state) => state.disconnectIntegration
  );

  const allApps = integrationsData.popular;
  const categories = Object.keys(integrationsData.categories);

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
    if (!isSignedIn) {
      router.push("/auth/sign-in");
      return;
    }

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
            />
            <span className="text-lg font-bold text-foreground hidden sm:inline">
              Cognive
            </span>
          </Link>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
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
          <p className="text-muted-foreground">Connect 500+ apps to Cognive</p>
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
                  className="bg-card border border-success/30 rounded-xl p-4 text-center group"
                >
                  <Image
                    src={app.logo}
                    alt={app.name}
                    width={48}
                    height={48}
                    className="mx-auto mb-3 rounded-xl"
                    unoptimized
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = `https://ui-avatars.com/api/?name=${app.name}&background=374151&color=fff`;
                    }}
                  />
                  <p className="text-sm font-medium text-foreground mb-2">
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

        {/* Category Tabs */}
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
          <Button
            variant={selectedCategory === null ? "default" : "ghost"}
            size="sm"
            onClick={() => setSelectedCategory(null)}
            className={selectedCategory === null ? "gradient-primary" : ""}
          >
            All
          </Button>
          {categories.map((cat) => (
            <Button
              key={cat}
              variant={selectedCategory === cat ? "default" : "ghost"}
              size="sm"
              onClick={() => setSelectedCategory(cat)}
              className={selectedCategory === cat ? "gradient-primary" : ""}
            >
              {categoryNames[cat] || cat}
            </Button>
          ))}
        </div>

        {/* Apps Grid */}
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-4">
            {selectedCategory
              ? categoryNames[selectedCategory] || selectedCategory
              : "🔥 MOST POPULAR"}
          </h2>
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
                  transition={{ duration: 0.3, delay: i * 0.03 }}
                  className={cn(
                    "bg-card border rounded-xl p-4 transition-all",
                    isConnected
                      ? "border-success/30"
                      : "border-border hover:border-primary/50"
                  )}
                  data-testid={`integration-card-${app.id}`}
                >
                  <div className="flex items-start gap-3">
                    <Image
                      src={app.logo}
                      alt={app.name}
                      width={48}
                      height={48}
                      className="rounded-xl flex-shrink-0"
                      unoptimized
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = `https://ui-avatars.com/api/?name=${app.name}&background=374151&color=fff`;
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-foreground flex items-center gap-2">
                        {app.name}
                        {app.supportsRealtime && (
                          <span className="text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                            Real-time
                          </span>
                        )}
                      </h3>
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                        {app.description}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4">
                    {isConnected ? (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full text-success border-success/30"
                        disabled
                      >
                        <Check className="w-4 h-4 mr-1" />
                        Connected
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full hover:bg-primary hover:text-primary-foreground hover:border-primary"
                        onClick={() => handleConnect(app.id)}
                        disabled={isConnecting}
                        data-testid={`connect-btn-${app.id}`}
                      >
                        {isConnecting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                            Connecting...
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
          <div className="text-center py-12">
            <p className="text-muted-foreground">
              No apps found matching &quot;{searchQuery}&quot;
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
