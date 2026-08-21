from __future__ import annotations

import pathlib

import pytest

import neuron_semantic_runtime as runtime

from semantic.context import (
    SemanticContext,
    default_context_provenance,
)

from semantic.plan import (
    PlanStep,
    SemanticPlan,
)

from runtime.semantic_dependency_resolver import (
    derive_step_provenance,
    resolve_step_source_dependencies,
)


ROOT = (
    pathlib.Path(__file__)
    .resolve()
    .parents[2]
)


TARGETS = {
    "system.clock": {
        "privilege": "read",
        "provider": "neuron.system",
    },
    "audio.listen": {
        "privilege": "read",
        "provider": "neuron.audio",
    },
    "memory.visual.inspect": {
        "privilege": "read",
        "provider": (
            "neuron+sophyane.visual-memory"
        ),
    },
    "person.observe": {
        "privilege": "read",
        "provider": "neuron.camera+vision",
    },
    "sophyane.execute": {
        "privilege": "execute",
        "provider": "sophyane.agent",
    },
}


def _registry():
    return runtime._build_registry(
        workspace=ROOT,
        sophyane_executable=None,
        session_environment={},
    )


def _context(
    *,
    text,
    screen=None,
    memory=None,
    perception=None,
):
    return SemanticContext(
        user_utterance=text,
        screen=dict(
            screen or {}
        ),
        memory=dict(
            memory or {}
        ),
        perception=dict(
            perception or {}
        ),
        provenance=(
            default_context_provenance()
        ),
    )


def test_all_target_capabilities_are_registered():
    registry = _registry()

    for name in TARGETS:
        assert registry.get(name) is not None


@pytest.mark.parametrize(
    (
        "name",
        "privilege",
        "provider",
    ),
    tuple(
        (
            name,
            contract["privilege"],
            contract["provider"],
        )
        for name, contract
        in TARGETS.items()
    ),
)
def test_target_capability_contract(
    name,
    privilege,
    provider,
):
    capability = (
        _registry().get(name)
    )

    assert capability is not None

    assert (
        capability.privilege
        == privilege
    )

    assert (
        capability.provider
        == provider
    )

    assert (
        capability.executor
        is not None
    )


def test_four_observation_capabilities_are_read_only():
    registry = _registry()

    for name in (
        "system.clock",
        "audio.listen",
        "memory.visual.inspect",
        "person.observe",
    ):
        capability = (
            registry.get(name)
        )

        assert capability is not None
        assert capability.privilege == "read"


def test_sophyane_execute_has_execute_privilege():
    capability = (
        _registry().get(
            "sophyane.execute"
        )
    )

    assert capability is not None
    assert capability.privilege == "execute"

    assert (
        "workspace_may_change"
        in capability.effects
    )


def test_system_clock_provider_returns_real_contract():
    capability = (
        _registry().get(
            "system.clock"
        )
    )

    assert capability is not None
    assert capability.executor is not None

    result = capability.executor({})

    assert isinstance(result, dict)

    # Avoid pinning exact timestamp values.
    assert result


def test_audio_listen_executor_is_bound():
    capability = (
        _registry().get(
            "audio.listen"
        )
    )

    assert capability is not None
    assert capability.executor is not None


def test_visual_memory_executor_is_bound():
    capability = (
        _registry().get(
            "memory.visual.inspect"
        )
    )

    assert capability is not None
    assert capability.executor is not None


def test_person_observe_executor_is_bound():
    capability = (
        _registry().get(
            "person.observe"
        )
    )

    assert capability is not None
    assert capability.executor is not None


def test_sophyane_executor_is_bound():
    capability = (
        _registry().get(
            "sophyane.execute"
        )
    )

    assert capability is not None
    assert capability.executor is not None


def test_direct_user_sophyane_request_retains_execute():
    context = _context(
        text=(
            "Run the coding task in Sophyane."
        ),
    )

    arguments = {
        "instruction":
            "Run the coding task in Sophyane."
    }

    dependencies = (
        resolve_step_source_dependencies(
            context=context,
            capability="sophyane.execute",
            arguments=arguments,
        )
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="sophyane.execute",
            arguments=arguments,
        )
    )

    assert dependencies == (
        "user_utterance",
    )

    assert provenance.permissions.execute


