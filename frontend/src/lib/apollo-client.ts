"use client";

import { ApolloClient, InMemoryCache, ApolloLink, HttpLink } from "@apollo/client/core";
import { setContext } from "@apollo/client/link/context";

const httpLink = new HttpLink({
  uri: "https://xnadxaee2bcsrhx6dido4yti2a.appsync-api.us-east-1.amazonaws.com/graphql",
  credentials: "include",
});

// Auth link to add Clerk JWT token
const authLink = setContext(async (_, { headers }) => {
  try {
    // Get token from Clerk
    const token = await (window as any).__clerk?.session?.getToken?.();
    
    return {
      headers: {
        ...headers,
        authorization: token ? `Bearer ${token}` : "",
      },
    };
  } catch (error) {
    console.error("Error getting auth token:", error);
    return { headers };
  }
});

export function createApolloClient() {
  return new ApolloClient({
    link: authLink.concat(httpLink),
    cache: new InMemoryCache(),
  });
}