"use client";

import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Show, UserButton } from "@clerk/nextjs";

export function Logo({ showText = true }: { showText?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2 group">
      <Image
        src="/relaywise-logo.svg"
        alt="Relaywise"
        width={36}
        height={36}
        className="group-hover:glow-primary transition-all rounded-lg"
      />
      {showText && <span className="text-xl font-bold text-foreground">Relaywise</span>}
    </Link>
  );
}

export function PublicNav() {
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
        </div>

        <div className="flex items-center gap-4">
          <Show when="signed-out">
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
          </Show>
          <Show when="signed-in">
            <Link href="/dashboard">
              <Button className="gradient-primary hover:glow-primary transition-all">
                Dashboard
              </Button>
            </Link>
            <UserButton />
          </Show>
        </div>
      </div>
    </nav>
  );
}
