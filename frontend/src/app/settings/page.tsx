"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { UserButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import {
  ArrowLeft,
  User,
  Plug,
  BarChart3,
  Settings as SettingsIcon,
  Download,
  Check,
} from "lucide-react";
import { useAppStore, useConnectedIntegrations } from "@/store/appStore";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function SettingsPage() {
  const router = useRouter();
  const connectedIntegrations = useConnectedIntegrations();
  const disconnectIntegration = useAppStore((state) => state.disconnectIntegration);

  const [name, setName] = useState("Demo User");
  const [email, setEmail] = useState("demo@example.com");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [inAppNotifications, setInAppNotifications] = useState(true);
  const [autoPause, setAutoPause] = useState(true);
  const [saved, setSaved] = useState(false);

  // Get connected apps details
  const connectedAppsDetails = connectedIntegrations;

  // Usage data (placeholder - will come from backend)
  const usage = {
    llmCalls: 1247,
    mcpCalls: 3582,
    activeAutomations: 3,
    queries: 47,
    storageUsedMB: 2.3,
  };

  const limits = {
    activeAutomations: 3,
    queries: 100,
    storageMB: 50,
  };

  const dailyLLMCalls = [
    { date: "2026-01-04", calls: 145 },
    { date: "2026-01-05", calls: 198 },
    { date: "2026-01-06", calls: 234 },
    { date: "2026-01-07", calls: 189 },
    { date: "2026-01-08", calls: 267 },
    { date: "2026-01-09", calls: 156 },
    { date: "2026-01-10", calls: 58 },
  ];

  const mcpCallsByIntegration: Record<string, number> = {
    discord: 1250,
    notion: 890,
    slack: 742,
    linkedin: 450,
    gmail: 250,
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="min-h-screen bg-background" data-testid="settings-page">
      {/* Header */}
      <header className="border-b border-border bg-card px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard")}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <Link href="/" className="flex items-center gap-2">
            <Image
              src="/relaywise-logo.svg"
              alt="Relaywise"
              width={32}
              height={32}
              className="rounded-lg"
            />
            <span className="text-lg font-bold text-foreground hidden sm:inline">
              Relaywise
            </span>
          </Link>
        </div>

        <div className="flex items-center gap-2">
          <UserButton fallback={<User className="w-4 h-4 text-primary" />} />
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-foreground mb-8">Settings</h1>

        <Tabs defaultValue="profile" className="space-y-8">
          <TabsList className="bg-card border border-border">
            <TabsTrigger value="profile" className="gap-2">
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">Profile</span>
            </TabsTrigger>
            <TabsTrigger value="integrations" className="gap-2">
              <Plug className="w-4 h-4" />
              <span className="hidden sm:inline">Integrations</span>
            </TabsTrigger>
            <TabsTrigger value="usage" className="gap-2">
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">Usage & Billing</span>
            </TabsTrigger>
            <TabsTrigger value="preferences" className="gap-2">
              <SettingsIcon className="w-4 h-4" />
              <span className="hidden sm:inline">Preferences</span>
            </TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-card border border-border rounded-2xl p-6"
            >
              <h2 className="text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
                <User className="w-5 h-5" />
                Profile
              </h2>

              <div className="flex items-center gap-6 mb-8">
                <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center text-2xl">
                  {name.charAt(0) || "U"}
                </div>
                <Button variant="outline">Change Photo</Button>
              </div>

              <div className="space-y-4 max-w-md">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="bg-background"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="bg-background"
                    disabled
                  />
                  <p className="text-xs text-muted-foreground">
                    Email is managed by your Clerk account
                  </p>
                </div>
                <div className="flex gap-3 pt-4">
                  <Button
                    onClick={handleSave}
                    className="gradient-primary hover:opacity-90"
                  >
                    {saved ? (
                      <>
                        <Check className="w-4 h-4 mr-1" /> Saved
                      </>
                    ) : (
                      "Save Changes"
                    )}
                  </Button>
                </div>
              </div>
            </motion.div>
          </TabsContent>

          {/* Integrations Tab */}
          <TabsContent value="integrations">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-card border border-border rounded-2xl p-6"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-foreground flex items-center gap-2">
                  <Plug className="w-5 h-5" />
                  Integrations
                </h2>
                <span className="text-muted-foreground">
                  Connected: {connectedAppsDetails.length}
                </span>
              </div>

              <div className="space-y-3 mb-6">
                {connectedAppsDetails.map((app) => (
                  <div
                    key={app.id}
                    className="flex items-center justify-between p-4 bg-background rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <Image
                        src={app.logo}
                        alt={app.name}
                        width={40}
                        height={40}
                        className="rounded-lg"
                        unoptimized
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.src = `https://ui-avatars.com/api/?name=${app.name}&background=374151&color=fff`;
                        }}
                      />
                      <span className="font-medium text-foreground">{app.name}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground hover:text-destructive"
                      onClick={() => disconnectIntegration(app.id)}
                    >
                      Disconnect
                    </Button>
                  </div>
                ))}
                {connectedAppsDetails.length === 0 && (
                  <p className="text-muted-foreground text-center py-4">
                    No integrations connected yet
                  </p>
                )}
              </div>

              <Button
                variant="outline"
                onClick={() => router.push("/integrations")}
                className="w-full"
              >
                + Add More Integrations
              </Button>
            </motion.div>
          </TabsContent>

          {/* Usage & Billing Tab */}
          <TabsContent value="usage">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* Plan Info */}
              <div className="bg-card border border-border rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-foreground flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Usage & Billing
                  </h2>
                </div>

                <div className="flex items-center justify-between p-4 bg-background rounded-lg mb-6">
                  <div>
                    <p className="font-semibold text-foreground">Free</p>
                    <p className="text-sm text-muted-foreground">
                      Relaywise is a personal project. There is no paid plan.
                    </p>
                  </div>
                </div>

                {/* Usage Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
                  <div className="bg-background rounded-lg p-4">
                    <p className="text-2xl font-bold text-foreground">
                      {usage.llmCalls.toLocaleString()}
                    </p>
                    <p className="text-sm text-muted-foreground">LLM Calls</p>
                  </div>
                  <div className="bg-background rounded-lg p-4">
                    <p className="text-2xl font-bold text-foreground">
                      {usage.mcpCalls.toLocaleString()}
                    </p>
                    <p className="text-sm text-muted-foreground">MCP Calls</p>
                  </div>
                  <div className="bg-background rounded-lg p-4">
                    <p className="text-2xl font-bold text-foreground">
                      {usage.activeAutomations} / {limits.activeAutomations}
                    </p>
                    <p className="text-sm text-muted-foreground">Active Automations</p>
                    <Progress
                      value={(usage.activeAutomations / limits.activeAutomations) * 100}
                      className="mt-2 h-1"
                    />
                  </div>
                  <div className="bg-background rounded-lg p-4">
                    <p className="text-2xl font-bold text-foreground">
                      {usage.queries} / {limits.queries}
                    </p>
                    <p className="text-sm text-muted-foreground">Queries This Month</p>
                    <Progress
                      value={(usage.queries / limits.queries) * 100}
                      className="mt-2 h-1"
                    />
                  </div>
                  <div className="bg-background rounded-lg p-4">
                    <p className="text-2xl font-bold text-foreground">
                      {usage.storageUsedMB} / {limits.storageMB} MB
                    </p>
                    <p className="text-sm text-muted-foreground">Storage Used</p>
                    <Progress
                      value={(usage.storageUsedMB / limits.storageMB) * 100}
                      className="mt-2 h-1"
                    />
                  </div>
                </div>
              </div>

              {/* Charts */}
              <div className="bg-card border border-border rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4">
                  📈 LLM Calls (Last 7 days)
                </h3>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={dailyLLMCalls}>
                      <XAxis
                        dataKey="date"
                        stroke="#6B7280"
                        fontSize={12}
                        tickFormatter={(v) => v.slice(5)}
                      />
                      <YAxis stroke="#6B7280" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#1F2937",
                          border: "1px solid #374151",
                          borderRadius: "8px",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="calls"
                        stroke="#F59E0B"
                        fill="url(#colorCalls)"
                      />
                      <defs>
                        <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-card border border-border rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4">
                  📊 MCP Calls by Integration
                </h3>
                <div className="space-y-3">
                  {Object.entries(mcpCallsByIntegration)
                    .sort((a, b) => b[1] - a[1])
                    .map(([app, calls]) => {
                      const maxCalls = Math.max(...Object.values(mcpCallsByIntegration));
                      return (
                        <div key={app} className="flex items-center gap-3">
                          <span className="text-sm text-foreground capitalize w-20">
                            {app}
                          </span>
                          <div className="flex-1 h-4 bg-background rounded-full overflow-hidden">
                            <div
                              className="h-full gradient-primary rounded-full"
                              style={{ width: `${(calls / maxCalls) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-muted-foreground w-16 text-right">
                            {calls.toLocaleString()}
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>

              <Button variant="outline" className="gap-2">
                <Download className="w-4 h-4" />
                Export Usage Report
              </Button>
            </motion.div>
          </TabsContent>

          {/* Preferences Tab */}
          <TabsContent value="preferences">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-card border border-border rounded-2xl p-6"
            >
              <h2 className="text-xl font-semibold text-foreground mb-6 flex items-center gap-2">
                <SettingsIcon className="w-5 h-5" />
                Preferences
              </h2>

              <div className="space-y-6 max-w-md">
                <div className="space-y-4">
                  <Label className="text-foreground">Notifications</Label>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      Email notifications
                    </span>
                    <Switch
                      checked={emailNotifications}
                      onCheckedChange={setEmailNotifications}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      In-app notifications
                    </span>
                    <Switch
                      checked={inAppNotifications}
                      onCheckedChange={setInAppNotifications}
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <Label className="text-foreground">Automation Behavior</Label>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      Auto-pause after 3 failures
                    </span>
                    <Switch checked={autoPause} onCheckedChange={setAutoPause} />
                  </div>
                </div>

                <Button
                  onClick={handleSave}
                  className="gradient-primary hover:opacity-90"
                >
                  {saved ? (
                    <>
                      <Check className="w-4 h-4 mr-1" /> Saved
                    </>
                  ) : (
                    "Save Preferences"
                  )}
                </Button>
              </div>
            </motion.div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
