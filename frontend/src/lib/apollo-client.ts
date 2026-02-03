"use client";

import { ApolloClient, InMemoryCache, HttpLink, split } from "@apollo/client/core";
import { setContext } from "@apollo/client/link/context";
import { getMainDefinition } from '@apollo/client/utilities';
import { createSubscriptionHandshakeLink } from 'aws-appsync-subscription-link';

const httpLink = new HttpLink({
  uri: process.env.NEXT_PUBLIC_APPSYNC_ENDPOINT || "https://bszu7pupljfg5hnlbfch6ccmfi.appsync-api.us-east-1.amazonaws.com/graphql",
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
  const apiKey = process.env.NEXT_PUBLIC_APPSYNC_API_KEY || '';
  const endpoint = process.env.NEXT_PUBLIC_APPSYNC_ENDPOINT || '';
  
  const region = 'us-east-1';

  const subscriptionLink = createSubscriptionHandshakeLink({
    url: endpoint,
    region: region,
    auth: {
      type: 'API_KEY',
      apiKey: apiKey,
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
      return definition.kind === 'OperationDefinition' && definition.operation === 'subscription';
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
