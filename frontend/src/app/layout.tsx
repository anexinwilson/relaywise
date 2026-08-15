import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { ApolloWrapper } from "@/components/ApolloWrapper";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Relaywise - Chat With Your Apps",
  description:
    "An AI agent that operates your connected apps. Ask a question or get something done across 860+ apps, in plain English.",
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
