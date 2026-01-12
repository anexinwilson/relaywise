"use client";

import { ApolloProvider as BaseApolloProvider } from "@apollo/client/react";
import { useAuth } from "@clerk/nextjs";
import { useMemo } from "react";
import { createApolloClient } from "@/lib/apollo-client";

export function ApolloProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();

  const client = useMemo(
    () => createApolloClient(() => getToken()),
    [getToken]
  );

  return <BaseApolloProvider client={client}>{children}</BaseApolloProvider>;
}