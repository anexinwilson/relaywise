"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowRight, Send } from "lucide-react";

const placeholderExamples = [
  "Monitor Discord for brand mentions...",
  "Send me a daily calendar summary...",
  "Create Notion tasks from starred emails...",
  "Alert me when someone mentions us on Twitter...",
];

export default function HeroSection() {
  const [currentPlaceholder, setCurrentPlaceholder] = useState(0);
  const [chatInput, setChatInput] = useState("");
  const [mounted, setMounted] = useState(false);
  const [isSignedIn, setIsSignedIn] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
    
    // Check if Clerk is properly configured and try to get auth status
    const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
    const hasClerk = key && !key.startsWith("pk_test_placeholder");
    
    if (hasClerk) {
      import("@clerk/nextjs").then((clerk) => {
        // We can't use hooks outside of component render, so we'll skip auth check
        // The redirect will happen anyway, and Clerk will handle auth state
      }).catch(() => {
        // Clerk not available
      });
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentPlaceholder((prev) => (prev + 1) % placeholderExamples.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const msg = chatInput.trim();
    if (msg) {
      // Always store message and redirect to dashboard or auth
      if (typeof window !== "undefined") {
        sessionStorage.setItem("pendingMessage", msg);
      }
      // Let the dashboard/auth handle the redirect logic
      router.push(`/dashboard?msg=${encodeURIComponent(msg)}`);
    } else {
      router.push("/auth/sign-up");
    }
  };

  if (!mounted) {
    return (
      <section className="pt-40 md:pt-48 pb-20 px-6" data-testid="hero-section">
        <div className="container mx-auto text-center max-w-5xl">
          <div className="animate-pulse">
            <div className="h-16 bg-muted rounded-lg mb-6 max-w-3xl mx-auto"></div>
            <div className="h-6 bg-muted rounded-lg mb-8 max-w-2xl mx-auto"></div>
            <div className="h-20 bg-muted rounded-2xl max-w-2xl mx-auto"></div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="pt-40 md:pt-48 pb-20 px-6" data-testid="hero-section">
      <div className="container mx-auto text-center max-w-5xl">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-5xl md:text-6xl font-bold mb-6"
        >
          Chat With Your Apps.{" "}
          <span className="text-gradient-primary">Automate Anything.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto"
        >
          862 apps. Powered by Composio. Ask anything, do anything. Automate it
          all — in plain English.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="max-w-2xl mx-auto"
        >
          <div className="bg-card rounded-2xl border border-border p-4 mb-4">
            <form onSubmit={handleSubmit} className="flex gap-3">
              <Input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={placeholderExamples[currentPlaceholder]}
                className="flex-1 h-12 bg-background text-foreground"
                data-testid="hero-chat-input"
              />
              <Button
                type="submit"
                className="h-12 px-6 gradient-primary hover:glow-primary"
                data-testid="hero-chat-submit"
              >
                <Send className="w-4 h-4" />
              </Button>
            </form>
            <p className="text-xs text-muted-foreground mt-3 text-center">
              Cognive will ask for the apps it needs
            </p>
          </div>

          <Button
            size="lg"
            className="gradient-primary hover:glow-primary text-lg px-8 py-6"
            onClick={() => router.push("/auth/sign-up")}
            data-testid="hero-start-free-btn"
          >
            Start Free <ArrowRight className="ml-2 w-5 h-5" />
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
