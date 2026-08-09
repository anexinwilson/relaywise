import "@apollo/client";

declare module "@apollo/client" {
  interface TypeOverrides {
    signatureStyle: "classic";
  }

  namespace ApolloClient {
    namespace DeclareDefaultOptions {
      interface WatchQuery {
        errorPolicy: "all";
      }

      interface Query {
        errorPolicy: "all";
      }
    }
  }
}
