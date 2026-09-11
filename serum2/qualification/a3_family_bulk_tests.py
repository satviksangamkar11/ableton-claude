"""16.5.69.2-A3: Family bulk qualifier framework tests.

Tests for:
  - discovery filtering
  - representative selection
  - route reuse vs evidence reuse
  - bulk individual attribution
  - exception isolation
  - executor boundary
  - surface classification
"""

from __future__ import annotations

import pytest

from serum2.qualification.a3_family_bulk_qualifier import (
    FamilyControl,
    Representative,
    RoutePatternSet,
    MutationClass,
    discover_family,
    select_representatives,
    bulk_qualify_members,
    isolate_exceptions,
    ParameterQualificationRecord,
)
from serum2.qualification.a3_route import MutationRoute, BehaviorRoute
from serum2.qualification.a3_control_executor import NullExecutor
from serum2.qualification.a3_surface_classifier import (
    classify_parameter,
    SurfaceClass,
    is_meaningful_surface,
    filter_meaningful_parameters,
    group_by_family,
)


# ---------------------------------------------------------------------------
# Test: Discovery filtering
# ---------------------------------------------------------------------------

class TestDiscoveryFiltering:
    def test_discover_family_extracts_osc1_controls(self):
        """Discovery extracts all Osc1-prefixed controls."""
        inventory = [
            {
                "semantic_candidate": "OSC1.Enable",
                "vst3_name": "A Enable",
                "vst3_index": 20,
                "mutation_class": "BOOLEAN",
            },
            {
                "semantic_candidate": "UNMAPPED",
                "vst3_name": "A Level",
                "vst3_index": 21,
                "mutation_class": "SCALAR",
            },
            {
                "semantic_candidate": "UNMAPPED",
                "vst3_name": "B Octave",
                "vst3_index": 23,
                "mutation_class": "INTEGER",
            },
        ]

        controls = discover_family(inventory, "Osc1")

        assert len(controls) == 2
        assert controls[0].vst3_name == "A Enable"
        assert controls[1].vst3_name == "A Level"
        assert all(c.family == "Osc1" for c in controls)

    def test_discover_family_sorted_by_index(self):
        """Discovery returns controls sorted by vst3_index."""
        inventory = [
            {
                "vst3_name": "A Level",
                "vst3_index": 21,
                "mutation_class": "SCALAR",
                "semantic_candidate": "UNMAPPED",
            },
            {
                "vst3_name": "A Enable",
                "vst3_index": 20,
                "mutation_class": "BOOLEAN",
                "semantic_candidate": "OSC1.Enable",
            },
        ]

        controls = discover_family(inventory, "Osc1")

        assert controls[0].vst3_index == 20
        assert controls[1].vst3_index == 21

    def test_discover_family_with_unknown_mutation_class(self):
        """Discovery handles unknown mutation classes gracefully."""
        inventory = [
            {
                "vst3_name": "A Enable",
                "vst3_index": 20,
                "mutation_class": "BOGUS_CLASS",
                "semantic_candidate": "OSC1.Enable",
            }
        ]

        controls = discover_family(inventory, "Osc1")

        assert len(controls) == 1
        assert controls[0].mutation_class == MutationClass.UNKNOWN


# ---------------------------------------------------------------------------
# Test: Representative selection
# ---------------------------------------------------------------------------

