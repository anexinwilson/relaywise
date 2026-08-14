"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqItems = [
  {
    question: "What is Relaywise?",
    answer:
      "Relaywise is where you talk to your apps instead of clicking through them. Connect your tools, Slack, Notion, Gmail, Discord, HubSpot, whatever you use, and just tell Relaywise what you want. It pulls data, takes action, and runs automations. All in plain English, no setup screens, no learning curve.",
  },
  {
    question: "What can I actually do with it?",
    answer: `Chat with your apps. Ask "what customer complaints came in today?" and Relaywise pulls answers from Slack, Discord, Intercom, wherever, all at once. No switching tabs, no copy pasting.

Instant actions. "Save these to Notion sorted by urgency" or "send this to the support channel." Done immediately, no workflow to build first.

Set up automations. Describe it once: "When someone mentions our product in Discord, check if they are a decision maker and notify me." Relaywise figures out the rest and runs it 24/7.

Multi step workflows. Monitor something, process it, route it, notify someone. Chain it all together from one conversation.

Confirmation before critical actions. For anything important, Relaywise asks before it executes. It does not just run things blindly.`,
  },
  {
    question: "How many apps does Relaywise connect to?",
    answer:
      "862 apps in Relaywise, powered by Composio Managed MCP. If your team uses it, it is probably already there.",
  },
  {
    question: "How is this different from Zapier, Make, or n8n?",
    answer: `All three make you think like an engineer before you get anything done. Zapier has you clicking through 20 screens. Make has visual nodes that look like a circuit board. n8n is practically a coding tool. All of them dump the cognitive load on you.

Relaywise flips that. You describe what you want in plain English and it handles the wiring. No triggers to configure, no fields to map, no logic trees to untangle. Less time figuring out the tool, more time actually getting work done.

The other thing none of them can do: ask a live question across multiple apps and get an instant answer. That is a completely different kind of useful.`,
  },
  {
    question: "Does it ask before doing things?",
    answer:
      "Yes. For anything important or hard to undo, Relaywise checks with you first rather than running it blindly. Your app passwords and tokens are never stored here, connected-app credentials stay with Composio.",
  },
  {
    question: "Who is this for?",
    answer:
      'Anyone who has too many apps open and too little time. The person managing a side project who does not want to learn Zapier just to save some time. The freelancer juggling clients across five tools. The creator trying to keep up with their community. The hobbyist who just wants their stuff to talk to each other without writing a single line of code. If you have ever thought "there has to be a faster way to do this," this is it.',
  },
  {
    question: "How long does setup take?",
    answer:
      "For a one time action: seconds. For an automation running permanently: under a minute. You describe it, Relaywise asks a clarifying question or two, and it is live.",
  },
  {
    question: "What does it cost?",
    answer:
      "Nothing. You get 100 credits a month, and they reset at the start of each month. There is no paid plan and no card to enter.\n\nThe allowance exists so one person cannot run up the model bill for everyone else. A typical request costs a fraction of a credit, so you are unlikely to notice it.",
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
