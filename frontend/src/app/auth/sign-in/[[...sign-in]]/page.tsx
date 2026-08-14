"use client";

import { SignIn } from "@clerk/nextjs";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Link href="/" className="flex items-center justify-center gap-2 mb-8">
          <Image
            src="/relaywise-logo.svg"
            alt="Relaywise"
            width={40}
            height={40}
            className="rounded-xl"
          />
          <span className="text-2xl font-bold text-foreground">Relaywise</span>
        </Link>

        <div className="bg-card border border-border rounded-2xl p-8">
          <SignIn
            appearance={{
              elements: {
                rootBox: "mx-auto w-full",
                card: "shadow-none border-0 bg-transparent p-0",
                headerTitle: "text-foreground text-2xl font-bold mb-2",
                headerSubtitle: "text-muted-foreground",
                socialButtonsBlockButton:
                  "border-border hover:bg-card bg-background text-foreground h-12",
                socialButtonsBlockButtonText: "text-foreground",
                formButtonPrimary: "gradient-primary hover:opacity-90 h-12",
                footerActionLink: "text-primary hover:text-primary/80",
                formFieldInput: "bg-background border-border text-foreground h-12",
                formFieldLabel: "text-foreground",
                dividerLine: "bg-border",
                // No background override: Clerk's card is light, and the app's
                // dark `bg-card` token painted a black box behind this label.
                dividerText: "text-muted-foreground",
              },
            }}
            routing="path"
            path="/auth/sign-in"
            signUpUrl="/auth/sign-up"
            fallbackRedirectUrl="/dashboard"
          />
        </div>
      </motion.div>
    </div>
  );
}
