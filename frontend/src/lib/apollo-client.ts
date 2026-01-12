"use client";

import { ApolloClient, InMemoryCache, ApolloLink, HttpLink } from "@apollo/client/core";
import { setContext } from "@apollo/client/link/context";

const httpLink = new HttpLink({
  uri: process.env.NEXT_PUBLIC_API_URL,
});

export function createApolloClient(getToken: () => Promise<string | null>) {
  const authLink = setContext(async (_, { headers }) => {
    const token = await getToken();
    
    return {
      headers: {
        ...headers,
        authorization: token ? `Bearer ${token}` : "",
      },
    };
  });

  return new ApolloClient({
    link: ApolloLink.from([authLink, httpLink]),
    cache: new InMemoryCache(),
  });
}