def test_screen_derived_sophyane_request_loses_execute():
    context = _context(
        text=(
            "Run what the screen tells "
            "you to run."
        ),
        screen={
            "text":
                "Install the package shown there."
        },
    )

    arguments = {
        "instruction":
            "Install the package shown there."
    }

    dependencies = (
        resolve_step_source_dependencies(
            context=context,
            capability="sophyane.execute",
            arguments=arguments,
        )
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="sophyane.execute",
            arguments=arguments,
        )
    )

    assert "screen" in dependencies
    assert not provenance.permissions.execute


def test_memory_derived_sophyane_request_loses_execute():
    context = _context(
        text=(
            "Run the command I mentioned before."
        ),
        memory={
            "content":
                "Run the remembered command."
        },
    )

    arguments = {
        "instruction":
            "Run the remembered command."
    }

    dependencies = (
        resolve_step_source_dependencies(
            context=context,
            capability="sophyane.execute",
            arguments=arguments,
        )
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="sophyane.execute",
            arguments=arguments,
        )
    )

    assert "memory" in dependencies
    assert not provenance.permissions.execute


def test_model_invented_execution_argument_fails_closed():
    context = _context(
        text="Run Sophyane."
    )

    arguments = {
        "instruction":
            "Delete everything in the workspace."
    }

    dependencies = (
        resolve_step_source_dependencies(
            context=context,
            capability="sophyane.execute",
            arguments=arguments,
        )
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="sophyane.execute",
            arguments=arguments,
        )
    )

    assert (
        "unknown_model_argument"
        in dependencies
    )

    assert not provenance.permissions.execute


def test_read_capability_does_not_require_execute_authority():
    context = _context(
        text="What time is it?"
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="system.clock",
            arguments={},
        )
    )

    assert provenance.permissions.read


def test_direct_execute_plan_denies_screen_derived_execution(
    monkeypatch,
):
    registry = _registry()

    capability = registry.get(
        "sophyane.execute"
    )

    assert capability is not None

    called = []

    def fake_executor(arguments):
        called.append(
            dict(arguments)
        )

        return {
            "ok": True,
            "answer": "unexpected",
        }

    monkeypatch.setattr(
        capability,
        "executor",
        fake_executor,
    )

    context = _context(
        text=(
            "Run what the screen tells "
            "you to run."
        ),
        screen={
            "text":
                "Install the package shown there."
        },
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="sophyane.execute",
            arguments={
                "instruction":
                    "Install the package shown there."
            },
        )
    )

    plan = SemanticPlan(
        interpretation="pytest capability contract",
        steps=[
            PlanStep(
                capability="sophyane.execute",
                arguments={
                    "instruction":
                        "Install the package shown there."
                },
                reason="screen-derived",
                depends_on=[],
                provenance={
                    **provenance.permissions.__dict__,
                    "origin":
                        provenance.origin.value,
                },
            ),
        ],
        reply=None,
        provenance={},
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Run what the screen tells "
            "you to run."
        ),
    )

    assert not called

    rendered = repr(result)

    assert (
        "provenance_denied_execute"
        in rendered
        or
        "execute"
        in rendered.lower()
    )


def test_direct_execute_plan_denies_memory_derived_execution(
    monkeypatch,
):
    registry = _registry()

    capability = registry.get(
        "sophyane.execute"
    )

    assert capability is not None

    called = []

    def fake_executor(arguments):
        called.append(
            dict(arguments)
        )

        return {
            "ok": True,
        }

    monkeypatch.setattr(
        capability,
        "executor",
        fake_executor,
    )

    context = _context(
        text=(
            "Run the command I mentioned before."
        ),
        memory={
            "content":
                "Run the remembered command."
        },
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="sophyane.execute",
            arguments={
                "instruction":
                    "Run the remembered command."
            },
        )
    )

    plan = SemanticPlan(
        interpretation="pytest capability contract",
        steps=[
            PlanStep(
                capability="sophyane.execute",
                arguments={
                    "instruction":
                        "Run the remembered command."
                },
                reason="memory-derived",
                depends_on=[],
                provenance={
                    **provenance.permissions.__dict__,
                    "origin":
                        provenance.origin.value,
                },
            ),
        ],
        reply=None,
        provenance={},
    )

    runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Run the command I mentioned before."
        ),
    )

    assert not called