class TestRepresentativeSelection:
    def test_select_representatives_reuses_existing_evidence(self):
        """Selection prioritizes reusing existing evidence."""
        controls = [
            FamilyControl(
                family="Osc1",
                semantic_id="OSC1.Enable",
                vst3_name="A Enable",
                vst3_index=20,
                mutation_class=MutationClass.BOOLEAN,
            ),
            FamilyControl(
                family="Osc1",
                semantic_id="UNMAPPED.Level",
                vst3_name="A Level",
                vst3_index=21,
                mutation_class=MutationClass.SCALAR,
            ),
        ]
        existing_evidence = {"OSC1.Enable": "evidence_123"}

        reps = select_representatives(controls, existing_evidence)

        assert len(reps) >= 1
        reused = [r for r in reps if r.reuse_existing]
        assert any(r.semantic_id == "OSC1.Enable" for r in reused)

    def test_select_representatives_picks_one_per_mutation_class(self):
        """Selection picks at most one representative per mutation class."""
        controls = [
            FamilyControl(
                family="Osc1",
                semantic_id="Scalar1",
                vst3_name="A Level",
                vst3_index=21,
                mutation_class=MutationClass.SCALAR,
            ),
            FamilyControl(
                family="Osc1",
                semantic_id="Scalar2",
                vst3_name="A Pan",
                vst3_index=22,
                mutation_class=MutationClass.SCALAR,
            ),
            FamilyControl(
                family="Osc1",
                semantic_id="Bool1",
                vst3_name="A Enable",
                vst3_index=20,
                mutation_class=MutationClass.BOOLEAN,
            ),
        ]

        reps = select_representatives(controls, {})

        scalar_reps = [r for r in reps if r.mutation_class == MutationClass.SCALAR]
        bool_reps = [r for r in reps if r.mutation_class == MutationClass.BOOLEAN]

        assert len(scalar_reps) == 1
        assert len(bool_reps) == 1


# ---------------------------------------------------------------------------
# Test: Bulk qualification with route reuse
# ---------------------------------------------------------------------------

class TestBulkQualification:
    def test_bulk_qualify_uses_proven_routes(self):
        """Bulk qualification applies proven routes to family members."""
        controls = [
            FamilyControl(
                family="Osc1",
                semantic_id="Scalar1",
                vst3_name="A Level",
                vst3_index=21,
                mutation_class=MutationClass.SCALAR,
            ),
            FamilyControl(
                family="Osc1",
                semantic_id="Scalar2",
                vst3_name="A Pan",
                vst3_index=22,
                mutation_class=MutationClass.SCALAR,
            ),
        ]

        proven_route = MutationRoute(adapter="host_param", host_param="A Level")
        routes = RoutePatternSet(
            family="Osc1",
            patterns={MutationClass.SCALAR: proven_route},
        )

        executor = NullExecutor()
        executor.state["Scalar1"] = 0.0
        executor.state["Scalar2"] = 0.0

        result = bulk_qualify_members(controls, routes, executor)

        assert result.discovered == 2
        assert result.family == "Osc1"
        assert len(result.results) == 2

    def test_bulk_qualify_records_individual_evidence(self):
        """Bulk qualification produces individual evidence per parameter."""
        controls = [
            FamilyControl(
                family="Osc1",
                semantic_id="Scalar1",
                vst3_name="A Level",
                vst3_index=21,
                mutation_class=MutationClass.SCALAR,
            ),
        ]

        proven_route = MutationRoute(adapter="host_param", host_param="A Level")
        routes = RoutePatternSet(
            family="Osc1",
            patterns={MutationClass.SCALAR: proven_route},
        )

        executor = NullExecutor()
        executor.state["Scalar1"] = 0.0

        result = bulk_qualify_members(controls, routes, executor, test_values={MutationClass.SCALAR: 0.5})

        assert len(result.results) == 1
        record = result.results[0]
        assert isinstance(record, ParameterQualificationRecord)
        assert record.semantic_id == "Scalar1"
        assert record.baseline_value == 0.0
        assert record.mutated_value == 0.5

    def test_bulk_qualify_isolates_exceptions(self):
        """Bulk qualification separates controls with no matching route."""
        controls = [
            FamilyControl(
                family="Osc1",
                semantic_id="Scalar1",
                vst3_name="A Level",
                vst3_index=21,
                mutation_class=MutationClass.SCALAR,
            ),
            FamilyControl(
                family="Osc1",
                semantic_id="Bool1",
                vst3_name="A Enable",
                vst3_index=20,
                mutation_class=MutationClass.BOOLEAN,
            ),
        ]

        # Only SCALAR route proven; BOOLEAN has no route
        proven_route = MutationRoute(adapter="host_param", host_param="A Level")
        routes = RoutePatternSet(
            family="Osc1",
            patterns={MutationClass.SCALAR: proven_route},
        )

        executor = NullExecutor()
        executor.state["Scalar1"] = 0.0
        executor.state["Bool1"] = False

        result = bulk_qualify_members(controls, routes, executor)

        assert len(result.exceptions) == 1
        assert result.exceptions[0].mutation_class == MutationClass.BOOLEAN


