import { auth, currentUser } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { DashboardContent } from "./DashboardContent";

export default async function DashboardPage() {
  const { userId } = await auth();

  if (!userId) {
    redirect("/auth");
  }

  const user = await currentUser();
  
  const userData = user ? {
    firstName: user.firstName,
    emailAddresses: user.emailAddresses?.map(email => ({
      emailAddress: email.emailAddress
    }))
  } : null;

  return <DashboardContent user={userData} />;
}