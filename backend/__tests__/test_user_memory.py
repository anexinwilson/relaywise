from memory.extraction import _parse
from memory.user_memory import build_memory_block


# --- rendering --------------------------------------------------------------


def test_no_memories_injects_nothing() -> None:
    """An empty block must stay empty — never inject a header with no content."""
    assert build_memory_block([]) == ""


def test_facts_and_preferences_are_separated() -> None:
    # The LangGraph store hands back plain dicts, not ORM rows.
    block = build_memory_block(
        [
            {"kind": "fact", "content": "The user is a designer in Lisbon."},
            {"kind": "preference", "content": "The user prefers bullet points."},
        ]
    )

    assert block.startswith("[MEMORY]")
    assert block.endswith("[/MEMORY]\n")
    assert "Facts about the user:" in block
    assert "User preferences:" in block
    assert "- The user is a designer in Lisbon." in block


# --- extraction parsing -----------------------------------------------------


def test_parses_a_plain_array() -> None:
    raw = '[{"kind": "fact", "content": "The user lives in Berlin."}]'

    assert _parse(raw) == [("fact", "The user lives in Berlin.")]


def test_parses_through_a_code_fence() -> None:
    raw = '```json\n[{"kind": "preference", "content": "Prefers short replies."}]\n```'

    assert _parse(raw) == [("preference", "Prefers short replies.")]


def test_parses_when_the_model_adds_commentary() -> None:
    raw = 'Sure! Here you go:\n[{"kind":"fact","content":"The user uses Notion."}]\nHope that helps.'

    assert _parse(raw) == [("fact", "The user uses Notion.")]


def test_empty_array_means_nothing_worth_remembering() -> None:
    assert _parse("[]") == []


def test_unparseable_output_is_dropped_not_guessed() -> None:
    """A wrong memory persists and poisons every later conversation, so
    anything ambiguous is discarded."""
    assert _parse("I could not determine any facts.") == []
    assert _parse('[{"kind": "fact", ') == []


def test_unknown_kind_falls_back_to_fact() -> None:
    raw = '[{"kind": "wild-guess", "content": "The user codes in Python."}]'

    assert _parse(raw) == [("fact", "The user codes in Python.")]


def test_entries_without_content_are_skipped() -> None:
    raw = '[{"kind": "fact", "content": "  "}, {"kind": "fact", "content": "Real fact."}]'

    assert _parse(raw) == [("fact", "Real fact.")]


def test_extraction_is_capped() -> None:
    raw = "[" + ",".join(f'{{"kind":"fact","content":"Fact {i}."}}' for i in range(20)) + "]"

    assert len(_parse(raw)) == 5


def test_entries_without_content_are_ignored() -> None:
    assert build_memory_block([{"kind": "fact", "content": ""}]) == ""


def test_key_is_stable_across_wording_whitespace() -> None:
    """Restating a fact must hit the same key so the store deduplicates it."""
    from memory.user_memory import _key

    assert _key("The user lives in Berlin.") == _key("  the USER lives in Berlin.  ")
    assert _key("The user lives in Berlin.") != _key("The user lives in Lisbon.")


def test_namespace_scopes_by_user() -> None:
    from memory.user_memory import _namespace

    assert _namespace("user_1") == ("memories", "user_1")
    assert _namespace("user_1") != _namespace("user_2")
