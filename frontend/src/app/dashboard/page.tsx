import { auth, currentUser } from "@clerk/nextjs/server";
import { SignedIn, SignedOut, UserButton, SignOutButton } from "@clerk/nextjs";
import Link from "next/link";
import { redirect } from "next/navigation";

export default async function DashboardPage() {
  const { userId, getToken } = await auth();
  const user = userId ? await currentUser() : null;
  const token = userId ? await getToken() : null;

  if (!userId) {
    redirect("/auth");
  }

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
              Welcome, {user?.firstName || user?.emailAddresses[0]?.emailAddress}
            </h2>
          </div>

          {token && (
            <div>
              <p className="text-sm text-gray-600 mb-2">JWT Token:</p>
              <pre className="text-xs font-mono break-all bg-gray-50 p-3 rounded">
                {token}
              </pre>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
