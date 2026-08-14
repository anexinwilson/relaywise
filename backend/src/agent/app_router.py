"""Work out which app a request is about, before paying for tool discovery.

A tool-using turn costs roughly 11,000 tokens: the model is called several
times and each call re-sends the ~3,600-token Composio schema. Three kinds of
request can never succeed and should never reach it:

- the app the user named is not connected
- the request is about apps but names none, and several are connected
- nothing is connected at all (handled earlier, in the service)

Deciding which case applies is string matching over a known list, not
reasoning, so it costs nothing and cannot hallucinate an app that does not
exist. A model call here would add latency and tokens to answer a question a
dictionary already answers.

Deliberately conservative: anything it cannot resolve confidently falls through
to the normal agent path. A false "which app did you mean?" is annoying, so the
bar for interrupting is high.
"""

from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass
from enum import Enum

TOOLKITS_PATH = pathlib.Path(__file__).with_name("toolkits.json")

# Words people use for an app without naming it. Only unambiguous ones: "email"
# could be Gmail or Outlook, so it maps to both and stays ambiguous unless just
# one of them is connected.
ALIASES: dict[str, tuple[str, ...]] = {
    "gmail": ("gmail", "inbox", "email", "mail"),
    "outlook": ("outlook", "email", "mail"),
    "slack": ("slack",),
    "discord": ("discord",),
    "notion": ("notion",),
    "linear": ("linear",),
    "jira": ("jira",),
    "github": ("github", "repo", "pull request", "pr"),
    "googlecalendar": ("calendar", "google calendar", "gcal"),
    "googledrive": ("drive", "google drive"),
    "googledocs": ("google docs", "gdocs"),
    "googlesheets": ("sheets", "google sheets", "spreadsheet"),
    "trello": ("trello",),
    "asana": ("asana",),
    "hubspot": ("hubspot",),
    "airtable": ("airtable",),
    "todoist": ("todoist",),
    "clickup": ("clickup",),
    "telegram": ("telegram",),
    "whatsapp": ("whatsapp",),
    "twitter": ("twitter", "tweet"),
    "linkedin": ("linkedin",),
}

# Phrases that imply an app is involved but name none. Used only to decide
# whether silence is worth a clarifying question.
APP_SHAPED = (
    "message", "email", "inbox", "channel", "task", "issue", "ticket",
    "calendar", "event", "meeting", "document", "doc", "file", "page",
    "spreadsheet", "contact", "lead", "note", "reminder", "send", "post",
)


class Resolution(Enum):
    MATCHED = "matched"          # exactly one connected app fits
    NOT_CONNECTED = "not_connected"  # named an app they have not connected
    AMBIGUOUS = "ambiguous"      # app-shaped request, several apps, none named
    UNRESOLVED = "unresolved"    # no signal; let the agent decide


@dataclass(frozen=True)
class AppMatch:
    resolution: Resolution
    slug: str | None = None
    candidates: tuple[str, ...] = ()
    # True when the app was inferred from habit rather than stated or implied
    # by this conversation. The reply should say which app it used.
    assumed: bool = False


def _load_toolkits() -> dict[str, str]:
    try:
        data = json.loads(TOOLKITS_PATH.read_text(encoding="utf-8"))
        return {entry["slug"]: entry["name"] for entry in data}
    except Exception:
        # Resolution is an optimisation; without the catalog everything simply
        # falls through to the agent, which still works.
        return {}


TOOLKIT_NAMES = _load_toolkits()


def _normalise(message: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", message.lower())


def _mentions(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def slugs_mentioned(message: str) -> set[str]:
    """Every app the message plausibly names, by slug, alias, or display name."""
    text = _normalise(message)
    found: set[str] = set()

    for slug, aliases in ALIASES.items():
        if any(_mentions(text, alias) for alias in aliases):
            found.add(slug)

    for slug, name in TOOLKIT_NAMES.items():
        if _mentions(text, slug.replace("_", " ")) or _mentions(text, name.lower()):
            found.add(slug)

    return found


def looks_app_shaped(message: str) -> bool:
    """Does this read like a request about an app, without naming one?

    Matches simple plurals: people write "messages" as often as "message".
    """
    text = _normalise(message)
    return any(_mentions(text, word) or _mentions(text, word + "s") for word in APP_SHAPED)


def resolve(
    message: str,
    connected: list[str],
    recent_app: str | None = None,
    preferred_app: str | None = None,
) -> AppMatch:
    """Decide whether this request can proceed as-is.

    Signals, strongest first:

    1. an app named outright in the message
    2. `recent_app` — what *this* conversation has been about
    3. `preferred_app` — what this user reaches for most, across all chats

    Two and three are the difference between an assistant and an interrogation:

        "did john reply in discord?"   -> Discord, named
        "find the latest message"      -> Discord, same chat  (recent_app)
        ...new chat tomorrow...
        "find all latest messages"     -> Discord, their habit (preferred_app)

    Kept pure so every case stays exactly testable; all three values are looked
    up by the caller.
    """
    if not connected:
        # The service short-circuits before this; nothing sensible to say here.
        return AppMatch(Resolution.UNRESOLVED)

    mentioned = slugs_mentioned(message)
    connected_set = set(connected)

    usable = mentioned & connected_set
    if len(usable) == 1:
        return AppMatch(Resolution.MATCHED, slug=next(iter(usable)))
    if usable:
        # Several named and all connected — the agent can pick between them.
        return AppMatch(Resolution.UNRESOLVED)

    if mentioned:
        # Named something real, but it is not connected. Naming one is more
        # useful than listing several.
        return AppMatch(
            Resolution.NOT_CONNECTED,
            slug=sorted(mentioned)[0],
            candidates=tuple(sorted(mentioned)),
        )

    if len(connected) == 1:
        # Only one thing it could possibly mean; asking would be pedantic.
        return AppMatch(Resolution.MATCHED, slug=connected[0])

    if looks_app_shaped(message):
        # Carry the conversation's subject forward rather than asking the same
        # question every turn. Only if it is still connected — a disconnect
        # between turns must not silently keep routing there.
        if recent_app and recent_app in connected_set:
            return AppMatch(Resolution.MATCHED, slug=recent_app)

        # A new conversation has no subject yet, so fall back to habit. Flagged
        # as assumed so the reply can name the app it chose and stay
        # correctable — silently acting in the wrong app is worse than asking.
        if preferred_app and preferred_app in connected_set:
            return AppMatch(Resolution.MATCHED, slug=preferred_app, assumed=True)

        return AppMatch(Resolution.AMBIGUOUS, candidates=tuple(sorted(connected)))

    return AppMatch(Resolution.UNRESOLVED)


def display_name(slug: str) -> str:
    return TOOLKIT_NAMES.get(slug, slug.replace("_", " ").title())
