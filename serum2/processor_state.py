"""
Processor-state safety boundary for Serum 2.0.21 VST3 processor state.

This module validates the container metadata/body boundary before a generated
state is allowed to reach Serum.

Important distinction:

- A .SerumPreset body is not automatically a VST3 processor state.
- A valid Serum 2.0.21 VST3 processor state must retain native processor
  metadata, including component="processor" and version=8.0.
- Corpus data must be normalized onto a native V8 processor skeleton rather
  than treated as a complete processor-state container.

This module performs validation only. It does not mutate the supplied state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple


PROCESSOR_COMPONENT = "processor"
PROCESSOR_VERSION = 8.0


class ProcessorStateError(ValueError):
    """Base error for invalid Serum processor-state construction."""


class ProcessorMetadataError(ProcessorStateError):
    """Raised when VST3 processor metadata is missing or invalid."""


class ProcessorBodyError(ProcessorStateError):
    """Raised when the processor body is structurally invalid."""


@dataclass(frozen=True)
class ProcessorStateContext:
    """
    Immutable validated processor-state context.

    The actual meta/body objects remain owned by the caller. This object
    records the validation-relevant identity and provenance without silently
    rewriting state.
    """

    meta: Mapping[str, Any]
    body: Mapping[str, Any]
    source: str = "unknown"

    @property
    def component(self) -> Any:
        return self.meta.get("component")

    @property
    def version(self) -> Any:
        return self.meta.get("version")


def validate_processor_metadata(meta: Mapping[str, Any]) -> None:
    """
    Validate the metadata required for Serum 2.0.21 VST3 processor state.

    This deliberately rejects malformed/ambiguous metadata instead of trying
    to repair it implicitly.
    """
    if not isinstance(meta, Mapping):
        raise ProcessorMetadataError(
            "processor metadata must be a mapping"
        )

    if "component" not in meta:
        raise ProcessorMetadataError(
            "missing required processor metadata field: 'component'"
        )

    if meta["component"] != PROCESSOR_COMPONENT:
        raise ProcessorMetadataError(
            "invalid processor component: "
            f"{meta['component']!r}; expected {PROCESSOR_COMPONENT!r}"
        )

    if "version" not in meta:
        raise ProcessorMetadataError(
            "missing required processor metadata field: 'version'"
        )

    try:
        version = float(meta["version"])
    except (TypeError, ValueError) as exc:
        raise ProcessorMetadataError(
            f"invalid processor version: {meta['version']!r}"
        ) from exc

    if version != PROCESSOR_VERSION:
        raise ProcessorMetadataError(
            f"unsupported processor state version: {version!r}; "
            f"expected {PROCESSOR_VERSION!r}"
        )


def validate_processor_body(body: Mapping[str, Any]) -> None:
    """
    Validate the minimum structural contract of a processor body.

    Do not impose a complete 162-key schema here. Serum-native state contains
    many keys whose exact presence/value semantics belong to Serum itself.

    The important safety boundary is that we never confuse a completely
    unvalidated object with a processor body.
    """
    if not isinstance(body, Mapping):
        raise ProcessorBodyError("processor body must be a mapping")

    if not body:
        raise ProcessorBodyError("processor body is empty")


def validate_processor_state(
    meta: Mapping[str, Any],
    body: Mapping[str, Any],
    *,
    source: str = "unknown",
) -> ProcessorStateContext:
    """
    Validate a complete processor state without modifying it.

    Raises before serialization/plugin loading when the processor identity
    contract is not satisfied.
    """
    validate_processor_metadata(meta)
    validate_processor_body(body)

    return ProcessorStateContext(
        meta=meta,
        body=body,
        source=source,
    )


def require_processor_state(
    skeleton: Tuple[Mapping[str, Any], Mapping[str, Any]],
    *,
    source: str = "skeleton",
) -> Tuple[Mapping[str, Any], Mapping[str, Any]]:
    """
    Validate and return an existing (meta, body) skeleton unchanged.

    This is the intended integration point for the evidence harness.
    """
    if not isinstance(skeleton, tuple) or len(skeleton) != 2:
        raise ProcessorStateError(
            "skeleton must be a (meta, body) tuple"
        )

    meta, body = skeleton

    validate_processor_state(meta, body, source=source)

    return skeleton