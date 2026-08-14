"""Local development server.

Runs only the HTTP surface. The AppSync path has no local equivalent — exercise
it against the deployed API, or call `app.graphql.dispatch` directly from a test.

    uv run python main.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.application:app", host="0.0.0.0", port=8000, reload=True)
