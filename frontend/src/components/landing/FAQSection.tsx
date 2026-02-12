"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqItems = [
  {
    question: "What is Cognive?",
    answer:
      "Cognive is where you talk to your apps instead of clicking through them. Connect your tools, Slack, Notion, Gmail, Discord, HubSpot, whatever you use, and just tell Cognive what you want. It pulls data, takes action, and runs automations. All in plain English, no setup screens, no learning curve.",
  },
  {
    question: "What can I actually do with it?",
    answer: `Chat with your apps. Ask "what customer complaints came in today?" and Cognive pulls answers from Slack, Discord, Intercom, wherever, all at once. No switching tabs, no copy pasting.

Instant actions. "Save these to Notion sorted by urgency" or "send this to the support channel." Done immediately, no workflow to build first.

Set up automations. Describe it once: "When someone mentions our product in Discord, check if they are a decision maker and notify me." Cognive figures out the rest and runs it 24/7.

Multi step workflows. Monitor something, process it, route it, notify someone. Chain it all together from one conversation.

Confirmation before critical actions. For anything important, Cognive asks before it executes. It does not just run things blindly.`,
  },
  {
    question: "How many apps does Cognive connect to?",
    answer:
      "862 apps in Cognive, powered by Composio Managed MCP. If your team uses it, it is probably already there.",
  },
  {
    question: "How is this different from Zapier, Make, or n8n?",
    answer: `All three make you think like an engineer before you get anything done. Zapier has you clicking through 20 screens. Make has visual nodes that look like a circuit board. n8n is practically a coding tool. All of them dump the cognitive load on you.

Cognive flips that. You describe what you want in plain English and it handles the wiring. No triggers to configure, no fields to map, no logic trees to untangle. Less time figuring out the tool, more time actually getting work done.

The other thing none of them can do: ask a live question across multiple apps and get an instant answer. That is a completely different kind of useful.`,
  },
  {
    question: "Is my data private?",
    answer:
      'Yes, and here is why you can trust that. Your data runs on AWS AgentCore, which is Amazon\'s infrastructure built specifically for AI agents that handle sensitive workflows. We chose it because it keeps your data isolated in memory, not sitting in a shared database where things can leak. The only way in is through your account login. Not us, not anyone else. Just you.\n\nFor critical workflows, Cognive will ask for your confirmation before doing anything. It does not act blindly.',
  },
  {
    question: "Who is this for?",
    answer:
      'Anyone who has too many apps open and too little time. The person managing a side project who does not want to learn Zapier just to save some time. The freelancer juggling clients across five tools. The creator trying to keep up with their community. The hobbyist who just wants their stuff to talk to each other without writing a single line of code. If you have ever thought "there has to be a faster way to do this," this is it.',
  },
  {
    question: "How long does setup take?",
    answer:
      "For a one time action: seconds. For an automation running permanently: under a minute. You describe it, Cognive asks a clarifying question or two, and it is live.",
  },
  {
    question: "What does it cost?",
    answer: "$15 a month. That is it.",
  },
];

export default function FAQSection() {
  return (
    <section className="py-20 px-6 bg-card/30" data-testid="faq-section">
      <div className="container mx-auto max-w-3xl">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-12">
          Frequently Asked Questions
        </h2>

        <Accordion type="single" collapsible className="w-full space-y-3">
          {faqItems.map((item, index) => (
            <AccordionItem
              key={index}
              value={`faq-${index}`}
              className="bg-card border border-border rounded-xl px-6"
            >
              <AccordionTrigger className="text-left text-foreground font-semibold hover:text-primary transition-colors">
                {item.question}
              </AccordionTrigger>
              <AccordionContent className="text-muted-foreground whitespace-pre-line leading-relaxed">
                {item.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
