"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Check, ArrowRight } from "lucide-react";

const pricingPlans = [
  {
    name: "Free",
    price: "$0",
    features: [
      "3 active automations",
      "100 queries/month",
      "50 MB storage",
      "Email support",
    ],
  },
  {
    name: "Pro",
    price: "$15",
    period: "/month",
    features: [
      "Unlimited automations",
      "Unlimited queries",
      "10 GB storage",
      "Priority support",
      "Advanced analytics",
    ],
    highlighted: true,
  },
];

export default function PricingSection() {
  return (
    <section className="py-20 px-6" data-testid="pricing-section">
      <div className="container mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
          Simple Pricing
        </h2>
        <p className="text-muted-foreground text-center mb-12">
          Start free. Upgrade when you&apos;re hooked.
        </p>

        <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
          {pricingPlans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-xl border p-8 ${
                plan.highlighted
                  ? "border-primary bg-card glow-primary"
                  : "border-border bg-card"
              }`}
            >
              <h3 className="text-2xl font-bold mb-2 text-foreground">
                {plan.name}
              </h3>
              <div className="mb-6">
                <span className="text-4xl font-bold text-foreground">
                  {plan.price}
                </span>
                {plan.period && (
                  <span className="text-muted-foreground">{plan.period}</span>
                )}
              </div>
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2">
                    <Check className="w-5 h-5 text-success" />
                    <span className="text-foreground">{feature}</span>
                  </li>
                ))}
              </ul>
              <Link href="/auth/sign-up">
                <Button
                  className={`w-full ${plan.highlighted ? "gradient-primary" : ""}`}
                  variant={plan.highlighted ? "default" : "outline"}
                >
                  Get Started
                </Button>
              </Link>
            </div>
          ))}
        </div>

        <div className="text-center mt-8">
          <Link
            href="/pricing"
            className="text-primary hover:underline inline-flex items-center gap-1"
          >
            See detailed pricing <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
