"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import Link from "next/link";
import { 
  Search, 
  Calendar, 
  Target, 
  MessageCircle, 
  Megaphone,
  ArrowRight, 
  Check,
  Send
} from "lucide-react";
import { PublicNav } from "./components/PublicNav";

const exampleCards = [
  {
    icon: Search,
    title: 'Find Lost Documents',
    description: '"Find the contract Sarah sent last week" → Searches Gmail attachments + Slack files + Google Drive → Shows exact file',
    tag: 'Pure chat • No more digging through apps',
    emoji: '🔍'
  },
  {
    icon: Calendar,
    title: 'AI Time Blocking',
    description: 'Reads Notion tasks → Checks Google Calendar for free slots → Auto-creates time blocks → Sends you daily schedule',
    tag: 'Automation • Runs every morning at 9am',
    emoji: '📅'
  },
  {
    icon: Target,
    title: 'Meeting Prep Brief',
    description: '30 min before meeting → Fetches attendee LinkedIn profiles → Pulls recent Slack conversations → Creates Notion brief',
    tag: 'Automation • Walk in prepared every time',
    emoji: '🎯'
  },
  {
    icon: MessageCircle,
    title: 'Lead Capture',
    description: 'Someone says "interested in demo" in Discord → Saves to Notion CRM with contact info → Alerts sales team in Slack',
    tag: 'Automation • Never miss a warm lead',
    emoji: '💬'
  },
  {
    icon: Megaphone,
    title: 'Content Distribution',
    description: 'Publish blog post → Auto-tweets with summary → Posts to LinkedIn → Adds to newsletter draft in Notion',
    tag: 'Automation • Write once, reach everywhere',
    emoji: '📢'
  },
];

const pricingPlans = [
  {
    name: 'Free',
    price: '$0',
    features: ['3 active automations', '100 queries/month', '50 MB storage', 'Email support'],
  },
  {
    name: 'Pro',
    price: '$15',
    period: '/month',
    features: ['Unlimited automations', 'Unlimited queries', '10 GB storage', 'Priority support', 'Advanced analytics'],
    highlighted: true,
  },
];

const testimonials = [
  {
    quote: "Finally, automation that doesn't need a 30-minute tutorial.",
    author: "Sarah Chen",
    role: "Product Manager"
  },
  {
    quote: "I set up 5 automations in 10 minutes. This is the future.",
    author: "Marcus Johnson",
    role: "Startup Founder"
  },
  {
    quote: "It's like having an assistant that actually understands me.",
    author: "Emily Rodriguez",
    role: "Marketing Lead"
  }
];

const placeholderExamples = [
  "Monitor Discord for brand mentions...",
  "Send me a daily calendar summary...",
  "Create Notion tasks from starred emails...",
  "Alert me when someone mentions us on Twitter..."
];

