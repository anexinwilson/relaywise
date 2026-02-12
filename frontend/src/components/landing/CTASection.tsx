"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function CTASection() {
  return (
    <section className="py-20 px-6" data-testid="cta-section">
      <div className="container mx-auto text-center">
        <h2 className="text-3xl md:text-4xl font-bold mb-4 text-foreground">
          Ready to try?
        </h2>
        <p className="text-muted-foreground mb-8">
          No credit card. Cancel anytime.
        </p>
        <Link href="/auth/sign-up">
          <Button
            size="lg"
            className="gradient-primary hover:glow-primary text-lg px-8"
            data-testid="cta-start-free-btn"
          >
            Start Free
          </Button>
        </Link>
      </div>
    </section>
  );
}
