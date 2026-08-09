from agent.intent import detect_personality_intent


def test_routes_unambiguous_conversation_without_model_call() -> None:
    assert detect_personality_intent("Hello, I'm Mira") == "greeting"
    assert detect_personality_intent("Who are you?") == "identity"
    assert detect_personality_intent("What is my name?") == "user_identity"
    assert detect_personality_intent("What apps do you support?") == "capabilities"


def test_leaves_action_requests_for_the_agent() -> None:
    assert detect_personality_intent("Hello, send the latest report to Slack") is None
    assert detect_personality_intent("Find my latest Gmail message") is None
