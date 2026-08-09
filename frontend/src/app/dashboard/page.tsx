import { auth, currentUser } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { DashboardClient } from "./DashboardClient";

export default async function DashboardPage() {
  const { userId } = await auth();

  if (!userId) {
    redirect("/auth/sign-in");
  }

  const user = await currentUser();
  const userData = user ? {
    firstName: user.firstName,
    emailAddresses: user.emailAddresses?.map(email => ({
      emailAddress: email.emailAddress
    })),
    imageUrl: user.imageUrl
  } : null;

  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
      </div>
    }>
      <DashboardClient user={userData} />
    </Suspense>
  );
}
