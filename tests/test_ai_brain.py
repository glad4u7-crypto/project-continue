"""Phase 11 AI Brain integration and safety tests."""
import json
from types import SimpleNamespace

import pytest

from services.ai_brain import (
    AIConfigurationError, AIResponseError, AISettings, AIResponseParser,
    HumanApprovalGate, MockAIProvider, OpenAICompatibleProvider,
    ProjectContextBuilder, InstructionGenerator,
)


class Repo:
    def get_project(self, pid):
        return {"id": pid, "name": "Demo", "description": "Plan", "status": "active"}
    def list_tasks(self, pid):
        return [{"id": "t1", "title": "Build", "description": "Implement feature",
                 "status": "todo", "priority": "high", "due_at": None, "assignee": None}]


def test_ai_configuration_defaults_to_disabled_mock():
    settings = AISettings.from_env({})
    assert settings.provider == "mock" and not settings.enabled and not settings.api_key


def test_remote_ai_requires_https_and_key():
    with pytest.raises(AIConfigurationError):
        AISettings.from_env({"AI_ENABLED": "true", "AI_PROVIDER": "openai_compatible",
                             "AI_BASE_URL": "http://example.com", "AI_API_KEY": "secret"})


def test_remote_provider_uses_timeout_and_returns_content():
    settings = AISettings.from_env({"AI_ENABLED": "true", "AI_PROVIDER": "openai_compatible",
                                    "AI_BASE_URL": "https://api.example.com", "AI_API_KEY": "secret"})
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": '{"summary":"ok","suggested_action":"review","task_id":null,"reason":"check","confidence":0.8}'}}]}
    class Session:
        def post(self, *args, **kwargs):
            assert kwargs["timeout"] == 20
            assert kwargs["headers"]["Authorization"] == "Bearer secret"
            return Response()
    assert "summary" in OpenAICompatibleProvider(settings, Session()).generate(system_prompt="s", user_prompt="u")


def test_context_builder_is_project_scoped_and_bounded():
    context = ProjectContextBuilder(Repo(), 1000).build("p1")
    assert context["project"]["id"] == "p1"
    assert context["tasks"][0]["id"] == "t1"
    assert "api_key" not in json.dumps(context).lower()


def test_context_builder_missing_project():
    class Missing(Repo):
        def get_project(self, pid): return None
    with pytest.raises(KeyError):
        ProjectContextBuilder(Missing()).build("missing")


def test_instruction_generator_marks_context_as_untrusted():
    system, user = InstructionGenerator().generate({"project": {"name": "x"}})
    assert "untrusted" in system and "read-only" in user


@pytest.mark.parametrize("action", ["start", "continue", "unblock", "review"])
def test_parser_accepts_only_allowed_actions(action):
    raw = json.dumps({"summary":"Next step","suggested_action":action,"task_id":"t1",
                      "reason":"Ready","confidence":0.9})
    assert AIResponseParser().parse(raw)["suggested_action"] == action


@pytest.mark.parametrize("raw", [
    "not json", "[]",
    '{"summary":"x","suggested_action":"delete","task_id":null,"reason":"x","confidence":1}',
    '{"summary":"x","suggested_action":"review","task_id":null,"reason":"x","confidence":2}',
    '{"summary":"x","suggested_action":"review","task_id":null,"reason":"x","confidence":1,"tool":"shell"}',
])
def test_parser_rejects_invalid_or_unsafe_payloads(raw):
    with pytest.raises(AIResponseError):
        AIResponseParser().parse(raw)


def test_approval_is_explicit_one_time_and_non_executing():
    gate = HumanApprovalGate()
    suggestion = {"suggested_action":"review","summary":"Check","reason":"Safe","task_id":None,"confidence":0.5}
    request = gate.submit("p1", suggestion)
    assert request.status == "pending"
    approved = gate.decide(request.request_id, approved=True)
    assert approved.status == "approved"
    with pytest.raises(ValueError):
        gate.decide(request.request_id, approved=False)


def test_rejected_approval_is_recorded():
    gate = HumanApprovalGate()
    req = gate.submit("p1", {"suggested_action":"start"})
    assert gate.decide(req.request_id, approved=False).status == "rejected"


def test_mock_provider_returns_parseable_advisory():
    parsed = AIResponseParser().parse(MockAIProvider().generate(system_prompt="", user_prompt=""))
    assert parsed["suggested_action"] == "review"
