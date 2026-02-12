"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Check, ChevronDown, ChevronUp } from "lucide-react";

const faqs = [
  {
    question: "Can I try Pro features before upgrading?",
    answer:
      "Yes! You can start with our free tier and upgrade anytime. All your automations and data will be preserved when you upgrade.",
  },
  {
    question: "What happens if I exceed my limits?",
    answer:
      "We'll notify you when you're approaching your limits. Your automations won't stop immediately - you'll have time to upgrade or reduce usage.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      'Absolutely. No contracts, no cancellation fees. Cancel anytime from your settings page and you won\'t be charged again.',
  },
  {
    question: "Do you offer refunds?",
    answer:
      "Yes, we offer a 14-day money-back guarantee. If you're not satisfied, contact us for a full refund.",
  },
  {
    question: "What payment methods do you accept?",
    answer:
      "We accept all major credit cards (Visa, Mastercard, American Express) and PayPal. Enterprise customers can pay via invoice.",
  },
];

export default function PricingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const router = useRouter();

  const handleGetStarted = () => {
    router.push("/auth/sign-up");
  };

  return (
    <div className="min-h-screen bg-background" data-testid="pricing-page">
      {/* Navigation */}
      <nav className="border-b border-border">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Image
              src="/cognive-logo.svg"
              alt="Cognive"
              width={32}
              height={32}
              className="rounded-lg"
            />
            <span className="text-xl font-bold text-foreground">Cognive</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/auth/sign-in">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Button
              className="gradient-primary hover:opacity-90"
              onClick={handleGetStarted}
            >
              Start Free
            </Button>
          </div>
        </div>
      </nav>

      {/* Header */}
      <section className="py-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
            Simple Pricing. No Tricks.
          </h1>
          <p className="text-xl text-muted-foreground">
            Start free. Upgrade when you&apos;re hooked.
          </p>
        </motion.div>
      </section>

      {/* Pricing Cards */}
      <section className="max-w-4xl mx-auto px-4 pb-16">
        <div className="grid md:grid-cols-2 gap-8">
          {/* Free Plan */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="bg-card border border-border rounded-2xl p-8"
          >
            <div className="mb-6">
              <h3 className="text-2xl font-bold text-foreground mb-2">Free</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold text-foreground">$0</span>
                <span className="text-muted-foreground">/month</span>
              </div>
              <p className="text-muted-foreground mt-2">
                Perfect for trying out Cognive
              </p>
            </div>

            <ul className="space-y-3 mb-8">
              {[
                "3 active automations",
                "100 queries/month",
                "50 MB storage",
                "5 connected apps",
                "Community support",
              ].map((feature, i) => (
                <li key={i} className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-success" />
                  <span className="text-foreground">{feature}</span>
                </li>
              ))}
            </ul>

            <Button
              variant="outline"
              className="w-full h-12"
              onClick={handleGetStarted}
            >
              Get Started Free
            </Button>
          </motion.div>

          {/* Pro Plan */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="bg-card border-2 border-primary rounded-2xl p-8 relative"
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="gradient-primary text-white text-sm font-medium px-4 py-1 rounded-full">
                Most Popular
              </span>
            </div>

            <div className="mb-6">
              <h3 className="text-2xl font-bold text-foreground mb-2">Pro</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold text-foreground">$15</span>
                <span className="text-muted-foreground">/month</span>
              </div>
              <p className="text-muted-foreground mt-2">
                For power users and small teams
              </p>
            </div>

            <ul className="space-y-3 mb-8">
              {[
                "Unlimited automations",
                "Unlimited queries",
                "5 GB storage",
                "Unlimited connected apps",
                "Priority support",
                "Advanced analytics",
                "Custom triggers",
                "API access",
              ].map((feature, i) => (
                <li key={i} className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-primary" />
                  <span className="text-foreground">{feature}</span>
                </li>
              ))}
            </ul>

            <Button
              className="w-full h-12 gradient-primary hover:opacity-90"
              onClick={handleGetStarted}
            >
              Start 14-Day Trial
            </Button>
          </motion.div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="max-w-3xl mx-auto px-4 pb-16">
        <h2 className="text-3xl font-bold text-foreground text-center mb-8">
          Frequently Asked Questions
        </h2>

        <div className="space-y-4">
          {faqs.map((faq, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.1 }}
              className="bg-card border border-border rounded-xl overflow-hidden"
            >
              <button
                className="w-full px-6 py-4 flex items-center justify-between text-left"
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
              >
                <span className="font-medium text-foreground">
                  {faq.question}
                </span>
                {openFaq === i ? (
                  <ChevronUp className="w-5 h-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-muted-foreground" />
                )}
              </button>
              {openFaq === i && (
                <div className="px-6 pb-4">
                  <p className="text-muted-foreground">{faq.answer}</p>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </section>

      {/* Contact Section */}
      <section className="py-16 text-center border-t border-border">
        <p className="text-muted-foreground">
          Still have questions?{" "}
          <a
            href="mailto:hello@cognive.app"
            className="text-primary hover:text-primary/90"
          >
            hello@cognive.app
          </a>
        </p>
      </section>
    </div>
  );
}