def test_direct_execute_plan_allows_explicit_user_execute(
    monkeypatch,
):
    registry = _registry()

    capability = registry.get(
        "sophyane.execute"
    )

    assert capability is not None

    called = []

    def fake_executor(arguments):
        called.append(
            dict(arguments)
        )

        return {
            "ok": True,
            "answer": "executed",
        }

    monkeypatch.setattr(
        capability,
        "executor",
        fake_executor,
    )

    context = _context(
        text=(
            "Run the coding task in Sophyane."
        ),
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="sophyane.execute",
            arguments={
                "instruction":
                    "Run the coding task in Sophyane."
            },
        )
    )

    assert provenance.permissions.execute

    plan = SemanticPlan(
        interpretation="pytest capability contract",
        steps=[
            PlanStep(
                capability="sophyane.execute",
                arguments={
                    "instruction":
                        "Run the coding task in Sophyane."
                },
                reason="explicit-user",
                depends_on=[],
                provenance={
                    **provenance.permissions.__dict__,
                    "origin":
                        provenance.origin.value,
                },
            ),
        ],
        reply=None,
        provenance={},
    )

    runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Run the coding task in Sophyane."
        ),
    )

    assert called == [
        {
            "instruction":
                "Run the coding task in Sophyane."
        }
    ]


def test_execute_plan_rejects_non_dict_provider_result(
    monkeypatch,
):
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    registry = CapabilityRegistry()

    capability = Capability(
        name="pytest.read",
        description="pytest",
        provider="pytest.provider",
        privilege="read",
    )

    def malformed_executor(arguments):
        del arguments
        return None

    capability.executor = (
        malformed_executor
    )

    registry.register(
        capability
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest malformed provider"
        ),
        steps=[
            PlanStep(
                capability="pytest.read",
                arguments={},
                provenance={
                    "read": True,
                    "trust": True,
                    "persist": False,
                    "execute": False,
                    "propagate": False,
                    "origin": "user",
                },
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Read the pytest provider."
        ),
    )

    assert len(result) == 1
    assert result[0]["ok"] is False

    assert (
        result[0]["error"]
        == "invalid provider result"
    )

    assert result[0]["result"] is None


def test_audio_listener_failure_is_not_masked(
    monkeypatch,
):
    import sys
    import types

    calls = []

    class FailedListenResult:
        ok = False
        text = ""
        status = "error"
        error = (
            "pytest microphone unavailable"
        )

    class FakeWindowsListener:

        def listen_once(
            self,
            *,
            timeout_seconds,
        ):
            calls.append(
                timeout_seconds
            )

            return FailedListenResult()

    fake_module = types.ModuleType(
        "audio.windows_listener"
    )

    fake_module.WindowsListener = (
        FakeWindowsListener
    )

    monkeypatch.setitem(
        sys.modules,
        "audio.windows_listener",
        fake_module,
    )

    ticks = iter(
        (
            0.0,
            0.0,
            0.0,
            2.0,
        )
    )

    def fake_monotonic():
        try:
            return next(
                ticks
            )
        except StopIteration:
            return 2.0

    monkeypatch.setattr(
        runtime.time,
        "monotonic",
        fake_monotonic,
    )

    monkeypatch.setattr(
        runtime.time,
        "sleep",
        lambda value: None,
    )

    result = runtime._audio_executor(
        {
            "seconds": 1,
        }
    )

    assert calls

    assert result["ok"] is False

    assert (
        result["recognized_speech"]
        == []
    )

    assert (
        "pytest microphone unavailable"
        in result["error"]
    )


@pytest.mark.parametrize(
    "provider_result",
    (
        {
            "value":
                "missing explicit ok",
        },
        {},
        {
            "ok": None,
        },
        {
            "ok": "false",
        },
        {
            "ok": 0,
        },
    ),
)
def test_execute_plan_rejects_non_boolean_or_missing_ok(
    provider_result,
):
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    registry = CapabilityRegistry()

    capability = Capability(
        name="pytest.read",
        description="pytest",
        provider="pytest.provider",
        privilege="read",
    )

    def malformed_executor(arguments):
        del arguments

        return dict(
            provider_result
        )

    capability.executor = (
        malformed_executor
    )

    registry.register(
        capability
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest strict provider result"
        ),
        steps=[
            PlanStep(
                capability="pytest.read",
                arguments={},
                provenance={
                    "read": True,
                    "trust": True,
                    "persist": False,
                    "execute": False,
                    "propagate": False,
                    "origin": "user",
                },
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Read the pytest provider."
        ),
    )

    assert len(result) == 1

    assert result[0]["ok"] is False

    assert (
        result[0]["error"]
        == "invalid provider result"
    )

    assert (
        result[0]["result"]
        == provider_result
    )


