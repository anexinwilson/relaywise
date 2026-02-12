"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { ArrowRight } from "lucide-react";
import integrationsData from "@/data/integrations.json";

export default function IntegrationsSection() {
  const popularApps = integrationsData.popular.slice(0, 12);

  return (
    <section className="py-20 px-6" data-testid="integrations-section">
      <div className="container mx-auto text-center">
        <h2 className="text-3xl md:text-4xl font-bold mb-4">
          862 Apps. One Conversation.
        </h2>
        <p className="text-muted-foreground mb-2">
          Connect the tools you already use
        </p>
        <p className="text-sm text-primary font-medium mb-12">
          Powered by Composio
        </p>

        <div className="grid grid-cols-4 md:grid-cols-6 gap-6 max-w-3xl mx-auto mb-8">
          {popularApps.map((app) => (
            <motion.div
              key={app.id}
              whileHover={{ scale: 1.1 }}
              className="bg-card rounded-xl p-4 border border-border hover:border-primary/50 transition-all"
            >
              <Image
                src={app.logo}
                alt={app.name}
                width={40}
                height={40}
                className="mx-auto rounded-lg"
                unoptimized
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.src = `https://ui-avatars.com/api/?name=${app.name}&background=1f2937&color=fff`;
                }}
              />
            </motion.div>
          ))}
        </div>

        <Link
          href="/integrations"
          className="text-primary hover:underline inline-flex items-center gap-1"
        >
          See all integrations <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </section>
  );
}
