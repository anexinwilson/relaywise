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
      "Relaywise lets you operate your apps by asking. Connect Slack, Notion, Gmail, Discord or whatever else you use, then describe what you want in plain English. It works out which tools to call, calls them, and reports back.",
  },
  {
    question: "What can I actually do with it?",
    answer: `Ask questions across your apps. "What was my last message in Slack?" or "find the file Sarah sent me" and it goes and looks, without you switching tabs.

Take actions. "Send this to the support channel" or "create a page in Notion with these notes." It confirms first, then does it.

Work across several apps in one request. Read from one, write to another, in a single conversation.

It remembers. Conversations continue where you left them, and things you tell it about yourself carry into later sessions.`,
  },
  {
    question: "How many apps does it connect to?",
    answer:
      "Around 860, through Composio's Tool Router. Tools are discovered when you ask for something rather than configured in advance, so anything Composio supports is reachable without setup on your side.",
  },
  {
    question: "How is this different from Zapier, Make, or n8n?",
    answer: `Those are workflow builders. You define triggers, map fields and wire steps together in advance, and the workflow then runs on its own.

Relaywise is the opposite shape. There is nothing to build first. You ask for something and it works out the steps at that moment. That makes it good for one-off requests and questions spanning several apps, which a workflow builder is clumsy at.

The tradeoff is real: Relaywise does not run anything on a schedule or in the background. If you need something to fire automatically at 9am every day, a workflow tool is the right choice.`,
  },
  {
    question: "Does it ask before doing things?",
    answer:
      "It reads without asking, and confirms before writing, sending or deleting. Your app passwords and tokens are never stored by Relaywise. Connected-app credentials stay with Composio.",
  },
  {
    question: "Who is this for?",
    answer:
      "People with more apps open than time. If you keep hunting through Slack, email and notes for one thing, or want something done in another app without leaving what you are doing, this shortens that.",
  },
  {
    question: "How long does setup take?",
    answer:
      "Connecting an app is an OAuth flow, so seconds each. After that you just ask. There is nothing to configure, no triggers or field mapping.",
  },
  {
    question: "What does it cost?",
    answer: `Nothing, and there is no paid plan or card to enter. Every account gets 100 credits a month, which reset at the start of each month.

Credits are metered from actual model usage, so a short question costs little and a long conversation touching several apps costs more. The allowance exists so one person cannot run up the model bill for everyone.`,
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