# ---------------------------------------------------------------------------
# Test: Exception isolation
# ---------------------------------------------------------------------------

class TestExceptionIsolation:
    def test_isolate_exceptions_returns_failed_controls(self):
        """Exception isolation extracts controls that failed qualification."""
        controls = [
            FamilyControl(
                family="Osc1",
                semantic_id="Scalar1",
                vst3_name="A Level",
                vst3_index=21,
                mutation_class=MutationClass.SCALAR,
            ),
        ]

        exception = FamilyControl(
            family="Osc1",
            semantic_id="Bool1",
            vst3_name="A Enable",
            vst3_index=20,
            mutation_class=MutationClass.BOOLEAN,
        )

        result = RoutePatternSet(
            family="Osc1",
            patterns={},
        )

        from serum2.qualification.a3_family_bulk_qualifier import BulkQualificationResult

        bulk_result = BulkQualificationResult(
            family="Osc1",
            discovered=2,
            qualified=1,
            exceptions=[exception],
        )

        exceptions = isolate_exceptions(bulk_result)

        assert len(exceptions) == 1
        assert exceptions[0].semantic_id == "Bool1"


# ---------------------------------------------------------------------------
# Test: Surface classification
# ---------------------------------------------------------------------------

class TestSurfaceClassification:
    def test_classify_parameter_synthesis(self):
        """Classification recognizes synthesis parameters."""
        assert classify_parameter("A Enable") == SurfaceClass.SYNTHESIS
        assert classify_parameter("A Pitch") == SurfaceClass.SYNTHESIS
        assert classify_parameter("Filter 1 Cutoff") == SurfaceClass.SYNTHESIS
        assert classify_parameter("Env 1 Attack") == SurfaceClass.SYNTHESIS

    def test_classify_parameter_modulation(self):
        """Classification recognizes modulation parameters."""
        assert classify_parameter("LFO 1 Rate") == SurfaceClass.MODULATION

    def test_classify_parameter_effect(self):
        """Classification recognizes effect parameters."""
        assert classify_parameter("Mod Delay Time") == SurfaceClass.EFFECT

    def test_classify_parameter_midi(self):
        """Classification recognizes MIDI passthrough."""
        assert classify_parameter("MIDI Velocity") == SurfaceClass.MIDI
        assert classify_parameter("Mod Wheel") == SurfaceClass.MIDI

    def test_is_meaningful_surface(self):
        """Meaningful surface includes synthesis, effects, modulation."""
        assert is_meaningful_surface(SurfaceClass.SYNTHESIS)
        assert is_meaningful_surface(SurfaceClass.EFFECT)
        assert is_meaningful_surface(SurfaceClass.MODULATION)
        assert not is_meaningful_surface(SurfaceClass.MIDI)
        assert not is_meaningful_surface(SurfaceClass.NON_SYNTHESIS)

    def test_filter_meaningful_parameters(self):
        """Filtering removes MIDI and non-synthesis parameters."""
        params = [
            {"vst3_name": "A Enable", "vst3_index": 20},
            {"vst3_name": "MIDI Velocity", "vst3_index": 100},
            {"vst3_name": "Filter 1 Cutoff", "vst3_index": 30},
        ]

        filtered = filter_meaningful_parameters(params)

        assert len(filtered) == 2
        names = {p["vst3_name"] for p in filtered}
        assert "A Enable" in names
        assert "Filter 1 Cutoff" in names
        assert "MIDI Velocity" not in names

    def test_group_by_family(self):
        """Grouping organizes parameters by family."""
        params = [
            {"vst3_name": "A Enable", "surface_class": "synthesis"},
            {"vst3_name": "A Level", "surface_class": "synthesis"},
            {"vst3_name": "B Enable", "surface_class": "synthesis"},
            {"vst3_name": "Filter 1 Cutoff", "surface_class": "synthesis"},
        ]

        grouped = group_by_family(params)

        assert "Osc1" in grouped
        assert "Osc2" in grouped
        assert "Filter1" in grouped
        assert len(grouped["Osc1"]) == 2
        assert len(grouped["Osc2"]) == 1
