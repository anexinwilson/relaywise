"""The worker must not import the agent at module scope.

Lambda caps the init phase at 10 seconds whatever the function timeout is.
LangChain, LangGraph and Composio together exceed that, and when init times out
Lambda throws the initialization away and repeats it inside the first
invocation, so the cost is paid twice:

    {"phase":"init","status":"timeout","durationMs":9999.088}

Importing lazily moves that work into the invoke phase, where no ceiling
applies. This test exists because the fix is one import line away from being
undone by someone tidying up.
"""

import ast
import pathlib

HANDLER = pathlib.Path(__file__).resolve().parent.parent / "src" / "worker" / "handler.py"

# Importing any of these at module scope drags in the whole agent stack.
HEAVY = ("agent.service", "composio", "langchain", "langgraph", "langchain_openai")


def _module_level_imports() -> set[str]:
    tree = ast.parse(HANDLER.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:  # module level only, not inside functions
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_agent_stack_is_not_imported_at_module_scope() -> None:
    at_module_level = _module_level_imports()
    offenders = [
        name
        for name in at_module_level
        if any(name == heavy or name.startswith(heavy + ".") for heavy in HEAVY)
    ]
    assert not offenders, (
        f"{offenders} imported at module scope in worker/handler.py. "
        "This runs during Lambda init, which is capped at 10s and will time out."
    )


def test_the_lazy_accessor_still_exists() -> None:
    """If this is gone, the import moved back to the top."""
    source = HANDLER.read_text(encoding="utf-8")
    assert "def _agent_service(" in source
    assert "from agent.service import get_agent_service" in source
