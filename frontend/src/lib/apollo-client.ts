"use client";

import { ApolloClient, InMemoryCache, HttpLink, split } from "@apollo/client/core";
import { setContext } from "@apollo/client/link/context";
import { getMainDefinition } from "@apollo/client/utilities";
import { createSubscriptionHandshakeLink } from "aws-appsync-subscription-link";

// Match the working frontenda Apollo client: AppSync endpoint + Lambda auth via Clerk JWT
const httpLink = new HttpLink({
  uri:
    process.env.NEXT_PUBLIC_APPSYNC_ENDPOINT 
});

const createAuthLink = (getToken: () => Promise<string | null>) => {
  return setContext(async (_, { headers }) => {
    try {
      const token = await getToken();

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

const createAppSyncLink = () => {
  const apiKey = process.env.NEXT_PUBLIC_APPSYNC_API_KEY || "";
  const endpoint = process.env.NEXT_PUBLIC_APPSYNC_ENDPOINT || "";
  const region = "us-east-1";

  console.log('[Apollo] Subscription config:', {
    endpoint: endpoint.substring(0, 50) + '...',
    apiKeyPrefix: apiKey.substring(0, 10) + '...',
    region
  });

  const subscriptionLink = createSubscriptionHandshakeLink({
    url: endpoint,
    region,
    auth: {
      type: "API_KEY",
      apiKey,
    },
  });

  return subscriptionLink;
};

export function createApolloClient(getToken: () => Promise<string | null>) {
  const authLink = createAuthLink(getToken);
  const subscriptionLink = createAppSyncLink();

  const splitLink = split(
    ({ query }) => {
      const definition = getMainDefinition(query);
      return (
        definition.kind === "OperationDefinition" &&
        definition.operation === "subscription"
      );
    },
    subscriptionLink,
    authLink.concat(httpLink)
  );

  return new ApolloClient({
    link: splitLink,
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
