import { auth, currentUser } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { DashboardChat } from "./DashboardChat";

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

  return <DashboardChat user={userData} />;
}