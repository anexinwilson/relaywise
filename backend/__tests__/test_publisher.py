"""The completion mutation's selection set is load-bearing.

AppSync delivers to a subscriber only the fields the mutation selected. A field
omitted here arrives as null however complete the payload was, and the browser
then has a finished task with nothing to display.
"""

import re

from worker import publisher

SUBSCRIBED_FIELDS = {
    "taskId",
    "userId",
    "status",
    "result",
    "error",
    "executionTime",
    "timestamp",
}


def _selection_set(mutation: str) -> set[str]:
    body = re.search(r"publishTaskComplete\(input: \$input\) \{(.*?)\}", mutation, re.S)
    assert body, "publishTaskComplete selection set not found"
    return set(body.group(1).split())


def test_mutation_selects_every_field_the_client_subscribes_to(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"publishTaskComplete": {}}}

    def fake_post(url, json, headers, timeout):
        captured["query"] = json["query"]
        return FakeResponse()

    monkeypatch.setattr(publisher.httpx, "post", fake_post)

    publisher.publish_completion(
        task_id="task-1",
        user_id="user-1",
        status="COMPLETED",
        result={"response": "done", "chatName": "a chat"},
    )

    assert _selection_set(captured["query"]) == SUBSCRIBED_FIELDS


def test_result_is_json_encoded_for_awsjson(monkeypatch) -> None:
    """AWSJSON variables must be JSON-encoded strings at the GraphQL boundary."""
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {}

    monkeypatch.setattr(
        publisher.httpx,
        "post",
        lambda url, json, headers, timeout: (captured.update(json), FakeResponse())[1],
    )

    publisher.publish_completion(
        task_id="task-1",
        user_id="user-1",
        status="COMPLETED",
        result={"response": "done"},
    )

    assert captured["variables"]["input"]["result"] == '{"response": "done"}'
