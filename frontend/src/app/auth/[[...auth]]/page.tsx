"use client";

import { SignIn } from "@clerk/nextjs";
import { motion } from "framer-motion";
import Link from "next/link";
import { Zap } from "lucide-react";

export default function AuthPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-2xl font-bold text-foreground">Cognive</span>
        </Link>

        {/* Clerk Sign In */}
        <div className="bg-card border border-border rounded-2xl p-8">
          <SignIn
            appearance={{
              elements: {
                rootBox: "mx-auto w-full",
                card: "shadow-none border-0 bg-transparent p-0",
                headerTitle: "text-foreground text-2xl font-bold mb-2",
                headerSubtitle: "text-muted-foreground",
                socialButtonsBlockButton: "border-border hover:bg-card bg-background text-foreground h-12",
                socialButtonsBlockButtonText: "text-foreground",
                formButtonPrimary: "gradient-primary hover:opacity-90 h-12",
                footerActionLink: "text-primary hover:text-primary/80",
                formFieldInput: "bg-background border-border text-foreground h-12",
                formFieldLabel: "text-foreground",
                dividerLine: "bg-border",
                dividerText: "text-muted-foreground bg-card",
              },
            }}
            routing="path"
            path="/auth"
            signUpUrl="/auth"
            afterSignInUrl="/dashboard"
            afterSignUpUrl="/dashboard"
          />
        </div>
      </motion.div>
    </div>
  );
}
