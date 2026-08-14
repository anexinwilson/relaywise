"use client";

import { ApolloProvider } from "@apollo/client/react";
import { ReactNode, useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { createApolloClient } from "@/lib/apollo-client";

export function ApolloWrapper({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();

  const client = useMemo(() => {
    return createApolloClient(async () => {
      try {
        return await getToken();
      } catch (error) {
        console.error("Error getting token:", error);
        return null;
      }
    });
  }, [getToken]);

  return <ApolloProvider client={client}>{children}</ApolloProvider>;
}
