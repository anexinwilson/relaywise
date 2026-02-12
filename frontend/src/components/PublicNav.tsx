"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

export function Logo({ showText = true }: { showText?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2 group">
      <Image
        src="/cognive-logo.svg"
        alt="Cognive"
        width={36}
        height={36}
        className="group-hover:glow-primary transition-all rounded-lg"
      />
      {showText && (
        <span className="text-xl font-bold text-foreground">Cognive</span>
      )}
    </Link>
  );
}

export function PublicNav() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [ClerkComponents, setClerkComponents] = useState<{
    SignedIn: React.ComponentType<{ children: React.ReactNode }>;
    SignedOut: React.ComponentType<{ children: React.ReactNode }>;
    UserButton: React.ComponentType<{ afterSignOutUrl?: string }>;
  } | null>(null);

  useEffect(() => {
    setMounted(true);
    
    // Check if Clerk is properly configured
    const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
    const hasClerk = key && !key.startsWith("pk_test_placeholder");

    if (hasClerk) {
      import("@clerk/nextjs").then((clerk) => {
        setClerkComponents({
          SignedIn: clerk.SignedIn,
          SignedOut: clerk.SignedOut,
          UserButton: clerk.UserButton,
        });
      }).catch(() => {
        // Clerk not available
      });
    }
  }, []);

  // Always show sign-in/sign-up buttons before client hydration
  if (!mounted) {
    return (
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Logo />
          <div className="hidden md:flex items-center gap-8">
            <Link
              href="/#how-it-works"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              How It Works
            </Link>
            <Link
              href="/integrations"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Integrations
            </Link>
            <Link
              href="/pricing"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/auth/sign-in">
              <Button
                variant="ghost"
                className="text-muted-foreground hover:text-foreground"
              >
                Sign In
              </Button>
            </Link>
            <Link href="/auth/sign-up">
              <Button className="gradient-primary hover:glow-primary transition-all">
                Start Free
              </Button>
            </Link>
          </div>
        </div>
      </nav>
    );
  }

  // Fallback navigation when Clerk is not configured or not yet loaded
  if (!ClerkComponents) {
    return (
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Logo />
          <div className="hidden md:flex items-center gap-8">
            <Link
              href="/#how-it-works"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              How It Works
            </Link>
            <Link
              href="/integrations"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Integrations
            </Link>
            <Link
              href="/pricing"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/auth/sign-in">
              <Button
                variant="ghost"
                className="text-muted-foreground hover:text-foreground"
              >
                Sign In
              </Button>
            </Link>
            <Link href="/auth/sign-up">
              <Button className="gradient-primary hover:glow-primary transition-all">
                Start Free
              </Button>
            </Link>
          </div>
        </div>
      </nav>
    );
  }

  const { SignedIn, SignedOut, UserButton } = ClerkComponents;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="container mx-auto px-6 py-4 flex items-center justify-between">
        <Logo />

        <div className="hidden md:flex items-center gap-8">
          <Link
            href="/#how-it-works"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            How It Works
          </Link>
          <Link
            href="/integrations"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Integrations
          </Link>
          <Link
            href="/pricing"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Pricing
          </Link>
        </div>

        <div className="flex items-center gap-4">
          <SignedOut>
            <Link href="/auth/sign-in">
              <Button
                variant="ghost"
                className="text-muted-foreground hover:text-foreground"
              >
                Sign In
              </Button>
            </Link>
            <Link href="/auth/sign-up">
              <Button className="gradient-primary hover:glow-primary transition-all">
                Start Free
              </Button>
            </Link>
          </SignedOut>
          <SignedIn>
            <Link href="/dashboard">
              <Button className="gradient-primary hover:glow-primary transition-all">
                Dashboard
              </Button>
            </Link>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
        </div>
      </div>
    </nav>
  );
}
