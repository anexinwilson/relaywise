"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Zap, Plug, Send, ArrowRight } from "lucide-react";
import { useAppStore } from "@/store/appStore";
import integrationsData from "@/data/integrations.json";

const templates = [
  { name: "Notion → Calendar", icon: "📅" },
  { name: "Discord → Slack", icon: "💬" },
  { name: "Email Auto-org", icon: "📧" },
];

export default function OnboardingPage() {
  const [chatInput, setChatInput] = useState("");
  const router = useRouter();
  const { setHasCompletedOnboarding } = useAppStore();

  const popularApps = integrationsData.popular.slice(0, 12);

  const handlePickTemplate = (templateName: string) => {
    setHasCompletedOnboarding(true);
    router.push(`/dashboard?msg=${encodeURIComponent(`Create ${templateName} automation`)}`);
  };

  const handleBrowseApps = () => {
    setHasCompletedOnboarding(true);
    router.push("/integrations");
  };

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    setHasCompletedOnboarding(true);
    router.push(`/dashboard?msg=${encodeURIComponent(chatInput)}`);
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4" data-testid="onboarding-page">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-4xl"
      >
        {/* Header */}
        <div className="text-center mb-12">
          <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mx-auto mb-6">
            <span className="text-white font-bold text-3xl">C</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            Welcome to Cognive
          </h1>
          <p className="text-xl text-muted-foreground">
            Let&apos;s connect your first app and start automating
          </p>
        </div>

        {/* Options */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          {/* Templates Option */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="bg-card border border-border rounded-2xl p-8"
          >
            <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-primary" />
            </div>
            <h2 className="text-xl font-bold text-foreground mb-2">
              Try a Template
            </h2>
            <p className="text-muted-foreground mb-6">
              See how it works instantly
            </p>

            <div className="space-y-3 mb-6">
              {templates.map((template, i) => (
                <button
                  key={i}
                  onClick={() => handlePickTemplate(template.name)}
                  className="w-full flex items-center gap-3 p-3 rounded-lg bg-background hover:bg-muted transition-colors text-left"
                  data-testid={`template-${i}`}
                >
                  <span className="text-xl">{template.icon}</span>
                  <span className="text-foreground">{template.name}</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground ml-auto" />
                </button>
              ))}
            </div>

            <Button
              variant="outline"
              className="w-full"
              onClick={() => handlePickTemplate(templates[0].name)}
            >
              Pick Template
            </Button>
          </motion.div>

          {/* Connect Apps Option */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="bg-card border border-border rounded-2xl p-8"
          >
            <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center mb-4">
              <Plug className="w-6 h-6 text-primary" />
            </div>
            <h2 className="text-xl font-bold text-foreground mb-2">
              Connect Your Apps
            </h2>
            <p className="text-muted-foreground mb-6">
              Start with the apps you use most
            </p>

            <div className="grid grid-cols-4 gap-3 mb-6">
              {popularApps.map((app) => (
                <button
                  key={app.id}
                  className="aspect-square rounded-lg bg-background hover:bg-muted transition-colors flex items-center justify-center p-2 group"
                  onClick={handleBrowseApps}
                >
                  <Image
                    src={app.logo}
                    alt={app.name}
                    width={32}
                    height={32}
                    className="rounded group-hover:scale-110 transition-transform"
                    unoptimized
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = `https://ui-avatars.com/api/?name=${app.name}&background=374151&color=fff`;
                    }}
                  />
                </button>
              ))}
            </div>

            <Button
              className="w-full gradient-primary hover:opacity-90"
              onClick={handleBrowseApps}
              data-testid="browse-apps-btn"
            >
              Browse 500+ Apps
            </Button>
          </motion.div>
        </div>

        {/* Chat Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="text-center"
        >
          <p className="text-muted-foreground mb-4">
            Or just tell me what you want...
          </p>
          <form onSubmit={handleChatSubmit} className="max-w-xl mx-auto">
            <div className="relative">
              <Input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="e.g., Monitor my Discord for brand mentions"
                className="h-14 pr-12 bg-card border-border text-lg"
                data-testid="onboarding-chat-input"
              />
              <Button
                type="submit"
                size="icon"
                className="absolute right-2 top-1/2 -translate-y-1/2 gradient-primary hover:opacity-90"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-sm text-muted-foreground mt-3">
              Cognive will ask for the apps it needs
            </p>
          </form>
        </motion.div>
      </motion.div>
    </div>
  );
}
