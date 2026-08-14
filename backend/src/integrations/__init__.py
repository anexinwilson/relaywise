"""Connected-app management, served to AppSync.

Runs from the worker image under a different entrypoint
(`integrations.handler.handler`) so the Composio SDK does not bloat the API
Lambda's cold start.

Nothing is re-exported here on purpose: binding `handler` at package level
would shadow the `integrations.handler` submodule of the same name, so
`from integrations import handler` would hand back the function rather than
the module.
"""
