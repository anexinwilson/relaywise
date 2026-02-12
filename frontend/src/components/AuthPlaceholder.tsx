import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function AuthPlaceholder({ type }: { type: "sign-in" | "sign-up" }) {
  const isSignIn = type === "sign-in";

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-2xl p-8 max-w-md w-full text-center">
        <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mx-auto mb-6">
          <span className="text-white font-bold text-3xl">C</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-4">
          {isSignIn ? "Sign In" : "Create Account"}
        </h1>
        <p className="text-muted-foreground mb-6">
          {isSignIn
            ? "Welcome back! Sign in to access your dashboard."
            : "Get started with Cognive for free."}
        </p>

        <div className="space-y-4 mb-6">
          <div className="bg-primary/10 text-primary rounded-lg p-4 text-sm">
            <strong>Clerk Authentication Required</strong>
            <p className="mt-1 text-muted-foreground">
              To enable authentication, add your Clerk publishable key to the
              .env.local file.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <Link href="/dashboard">
            <Button className="w-full gradient-primary hover:opacity-90">
              Continue to Demo Dashboard
            </Button>
          </Link>
          <Link href="/">
            <Button variant="ghost" className="w-full">
              Back to Home
            </Button>
          </Link>
        </div>

        <p className="text-xs text-muted-foreground mt-6">
          {isSignIn ? (
            <>
              Don&apos;t have an account?{" "}
              <Link href="/auth/sign-up" className="text-primary hover:underline">
                Sign up
              </Link>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <Link href="/auth/sign-in" className="text-primary hover:underline">
                Sign in
              </Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
