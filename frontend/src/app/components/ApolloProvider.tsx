"use client";

import { ApolloProvider as Provider } from "@apollo/client/react";
import { ReactNode, useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { createApolloClient } from "@/lib/apollo-client";

export function ApolloProvider({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  
  const client = useMemo(() => {
    return createApolloClient(async () => {
      try {
        const token = await getToken();
        return token;
      } catch (error) {
        console.error('Error getting token:', error);
        return null;
      }
    });
  }, [getToken]);

  return <Provider client={client}>{children}</Provider>;
}