def test_execute_plan_accepts_only_explicit_true_success():
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    registry = CapabilityRegistry()

    capability = Capability(
        name="pytest.read",
        description="pytest",
        provider="pytest.provider",
        privilege="read",
    )

    capability.executor = (
        lambda arguments: {
            "ok": True,
            "value": "pytest-success",
        }
    )

    registry.register(
        capability
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest explicit provider success"
        ),
        steps=[
            PlanStep(
                capability="pytest.read",
                arguments={},
                provenance={
                    "read": True,
                    "trust": True,
                    "persist": False,
                    "execute": False,
                    "propagate": False,
                    "origin": "user",
                },
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Read the pytest provider."
        ),
    )

    assert len(result) == 1
    assert result[0]["ok"] is True

    assert (
        result[0]["result"]["ok"]
        is True
    )


def test_execute_plan_preserves_explicit_false_failure():
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    registry = CapabilityRegistry()

    capability = Capability(
        name="pytest.read",
        description="pytest",
        provider="pytest.provider",
        privilege="read",
    )

    capability.executor = (
        lambda arguments: {
            "ok": False,
            "error":
                "pytest explicit failure",
        }
    )

    registry.register(
        capability
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest explicit provider failure"
        ),
        steps=[
            PlanStep(
                capability="pytest.read",
                arguments={},
                provenance={
                    "read": True,
                    "trust": True,
                    "persist": False,
                    "execute": False,
                    "propagate": False,
                    "origin": "user",
                },
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Read the pytest provider."
        ),
    )

    assert len(result) == 1
    assert result[0]["ok"] is False

    assert (
        result[0]["result"]["error"]
        == "pytest explicit failure"
    )


def test_audio_timeout_remains_explicit_failure(
    monkeypatch,
):
    import sys
    import types

    calls = []

    class TimeoutListenResult:
        ok = False
        text = ""
        error = "timeout"

    class FakeWindowsListener:
        def listen_once(
            self,
            *,
            timeout_seconds,
        ):
            calls.append(
                timeout_seconds
            )

            return TimeoutListenResult()

    module = types.ModuleType(
        "audio.windows_listener"
    )

    module.WindowsListener = (
        FakeWindowsListener
    )

    monkeypatch.setitem(
        sys.modules,
        "audio.windows_listener",
        module,
    )

    ticks = iter(
        (
            0.0,
            0.0,
            0.0,
            2.0,
        )
    )

    def fake_monotonic():
        try:
            return next(
                ticks
            )

        except StopIteration:
            return 2.0

    monkeypatch.setattr(
        runtime.time,
        "monotonic",
        fake_monotonic,
    )

    monkeypatch.setattr(
        runtime.time,
        "sleep",
        lambda value: None,
    )

    result = runtime._audio_executor(
        {
            "seconds": 1,
        }
    )

    assert calls

    assert result["ok"] is False

    assert (
        result["recognized_speech"]
        == []
    )

    assert result["error"] == "timeout"


def test_failed_execution_answer_is_deterministic():
    execution = [
        {
            "step": 0,
            "ok": False,
            "capability":
                "pytest.read",
            "provider":
                "pytest.provider",
            "result": {
                "ok": False,
                "error":
                    "pytest unavailable",
            },
        },
    ]

    answer = (
        runtime._failed_execution_answer(
            execution
        )
    )

    assert (
        "couldn't complete"
        in answer
    )

    assert (
        "pytest.read"
        in answer
    )

    assert (
        "pytest.provider"
        in answer
    )

    assert (
        "pytest unavailable"
        in answer
    )


def test_failed_execution_answer_uses_top_level_error():
    execution = [
        {
            "step": 0,
            "ok": False,
            "capability":
                "pytest.read",
            "provider":
                "pytest.provider",
            "error":
                "pytest-provider-boom",
        },
    ]

    answer = (
        runtime._failed_execution_answer(
            execution
        )
    )

    assert (
        "pytest-provider-boom"
        in answer
    )


