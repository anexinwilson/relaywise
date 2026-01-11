"use client";

import Link from "next/link";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import { Zap, ArrowRight } from "lucide-react";

export function Logo({ showText = true }: { showText?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2 group">
      <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center group-hover:glow-primary transition-all">
        <Zap className="w-5 h-5 text-white" />
      </div>
      {showText && (
        <span className="text-xl font-bold text-foreground">Cognive</span>
      )}
    </Link>
  );
}

export function PublicNav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="container mx-auto px-6 py-4 flex items-center justify-between">
        <Logo />
        
        <div className="hidden md:flex items-center gap-8">
          <a 
            href="#how-it-works" 
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            How It Works
          </a>
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
            <Link href="/auth" className="text-muted-foreground hover:text-foreground transition-colors px-4 py-2">
              Sign In
            </Link>
            <Link href="/auth" className="gradient-primary hover:glow-primary transition-all px-4 py-2 rounded-lg text-white">
              Start Free
            </Link>
          </SignedOut>
          <SignedIn>
            <Link href="/dashboard" className="gradient-primary hover:glow-primary transition-all px-4 py-2 rounded-lg text-white">
              Dashboard
            </Link>
          </SignedIn>
        </div>
      </div>
    </nav>
  );
}
