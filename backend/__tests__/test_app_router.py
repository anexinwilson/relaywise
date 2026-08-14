"""Resolution decides whether a request is worth ~11k tokens of tool discovery.

The bar for interrupting the user is deliberately high: a wrong "which app did
you mean?" is worse than a slightly wasteful run, so anything unclear must fall
through to the agent rather than stopping to ask.
"""

from agent.app_router import Resolution, resolve, slugs_mentioned


def test_names_a_connected_app() -> None:
    match = resolve("find the latest message in slack", ["slack", "gmail"])

    assert match.resolution is Resolution.MATCHED
    assert match.slug == "slack"


def test_recognises_an_app_by_alias() -> None:
    """People say "inbox", not "gmail"."""
    match = resolve("summarise my inbox", ["gmail", "slack"])

    assert match.resolution is Resolution.MATCHED
    assert match.slug == "gmail"


def test_names_an_app_that_is_not_connected() -> None:
    match = resolve("send this to notion", ["slack"])

    assert match.resolution is Resolution.NOT_CONNECTED
    assert match.slug == "notion"


def test_ambiguous_when_several_connected_and_none_named() -> None:
    match = resolve("check the latest message", ["slack", "discord"])

    assert match.resolution is Resolution.AMBIGUOUS
    assert set(match.candidates) == {"slack", "discord"}


def test_single_connected_app_is_never_ambiguous() -> None:
    """With one app there is nothing to disambiguate; asking would be pedantic."""
    match = resolve("check the latest message", ["slack"])

    assert match.resolution is Resolution.MATCHED
    assert match.slug == "slack"


def test_non_app_requests_fall_through() -> None:
    """No app signal at all: let the agent decide rather than interrupting."""
    match = resolve("what is the weather like", ["slack", "gmail"])

    assert match.resolution is Resolution.UNRESOLVED


def test_several_named_and_connected_falls_through_to_the_agent() -> None:
    """The agent can pick between apps the user explicitly named."""
    match = resolve("copy the slack thread into notion", ["slack", "notion"])

    assert match.resolution is Resolution.UNRESOLVED


def test_no_connections_is_handled_elsewhere() -> None:
    assert resolve("check slack", []).resolution is Resolution.UNRESOLVED


def test_substrings_do_not_false_match() -> None:
    """Word boundaries matter: 'slacking off' is not a Slack request."""
    assert "slack" not in slugs_mentioned("I have been slacking off")


def test_matches_catalog_names_not_just_aliases() -> None:
    assert "airtable" in slugs_mentioned("add a row in Airtable")


def test_ambiguous_alias_stays_ambiguous_across_two_connected_apps() -> None:
    """"email" could be Gmail or Outlook; with both connected, ask."""
    match = resolve("check my email", ["gmail", "outlook"])

    assert match.resolution is Resolution.UNRESOLVED


def test_ambiguous_alias_resolves_when_only_one_is_connected() -> None:
    match = resolve("check my email", ["gmail", "slack"])

    assert match.resolution is Resolution.MATCHED
    assert match.slug == "gmail"


# --- conversational stickiness ----------------------------------------------


def test_follow_up_reuses_the_conversation_app() -> None:
    """The case that matters: "did john message me?" then "find the latest one".

    Without this the user is asked which app on every single turn.
    """
    match = resolve(
        "find the latest message",
        ["slack", "gmail", "discord", "notion"],
        recent_app="slack",
    )

    assert match.resolution is Resolution.MATCHED
    assert match.slug == "slack"


def test_an_explicitly_named_app_overrides_the_remembered_one() -> None:
    match = resolve("check my notion page", ["slack", "notion"], recent_app="slack")

    assert match.resolution is Resolution.MATCHED
    assert match.slug == "notion"


def test_a_disconnected_recent_app_is_not_reused() -> None:
    """Disconnecting between turns must stop routing there."""
    match = resolve("find the latest message", ["gmail", "discord"], recent_app="slack")

    assert match.resolution is Resolution.AMBIGUOUS


def test_still_asks_on_the_first_ambiguous_turn() -> None:
    match = resolve("find the latest message", ["slack", "gmail"], recent_app=None)

    assert match.resolution is Resolution.AMBIGUOUS


# --- habits across conversations --------------------------------------------


def test_a_new_chat_falls_back_to_the_users_habit() -> None:
    """The point of memory: a fresh conversation should not start from zero.

    "did john reply in discord?" yesterday, then a new chat today asking
    "find all latest messages" — Discord, without asking again.
    """
    match = resolve(
        "find all the latest messages",
        ["slack", "discord", "gmail"],
        recent_app=None,
        preferred_app="discord",
    )

    assert match.resolution is Resolution.MATCHED
    assert match.slug == "discord"
    assert match.assumed is True


def test_this_conversation_beats_the_habit() -> None:
    """What the chat is about now outranks what the user usually does."""
    match = resolve(
        "find the latest message",
        ["slack", "discord"],
        recent_app="slack",
        preferred_app="discord",
    )

    assert match.slug == "slack"
    assert match.assumed is False


def test_naming_an_app_beats_everything() -> None:
    match = resolve(
        "check discord for that",
        ["slack", "discord"],
        recent_app="slack",
        preferred_app="slack",
    )

    assert match.slug == "discord"
    assert match.assumed is False


def test_a_disconnected_habit_is_ignored() -> None:
    match = resolve(
        "find the latest message",
        ["gmail", "slack"],
        preferred_app="discord",
    )

    assert match.resolution is Resolution.AMBIGUOUS


def test_no_history_still_asks() -> None:
    match = resolve("find the latest message", ["slack", "gmail"])

    assert match.resolution is Resolution.AMBIGUOUS


def test_an_assumed_app_is_flagged_so_the_reply_can_say_so() -> None:
    """Acting silently in the wrong app is worse than a one-line disclosure."""
    assumed = resolve("send a message", ["slack", "gmail"], preferred_app="slack")
    explicit = resolve("send a slack message", ["slack", "gmail"])

    assert assumed.assumed is True
    assert explicit.assumed is False