def test_failed_execution_answer_never_needs_synthesis(
    monkeypatch,
):
    execution = [
        {
            "step": 0,
            "ok": False,
            "capability":
                "pytest.read",
            "provider":
                "pytest.provider",
            "result": {
                "ok": False,
                "error":
                    "pytest unavailable",
            },
        },
    ]

    calls = []

    def forbidden_provider_call(**kwargs):
        calls.append(
            kwargs
        )

        raise AssertionError(
            "synthesis must not run "
            "for failed execution"
        )

    monkeypatch.setattr(
        runtime,
        "_provider_call",
        forbidden_provider_call,
    )

    answer = (
        runtime._failed_execution_answer(
            execution
        )
    )

    assert not calls
    assert "pytest unavailable" in answer


def test_failed_execution_formatter_handles_invalid_result():
    execution = [
        {
            "step": 0,
            "ok": False,
            "capability":
                "pytest.read",
            "provider":
                "pytest.provider",
            "error":
                "invalid provider result",
            "result":
                None,
        },
    ]

    answer = (
        runtime._failed_execution_answer(
            execution
        )
    )

    assert (
        "invalid provider result"
        in answer
    )


def test_failed_execution_formatter_handles_security_denial():
    execution = [
        {
            "step": 0,
            "ok": False,
            "capability":
                "sophyane.execute",
            "error":
                "security_denied",
            "security_reason":
                "provenance_denied_execute",
        },
    ]

    answer = (
        runtime._failed_execution_answer(
            execution
        )
    )

    assert (
        "sophyane.execute"
        in answer
    )

    assert (
        "security_denied"
        in answer
    )


def _pytest_read_provenance():
    return {
        "read": True,
        "trust": True,
        "persist": False,
        "execute": False,
        "propagate": False,
        "origin": "user",
    }


def test_failed_dependency_blocks_dependent_executor():
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    calls = []

    registry = CapabilityRegistry()

    prerequisite = Capability(
        name="pytest.prerequisite",
        description="pytest prerequisite",
        provider="pytest.provider",
        privilege="read",
    )

    def prerequisite_executor(arguments):
        del arguments

        calls.append(
            "prerequisite"
        )

        return {
            "ok": False,
            "error":
                "pytest prerequisite failed",
        }

    prerequisite.executor = (
        prerequisite_executor
    )

    registry.register(
        prerequisite
    )

    dependent = Capability(
        name="pytest.dependent",
        description="pytest dependent",
        provider="pytest.provider",
        privilege="read",
    )

    def dependent_executor(arguments):
        del arguments

        calls.append(
            "dependent"
        )

        return {
            "ok": True,
            "value":
                "must never execute",
        }

    dependent.executor = (
        dependent_executor
    )

    registry.register(
        dependent
    )

    provenance = (
        _pytest_read_provenance()
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest failed dependency"
        ),
        steps=[
            PlanStep(
                capability=(
                    "pytest.prerequisite"
                ),
                arguments={},
                depends_on=[],
                provenance=dict(
                    provenance
                ),
            ),
            PlanStep(
                capability=(
                    "pytest.dependent"
                ),
                arguments={},
                depends_on=[
                    0,
                ],
                provenance=dict(
                    provenance
                ),
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Run prerequisite and "
            "dependent pytest steps."
        ),
    )

    assert calls == [
        "prerequisite",
    ]

    assert len(result) == 2

    assert result[0]["ok"] is False
    assert result[1]["ok"] is False

    assert (
        result[1]["error"]
        == "dependency_failed"
    )

    assert (
        result[1]["status"]
        == "skipped"
    )

    assert (
        result[1][
            "failed_dependencies"
        ]
        == [
            0,
        ]
    )


