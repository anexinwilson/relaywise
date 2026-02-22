import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { ApolloWrapper } from "@/components/ApolloWrapper";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cognive - Chat With Your Apps. Automate Anything.",
  description:
    "MCP-powered. 500+ integrations. Ask anything, do anything. Automate it all — in plain English.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

  // If no valid Clerk key, render without Clerk provider (for local dev)
  if (!publishableKey || publishableKey.startsWith("pk_test_placeholder")) {
    return (
      <html lang="en" className="dark">
        <body className="antialiased" suppressHydrationWarning>
          <ApolloWrapper>
            {children}
            <Toaster />
          </ApolloWrapper>
        </body>
      </html>
    );
  }

  return (
    <ClerkProvider publishableKey={publishableKey}>
      <html lang="en" className="dark">
        <body className="antialiased" suppressHydrationWarning>
          <ApolloWrapper>
            {children}
            <Toaster />
          </ApolloWrapper>
        </body>
      </html>
    </ClerkProvider>
  );
}
