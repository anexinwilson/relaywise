"use client";

import { ApolloProvider as Provider } from "@apollo/client/react";
import { ReactNode } from "react";
import { createApolloClient } from "@/lib/apollo-client";

const client = createApolloClient();

export function ApolloProvider({ children }: { children: ReactNode }) {
  return <Provider client={client}>{children}</Provider>;
}