"""15.2.8.4: FXDistortion Enable -- discovery-only, NOT a claim.

Conclusion: UNKNOWN. Not UNSUPPORTED (that would assert Serum demonstrably
rejects the mechanism -- we never tested a mutation because no valid mutation
target was found). Not a new status tier either -- UNKNOWN plus this recorded
search metadata is sufficient; the capability ladder is not expanded just
because discovery was hard this round.
"""
import pickle

FXDISTORTION_ENABLE_DISCOVERY = {
    "family": "FXDistortion",
    "field": "Enable",
    "status": "UNKNOWN",
    "reason": "no_valid_mutation_target_found",
    "mechanism_search": {
        "body_field": {
            "checked": "FXRack0.FX[i].FXDistortion.plainParams.kParamEnable",
            "result": "not_found",
            "detail": "corpus: 515/516 instances None, 1 stray 0.0; Aardvark's real "
                      "instance (FX[2]) has no kParamEnable key at all in plainParams "
                      "(only kParamDrive/kParamLevelOut/kParamMode/kParamWet present)",
        },
        "fxrack_level_field": {
            "checked": "FXRack0.plainParams",
            "result": "not_found",
            "detail": "empty dict across all 997 corpus bodies observed",
        },
        "type_field": {
            "checked": "FXRack0.FX[i].type",
            "result": "identified_as_unit_selector_not_enable",
            "detail": "integer values 0-15 correspond 1:1 with the 16 FX-family kind "
                      "names by occurrence count (e.g. type=0 count=517 matches "
                      "FXDistortion count=517 exactly) -- this is a kind discriminant, "
                      "not a bypass flag",
        },
        "host_parameter": {
            "checked": "full VST3 parameter list (2623 params) via DawDreamer "
                      "get_parameters_description, keyword-filtered on "
                      "dist/enable/bypass/fx",
            "result": "not_found",
            "detail": "found: global 'Bypass' (whole-plugin, index 16), unrelated "
                     "'A/B/C/Noise/Sub Enable' (oscillator/voice section enables, not "
                     "FX-unit enables), and generically-numbered 'FX Main Param 1-16' / "
                     "'FX Bus 1-2 Param 1-16' (positional passthrough knobs for whatever "
                     "unit occupies that host-exposed slot -- not a named per-unit enable)",
        },
        "flex_field": {
            "checked": "FXRack0.FX[i].flex",
            "result": "not_decoded",
            "detail": "observed as a list of dicts (e.g. [{}, {}] in Aardvark's "
                      "FXDistortion instance) -- structurally present but semantically "
                      "unexplored. Explicitly deferred, not ruled out as the enable "
                      "mechanism's location.",
        },
    },
    "conclusion": (
        "We searched the currently understood representation (body fields, "
        "FXRack-level fields, the type discriminant, and the full host parameter "
        "list) and did not find an Enable mechanism for an individual FX unit. "
        "This does NOT mean Serum has no such mechanism, and does NOT mean Enable "
        "is unsupported -- flex remains unresolved, so both stronger claims are "
        "premature. No mutation experiment was run because no valid target exists "
        "yet: no causal claim, no persistence claim, no ClaimEngine promotion."
    ),
    "backlog": "15.2.8.x -- Decode flex: structurally present, semantically unexplored, "
              "deferred as its own investigation rather than blocking FX-family discovery.",
}

pickle.dump(FXDISTORTION_ENABLE_DISCOVERY,
           open(r"D:/ableton claude/experiments/_fxdist_enable_discovery.pkl", "wb"))
print("Recorded discovery note (no claim, no promotion):")
print(FXDISTORTION_ENABLE_DISCOVERY["conclusion"])
