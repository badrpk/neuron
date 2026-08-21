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
