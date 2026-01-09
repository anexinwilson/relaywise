import { auth, currentUser } from "@clerk/nextjs/server";
import { SignedIn, SignedOut, UserButton, SignOutButton } from "@clerk/nextjs";
import Link from "next/link";

export default async function Home() {
  const { userId, getToken } = await auth();
  const user = userId ? await currentUser() : null;
  const token = userId ? await getToken() : null;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <h1 className="text-xl font-semibold">Cognive</h1>
            <div className="flex items-center gap-4">
              <SignedOut>
                <Link
                  href="/sign-in"
                  className="text-sm font-medium hover:underline"
                >
                  Sign In
                </Link>
                <Link
                  href="/sign-up"
                  className="px-4 py-2 text-sm font-medium bg-black text-white rounded hover:bg-gray-800"
                >
                  Sign Up
                </Link>
              </SignedOut>
              <SignedIn>
                <div className="flex items-center gap-4">
                  <UserButton />
                  <SignOutButton>
                    <button className="text-sm font-medium hover:underline">
                      Sign Out
                    </button>
                  </SignOutButton>
                </div>
              </SignedIn>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-12">
        <SignedOut>
          <div className="text-center space-y-6 py-16">
            <h2 className="text-3xl font-bold">Welcome</h2>
            <div className="flex gap-4 justify-center">
              <Link
                href="/sign-in"
                className="px-6 py-3 bg-black text-white rounded hover:bg-gray-800"
              >
                Sign In
              </Link>
              <Link
                href="/sign-up"
                className="px-6 py-3 border border-black rounded hover:bg-gray-50"
              >
                Sign Up
              </Link>
            </div>
          </div>
        </SignedOut>

        <SignedIn>
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-semibold mb-4">
                Welcome, {user?.firstName || user?.emailAddresses[0]?.emailAddress}
              </h2>
            </div>

            {token && (
              <div>
                <p className="text-sm text-gray-600 mb-2">Token:</p>
                <pre className="text-xs font-mono break-all">
                  {token}
                </pre>
              </div>
            )}
          </div>
        </SignedIn>
      </main>
    </div>
  );
}
