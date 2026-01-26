"use client";

import { ApolloClient, InMemoryCache, ApolloLink, HttpLink } from "@apollo/client/core";
import { setContext } from "@apollo/client/link/context";

const httpLink = new HttpLink({
  uri: process.env.NEXT_PUBLIC_APPSYNC_ENDPOINT || "https://bszu7pupljfg5hnlbfch6ccmfi.appsync-api.us-east-1.amazonaws.com/graphql",
  // Remove credentials: "include" line - it's not needed for JWT auth
});

// Auth link that receives the token as a parameter
const createAuthLink = (getToken: () => Promise<string | null>) => {
  return setContext(async (_, { headers }) => {
    try {
      const token = await getToken();
      
      console.log('=== Apollo Auth Link ===');
      console.log('Token obtained:', !!token);
      console.log('Token preview:', token ? token.substring(0, 50) + '...' : 'none');
      
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
};

export function createApolloClient(getToken: () => Promise<string | null>) {
  const authLink = createAuthLink(getToken);
  
  return new ApolloClient({
    link: authLink.concat(httpLink),
    cache: new InMemoryCache(),
    defaultOptions: {
      watchQuery: {
        errorPolicy: "all",
      },
      query: {
        errorPolicy: "all",
      },
    },
  });
}