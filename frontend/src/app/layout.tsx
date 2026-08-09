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
  return (
    <ClerkProvider>
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
