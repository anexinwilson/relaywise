"use client";

import { motion } from "framer-motion";
import { Search, Calendar, Target, MessageCircle, Megaphone } from "lucide-react";

const exampleCards = [
  {
    icon: Search,
    title: "Find Lost Documents",
    description:
      '"Find the contract Sarah sent last week" → Searches Gmail attachments + Slack files + Google Drive → Shows exact file',
    tag: "Pure chat • No more digging through apps",
    emoji: "🔍",
  },
  {
    icon: Calendar,
    title: "AI Time Blocking",
    description:
      "Reads Notion tasks → Checks Google Calendar for free slots → Auto-creates time blocks → Sends you daily schedule",
    tag: "Automation • Runs every morning at 9am",
    emoji: "📅",
  },
  {
    icon: Target,
    title: "Meeting Prep Brief",
    description:
      "30 min before meeting → Fetches attendee LinkedIn profiles → Pulls recent Slack conversations → Creates Notion brief",
    tag: "Automation • Walk in prepared every time",
    emoji: "🎯",
  },
  {
    icon: MessageCircle,
    title: "Lead Capture",
    description:
      'Someone says "interested in demo" in Discord → Saves to Notion CRM with contact info → Alerts sales team in Slack',
    tag: "Automation • Never miss a warm lead",
    emoji: "💬",
  },
  {
    icon: Megaphone,
    title: "Content Distribution",
    description:
      "Publish blog post → Auto-tweets with summary → Posts to LinkedIn → Adds to newsletter draft in Notion",
    tag: "Automation • Write once, reach everywhere",
    emoji: "📢",
  },
];

export default function ExamplesSection() {
  return (
    <section
      id="how-it-works"
      className="py-20 px-6 bg-card/30"
      data-testid="examples-section"
    >
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
          {exampleCards.map((card, index) => (
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
              <p className="text-xs text-primary font-medium">{card.tag}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
