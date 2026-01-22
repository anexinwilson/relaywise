"use client";

import { ApolloClient, InMemoryCache, ApolloLink, HttpLink } from "@apollo/client/core";

const httpLink = new HttpLink({
  uri: process.env.NEXT_PUBLIC_API_URL,
  credentials: "include",
});

export function createApolloClient() {
  return new ApolloClient({
    link: httpLink,
    cache: new InMemoryCache(),
  });
}