export default function LandingPage() {
  const router = useRouter();
  const [currentPlaceholder, setCurrentPlaceholder] = useState(0);
  const [chatInput, setChatInput] = useState('');

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentPlaceholder((prev) => (prev + 1) % placeholderExamples.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      {/* Hero Section */}
      <section className="pt-40 md:pt-48 pb-20 px-6">
        <div className="container mx-auto text-center max-w-5xl">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-5xl md:text-6xl font-bold mb-6"
          >
            Chat With Your Apps.{' '}
            <span className="text-gradient-primary">Automate Anything.</span>
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto"
          >
            MCP-powered. 500+ integrations. Ask anything, do anything. Automate it all.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <SignedOut>
              <Link href="/auth" className="gradient-primary hover:glow-primary text-lg px-8 py-6 rounded-lg inline-flex items-center gap-2 text-white">
                Start Free <ArrowRight className="w-5 h-5" />
              </Link>
            </SignedOut>
            <SignedIn>
              <Link href="/dashboard" className="gradient-primary hover:glow-primary text-lg px-8 py-6 rounded-lg inline-flex items-center gap-2 text-white">
                Go to Dashboard <ArrowRight className="w-5 h-5" />
              </Link>
            </SignedIn>
          </motion.div>
        </div>
      </section>

      {/* See What's Possible Section */}
      <section className="py-20 px-6 bg-card/30">
        <div className="container mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              See What&apos;s Possible
            </h2>
            <p className="text-muted-foreground text-lg">
              Real workflows. Built in seconds.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {exampleCards.map((card, index) => {
              const Icon = card.icon;
              return (
                <motion.div
                  key={card.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  viewport={{ once: true }}
                  whileHover={{ y: -4 }}
                  className="bg-card rounded-xl border border-border p-6 hover:border-primary/50 hover-glow transition-all cursor-pointer group"
                >
                  <span className="text-3xl mb-4 block">{card.emoji}</span>
                  <h3 className="text-xl font-bold mb-3 text-foreground group-hover:text-primary transition-colors">
                    {card.title}
                  </h3>
                  <p className="text-muted-foreground text-sm mb-4 leading-relaxed">
                    {card.description}
                  </p>
                  <p className="text-xs text-primary font-medium">
                    {card.tag}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Integrations Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            500+ Apps. One Conversation.
          </h2>
          <p className="text-muted-foreground mb-12">
            Connect the tools you already use
          </p>

          <div className="grid grid-cols-4 md:grid-cols-6 gap-6 max-w-3xl mx-auto mb-8">
            {Array.from({ length: 12 }).map((_, i) => (
              <motion.div
                key={i}
                whileHover={{ scale: 1.1 }}
                className="bg-card rounded-xl p-4 border border-border hover:border-primary/50 transition-all"
              >
                <div className="w-10 h-10 mx-auto rounded-lg bg-muted flex items-center justify-center">
                  <span className="text-xs text-muted-foreground">App {i + 1}</span>
                </div>
              </motion.div>
            ))}
          </div>

          <Link href="/integrations" className="text-primary hover:underline inline-flex items-center gap-1">
            See all integrations <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Try It Section - Mini Chat */}
      <section className="py-20 px-6 bg-card/30">
        <div className="container mx-auto max-w-2xl">
          <div className="text-center mb-8">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Try It Now
            </h2>
            <p className="text-muted-foreground">
              Just type what you want to automate
            </p>
          </div>

          <div className="bg-card rounded-2xl border border-border p-6">
            <form 
              className="flex gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                router.push('/auth');
              }}
            >
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={placeholderExamples[currentPlaceholder]}
                className="flex-1 h-12 bg-background text-foreground border border-border rounded-lg px-4 focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button type="submit" className="h-12 px-6 gradient-primary rounded-lg text-white">
                <Send className="w-4 h-4" />
              </button>
            </form>
            <p className="text-xs text-muted-foreground mt-3 text-center">
              Cognive will ask for the apps it needs
            </p>
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="py-20 px-6">
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
                    ? 'border-primary bg-card glow-primary'
                    : 'border-border bg-card'
                }`}
              >
                <h3 className="text-2xl font-bold mb-2 text-foreground">{plan.name}</h3>
                <div className="mb-6">
                  <span className="text-4xl font-bold text-foreground">{plan.price}</span>
                  {plan.period && <span className="text-muted-foreground">{plan.period}</span>}
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2">
                      <Check className="w-5 h-5 text-success" />
                      <span className="text-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
                <SignedOut>
                  <Link
                    href="/auth"
                    className={`w-full px-4 py-2 rounded-lg block text-center ${
                      plan.highlighted 
                        ? 'gradient-primary text-white' 
                        : 'border border-border hover:bg-card'
                    }`}
                  >
                    Get Started
                  </Link>
                </SignedOut>
              </div>
            ))}
          </div>

          <div className="text-center mt-8">
            <Link href="/pricing" className="text-primary hover:underline inline-flex items-center gap-1">
              See detailed pricing <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 px-6 bg-card/30">
        <div className="container mx-auto">
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                viewport={{ once: true }}
                className="bg-card rounded-xl border border-border p-6"
              >
                <p className="text-foreground mb-4 italic">&quot;{testimonial.quote}&quot;</p>
                <div>
                  <p className="font-semibold text-foreground">{testimonial.author}</p>
                  <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-foreground">Ready to try?</h2>
          <p className="text-muted-foreground mb-8">No credit card. Cancel anytime.</p>
          <SignedOut>
            <Link href="/auth" className="gradient-primary hover:glow-primary text-lg px-8 py-6 rounded-lg text-white inline-block">
              Start Free
            </Link>
          </SignedOut>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12 px-6">
        <div className="container mx-auto">
          <div className="text-center text-muted-foreground text-sm">
            <p>Built for humans who hate complicated tools</p>
            <p className="text-xs mt-1">Powered by Model Context Protocol</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
