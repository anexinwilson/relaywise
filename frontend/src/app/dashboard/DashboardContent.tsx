"use client";

import Link from "next/link";
import { UserButton, SignOutButton } from "@clerk/nextjs";

interface User {
  firstName?: string | null;
  emailAddresses?: Array<{ emailAddress: string }>;
}

export function DashboardContent({ user }: { user: User | null }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="text-xl font-semibold">
              Cognive
            </Link>
            <div className="flex items-center gap-4">
              <UserButton />
              <SignOutButton>
                <button className="text-sm font-medium hover:underline">
                  Sign Out
                </button>
              </SignOutButton>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-12">
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold mb-4">
              Welcome, {user?.firstName || user?.emailAddresses?.[0]?.emailAddress || "User"}
            </h2>
          </div>
        </div>
      </main>
    </div>
  );
}