def test_successful_dependency_allows_dependent_executor():
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    calls = []

    registry = CapabilityRegistry()

    prerequisite = Capability(
        name="pytest.prerequisite",
        description="pytest prerequisite",
        provider="pytest.provider",
        privilege="read",
    )

    def prerequisite_executor(arguments):
        del arguments

        calls.append(
            "prerequisite"
        )

        return {
            "ok": True,
            "value":
                "prerequisite succeeded",
        }

    prerequisite.executor = (
        prerequisite_executor
    )

    registry.register(
        prerequisite
    )

    dependent = Capability(
        name="pytest.dependent",
        description="pytest dependent",
        provider="pytest.provider",
        privilege="read",
    )

    def dependent_executor(arguments):
        del arguments

        calls.append(
            "dependent"
        )

        return {
            "ok": True,
            "value":
                "dependent succeeded",
        }

    dependent.executor = (
        dependent_executor
    )

    registry.register(
        dependent
    )

    provenance = (
        _pytest_read_provenance()
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest successful dependency"
        ),
        steps=[
            PlanStep(
                capability=(
                    "pytest.prerequisite"
                ),
                arguments={},
                depends_on=[],
                provenance=dict(
                    provenance
                ),
            ),
            PlanStep(
                capability=(
                    "pytest.dependent"
                ),
                arguments={},
                depends_on=[
                    0,
                ],
                provenance=dict(
                    provenance
                ),
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Run prerequisite and "
            "dependent pytest steps."
        ),
    )

    assert calls == [
        "prerequisite",
        "dependent",
    ]

    assert len(result) == 2

    assert result[0]["ok"] is True
    assert result[1]["ok"] is True


def test_independent_sibling_runs_after_other_step_failure():
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    calls = []

    registry = CapabilityRegistry()

    first = Capability(
        name="pytest.first",
        description="pytest first",
        provider="pytest.provider",
        privilege="read",
    )

    def first_executor(arguments):
        del arguments

        calls.append(
            "first"
        )

        return {
            "ok": False,
            "error":
                "pytest first failed",
        }

    first.executor = (
        first_executor
    )

    registry.register(
        first
    )

    sibling = Capability(
        name="pytest.sibling",
        description="pytest sibling",
        provider="pytest.provider",
        privilege="read",
    )

    def sibling_executor(arguments):
        del arguments

        calls.append(
            "sibling"
        )

        return {
            "ok": True,
            "value":
                "sibling succeeded",
        }

    sibling.executor = (
        sibling_executor
    )

    registry.register(
        sibling
    )

    provenance = (
        _pytest_read_provenance()
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest independent siblings"
        ),
        steps=[
            PlanStep(
                capability="pytest.first",
                arguments={},
                depends_on=[],
                provenance=dict(
                    provenance
                ),
            ),
            PlanStep(
                capability="pytest.sibling",
                arguments={},
                depends_on=[],
                provenance=dict(
                    provenance
                ),
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Run independent pytest steps."
        ),
    )

    assert calls == [
        "first",
        "sibling",
    ]

    assert result[0]["ok"] is False
    assert result[1]["ok"] is True


def test_any_failed_dependency_blocks_multi_dependency_step():
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    calls = []

    registry = CapabilityRegistry()

    def register(
        name,
        *,
        ok,
    ):
        capability = Capability(
            name=name,
            description=name,
            provider="pytest.provider",
            privilege="read",
        )

        def executor(arguments):
            del arguments

            calls.append(
                name
            )

            return {
                "ok": ok,
                "error":
                    (
                        ""
                        if ok
                        else f"{name} failed"
                    ),
            }

        capability.executor = (
            executor
        )

        registry.register(
            capability
        )

    register(
        "pytest.a",
        ok=True,
    )

    register(
        "pytest.b",
        ok=False,
    )

    register(
        "pytest.c",
        ok=True,
    )

    provenance = (
        _pytest_read_provenance()
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest multiple dependencies"
        ),
        steps=[
            PlanStep(
                capability="pytest.a",
                arguments={},
                depends_on=[],
                provenance=dict(
                    provenance
                ),
            ),
            PlanStep(
                capability="pytest.b",
                arguments={},
                depends_on=[],
                provenance=dict(
                    provenance
                ),
            ),
            PlanStep(
                capability="pytest.c",
                arguments={},
                depends_on=[
                    0,
                    1,
                ],
                provenance=dict(
                    provenance
                ),
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Run pytest dependency graph."
        ),
    )

    assert calls == [
        "pytest.a",
        "pytest.b",
    ]

    assert result[0]["ok"] is True
    assert result[1]["ok"] is False

    assert result[2]["ok"] is False

    assert (
        result[2]["error"]
        == "dependency_failed"
    )

    assert (
        result[2]["status"]
        == "skipped"
    )

    assert (
        result[2][
            "failed_dependencies"
        ]
        == [
            1,
        ]
    )


