from app.services import task_queue


def test_title_drops_conversational_openers() -> None:
    """"see if i have any new messages" is a sentence, not a label."""
    assert task_queue.build_title("see if i have any new messages") == "Any new messages"


def test_title_peels_stacked_openers() -> None:
    assert task_queue.build_title("hey can you please check my inbox") == "Check my inbox"


def test_title_capitalises_without_flattening_the_rest() -> None:
    """Gmail must stay Gmail."""
    assert task_queue.build_title("summarise my Gmail threads").startswith("Summarise")
    assert "Gmail" in task_queue.build_title("summarise my Gmail threads")


def test_title_collapses_whitespace_and_trailing_punctuation() -> None:
    assert task_queue.build_title("  hello   there!!  ") == "There"


def test_title_falls_back_for_empty_message() -> None:
    assert task_queue.build_title("   ") == "New conversation"
    assert task_queue.build_title("please") == "New conversation"


def test_title_is_length_bounded() -> None:
    title = task_queue.build_title("word " * 200)
    assert len(title) <= task_queue.MAX_TITLE_CHARS
    assert len(title.split()) <= task_queue.MAX_TITLE_WORDS


def test_enqueue_uses_session_as_group_and_task_as_dedup(monkeypatch) -> None:
    """Ordering is per conversation; deduplication must not collapse two
    identical messages sent in the same chat."""
    sent = {}

    class FakeSqs:
        def send_message(self, **kwargs):
            sent.update(kwargs)

    monkeypatch.setattr(task_queue, "get_sqs", lambda: FakeSqs())

    task = task_queue.enqueue_task(
        user_id="user_123",
        session_id="session_abc",
        message="do the thing",
        chat_name="do the thing",
    )

    assert sent["MessageGroupId"] == "session_abc"
    assert sent["MessageDeduplicationId"] == task.task_id
    assert task.task_id != "session_abc"