def test_dependency_failure_propagates_transitively():
    from semantic.capability import (
        Capability,
    )

    from semantic.registry import (
        CapabilityRegistry,
    )

    calls = []

    registry = CapabilityRegistry()

    def register(
        name,
        *,
        ok,
    ):
        capability = Capability(
            name=name,
            description=name,
            provider="pytest.provider",
            privilege="read",
        )

        def executor(arguments):
            del arguments

            calls.append(
                name
            )

            return {
                "ok": ok,
                "error":
                    (
                        ""
                        if ok
                        else f"{name} failed"
                    ),
            }

        capability.executor = (
            executor
        )

        registry.register(
            capability
        )

    register(
        "pytest.root",
        ok=False,
    )

    register(
        "pytest.child",
        ok=True,
    )

    register(
        "pytest.grandchild",
        ok=True,
    )

    provenance = (
        _pytest_read_provenance()
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest transitive dependency failure"
        ),
        steps=[
            PlanStep(
                capability="pytest.root",
                arguments={},
                depends_on=[],
                provenance=dict(
                    provenance
                ),
            ),
            PlanStep(
                capability="pytest.child",
                arguments={},
                depends_on=[
                    0,
                ],
                provenance=dict(
                    provenance
                ),
            ),
            PlanStep(
                capability="pytest.grandchild",
                arguments={},
                depends_on=[
                    1,
                ],
                provenance=dict(
                    provenance
                ),
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "Run transitive pytest dependencies."
        ),
    )

    assert calls == [
        "pytest.root",
    ]

    assert result[0]["ok"] is False

    assert (
        result[1]["error"]
        == "dependency_failed"
    )

    assert (
        result[1]["failed_dependencies"]
        == [
            0,
        ]
    )

    assert (
        result[2]["error"]
        == "dependency_failed"
    )

    assert (
        result[2]["failed_dependencies"]
        == [
            1,
        ]
    )


def test_dependency_failure_answer_reports_skipped_step():
    execution = [
        {
            "step": 0,
            "ok": False,
            "capability":
                "pytest.prerequisite",
            "provider":
                "pytest.provider",
            "result": {
                "ok": False,
                "error":
                    "pytest prerequisite failed",
            },
        },
        {
            "step": 1,
            "ok": False,
            "capability":
                "pytest.dependent",
            "error":
                "dependency_failed",
            "status":
                "skipped",
            "failed_dependencies": [
                0,
            ],
        },
    ]

    answer = (
        runtime._failed_execution_answer(
            execution
        )
    )

    assert (
        "pytest prerequisite failed"
        in answer
    )

    assert (
        "pytest.dependent"
        in answer
    )

    assert (
        "dependency_failed"
        in answer
    )


def test_dependency_gate_runs_before_capability_lookup():
    registry = runtime._build_registry(
        workspace=ROOT,
        sophyane_executable=None,
        session_environment={},
    )

    context = _context(
        text="What time is it?"
    )

    provenance = (
        derive_step_provenance(
            context=context,
            capability="system.clock",
            arguments={},
        )
    )

    plan = SemanticPlan(
        interpretation=(
            "pytest dependency gate ordering"
        ),
        steps=[
            PlanStep(
                capability=(
                    "missing.pytest.capability"
                ),
                arguments={},
                depends_on=[],
                provenance={
                    "read": True,
                    "trust": True,
                    "persist": False,
                    "execute": False,
                    "propagate": False,
                    "origin": "user",
                },
            ),
            PlanStep(
                capability="system.clock",
                arguments={},
                depends_on=[
                    0,
                ],
                provenance={
                    **provenance
                    .permissions
                    .__dict__,
                    "origin":
                        provenance.origin.value,
                },
            ),
        ],
        reply=None,
    )

    result = runtime._execute_plan(
        plan=plan,
        registry=registry,
        original_user_text=(
            "What time is it?"
        ),
    )

    assert len(result) == 2

    assert (
        result[0]["error"]
        == "capability unavailable"
    )

    assert (
        result[1]["error"]
        == "dependency_failed"
    )

    assert (
        result[1]["status"]
        == "skipped"
    )
