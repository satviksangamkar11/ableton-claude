autowatch = 1;

inlets = 3;
outlets = 2;

/*
 * Experiment A Harness v0.1
 * Scope: A0 + A1 ONLY
 *
 * Inlet 0:
 *   Raw vst~ parameter enumeration output.
 *
 * Inlet 1:
 *   Raw vst~ get/value output.
 *
 * Inlet 2:
 *   Recorder control / metadata messages.
 *
 * Outlet 0:
 *   Commands sent TO vst~.
 *
 * Outlet 1:
 *   Recorder status.
 *
 * HARD RULE:
 * This file records observations.
 * It does NOT interpret semantic identity,
 * mutation class, value meaning, or production capability.
 */


// -----------------------------------------------------------------------------
// RUN STATE
// -----------------------------------------------------------------------------

var runId = "A0-A1-" + timestampId();
var startedAt = new Date().toISOString();

var hostVersion = "UNKNOWN";

var pluginName = "UNKNOWN";
var pluginVersion = "2.0.21";
var pluginFormat = "VST3";
var pluginIdentifier = "UNKNOWN";

var parameterCount = null;

// Raw parameter-name observations.
// Each entry is:
// {
//     index: Number,
//     name: String,
//     observed_at: ISO timestamp
// }
var parameterNames = [];

// Raw parameter-value observations.
// Key = parameter index as string.
// Value:
// {
//     index: Number,
//     normalized: raw value,
//     symbolic: raw symbolic value,
//     observed_at: ISO timestamp
// }
var parameterValues = {};


// -----------------------------------------------------------------------------
// A0 VIABILITY
// -----------------------------------------------------------------------------

var viability = {
    load: "UNKNOWN",
    editor_open: "UNKNOWN",
    audio_path: "UNKNOWN",
    midi: "UNKNOWN",
    snapshot: "UNKNOWN"
};


// -----------------------------------------------------------------------------
// FROZEN RECORDER CONTRACT
// -----------------------------------------------------------------------------

var recorderContract = {
    recorder_scope: "A0-A1",

    semantic_interpretation: false,
    classification: false,
    value_interpretation: false,

    preserve_raw_representation: true,

    mutation_testing: false,
    restore_testing: false,
    persistence_testing: false,
    runtime_behavior_testing: false
};


// -----------------------------------------------------------------------------
// BASIC STATUS
// -----------------------------------------------------------------------------

function bang()
{
    outlet(1, "ready", runId);
}


// -----------------------------------------------------------------------------
// RESET
// -----------------------------------------------------------------------------

function reset()
{
    runId = "A0-A1-" + timestampId();
    startedAt = new Date().toISOString();

    parameterCount = null;

    parameterNames = [];
    parameterValues = {};

    viability = {
        load: "UNKNOWN",
        editor_open: "UNKNOWN",
        audio_path: "UNKNOWN",
        midi: "UNKNOWN",
        snapshot: "UNKNOWN"
    };

    outlet(1, "reset", runId);
}


// -----------------------------------------------------------------------------
// A0 STATUS MARKERS
// -----------------------------------------------------------------------------

function markload(value)
{
    viability.load = normalizeStatus(value);
    outlet(1, "load", viability.load);
}


function markeditor(value)
{
    viability.editor_open = normalizeStatus(value);
    outlet(1, "editor_open", viability.editor_open);
}


function markaudiopath(value)
{
    viability.audio_path = normalizeStatus(value);
    outlet(1, "audio_path", viability.audio_path);
}


function markmidi(value)
{
    viability.midi = normalizeStatus(value);
    outlet(1, "midi", viability.midi);
}


function marksnapshot(value)
{
    viability.snapshot = normalizeStatus(value);
    outlet(1, "snapshot", viability.snapshot);
}


function normalizeStatus(value)
{
    var s = String(value).toUpperCase();

    if (s === "PASS")
        return "PASS";

    if (s === "FAIL")
        return "FAIL";

    return "UNKNOWN";
}


// -----------------------------------------------------------------------------
// A1 PARAMETER ENUMERATION
// -----------------------------------------------------------------------------

/*
 * We deliberately preserve the textual representation emitted by vst~.
 *
 * No attempt is made to decide what the parameter means.
 */

function recordParameterName(index, name)
{
    var idx = Number(index);

    if (!isFinite(idx))
        return;

    parameterNames.push({
        index: idx,
        name: String(name),
        observed_at: new Date().toISOString()
    });

    outlet(1, "parameter_name", idx, String(name));
}


function recordParameterValue(index, normalized, symbolic)
{
    var idx = Number(index);

    if (!isFinite(idx))
        return;

    var rec = {
        index: idx,
        normalized: normalized,
        observed_at: new Date().toISOString()
    };

    if (symbolic !== undefined)
        rec.symbolic = symbolic;

    parameterValues[String(idx)] = rec;

    outlet(1, "parameter_value", idx, normalized);

    if (symbolic !== undefined)
        outlet(1, "parameter_symbolic", idx, symbolic);
}


// -----------------------------------------------------------------------------
// RAW vst~ PARAMETER OUTPUT
// -----------------------------------------------------------------------------
//
// Max can split a symbol containing spaces into message name + arguments.
// Therefore reconstruct the textual payload without interpreting it.
//

function anything()
{
    var args = arrayfromargs(arguments);
    var message = messagename;

    // -------------------------------------------------------------------------
    // INLET 0 = raw parameter-name stream
    // -------------------------------------------------------------------------

    if (inlet === 0)
    {
        var raw = message;

        if (args.length > 0)
            raw += " " + args.join(" ");

        // Parameter names returned by vst~ are observations only.
        // Assign ordinal index in arrival order here.
        //
        // This is NOT semantic indexing. It is simply the order in which
        // the host enumeration was observed.
        var index = parameterNames.length;

        recordParameterName(index, raw);
        return;
    }


    // -------------------------------------------------------------------------
    // INLET 2 = recorder controls / metadata
    // -------------------------------------------------------------------------

    if (inlet === 2)
    {
        if (message === "set_host_version")
        {
            hostVersion = args.join(" ");
            return;
        }

        if (message === "set_plugin_name")
        {
            pluginName = args.join(" ");
            return;
        }

        if (message === "set_plugin_version")
        {
            pluginVersion = args.join(" ");
            return;
        }

        if (message === "set_plugin_identifier")
        {
            pluginIdentifier = args.join(" ");
            return;
        }

        if (message === "export")
        {
            export_json();
            return;
        }

        if (message === "reset")
        {
            reset();
            return;
        }

        if (message === "markload")
        {
            markload(args.length ? args[0] : "UNKNOWN");
            return;
        }

        if (message === "markeditor")
        {
            markeditor(args.length ? args[0] : "UNKNOWN");
            return;
        }

        if (message === "markaudiopath")
        {
            markaudiopath(args.length ? args[0] : "UNKNOWN");
            return;
        }

        if (message === "markmidi")
        {
            markmidi(args.length ? args[0] : "UNKNOWN");
            return;
        }

        if (message === "marksnapshot")
        {
            marksnapshot(args.length ? args[0] : "UNKNOWN");
            return;
        }

        outlet(1, "unknown_control", message);
        return;
    }


    // -------------------------------------------------------------------------
    // INLET 1 = raw vst~ value/get output
    // -------------------------------------------------------------------------

    if (inlet === 1)
    {
        var data = [message].concat(args);

        /*
         * Expected conceptual form:
         *
         *   <index> <normalized> [symbolic...]
         *
         * We do not convert the normalized value to a semantic domain.
         */

        if (data.length >= 2)
        {
            var idx = Number(data[0]);

            if (!isFinite(idx))
            {
                outlet(1, "unrecognized_value", data.join(" "));
                return;
            }

            // Special vst~ get -4 result:
            // parameter count.
            if (idx === -4)
            {
                parameterCount = Number(data[1]);

                if (isFinite(parameterCount))
                {
                    outlet(1, "parameter_count", parameterCount);
                }
                else
                {
                    parameterCount = null;
                    outlet(1, "parameter_count", "UNKNOWN");
                }

                return;
            }

            var normalized = data[1];
            var symbolic = undefined;

            if (data.length > 2)
                symbolic = data.slice(2).join(" ");

            recordParameterValue(
                idx,
                normalized,
                symbolic
            );

            return;
        }

        outlet(1, "unrecognized_value", data.join(" "));
        return;
    }
}


// -----------------------------------------------------------------------------
// INTEGER / FLOAT HANDLERS
// -----------------------------------------------------------------------------
//
// Some Max message routes deliver numeric messages through int/float methods.
// Handle them here as well.
//

function int()
{
    var args = arrayfromargs(arguments);

    handleNumericMessage(args);
}


function float()
{
    var args = arrayfromargs(arguments);

    handleNumericMessage(args);
}


function handleNumericMessage(args)
{
    if (inlet !== 1)
        return;

    if (args.length < 2)
        return;

    var idx = Number(args[0]);

    if (!isFinite(idx))
        return;

    if (idx === -4)
    {
        parameterCount = Number(args[1]);

        if (isFinite(parameterCount))
            outlet(1, "parameter_count", parameterCount);

        return;
    }

    recordParameterValue(
        idx,
        args[1],
        args.length > 2 ? args.slice(2).join(" ") : undefined
    );
}


// -----------------------------------------------------------------------------
// COMMANDS TO vst~
// -----------------------------------------------------------------------------

function load_serum()
{
    /*
     * The actual plug-in path/identifier should be supplied by the Max patch.
     * This JS recorder does not guess or invent it.
     *
     * Example patch message:
     *
     *     plug "C:/.../Serum2.vst3"
     *
     * or another valid vst~ loading mechanism appropriate to the machine.
     */
    outlet(0, "plug");
}


function open_editor()
{
    outlet(0, "open");
}


function request_parameter_count()
{
    outlet(0, "get", -4);
}


function request_parameters()
{
    outlet(0, "params");
}


// -----------------------------------------------------------------------------
// EXPORT
// -----------------------------------------------------------------------------

function export_json()
{
    var d = new Dict();

    d.clear();

    // -------------------------------------------------------------------------
    // EXPERIMENT METADATA
    // -------------------------------------------------------------------------

    d.set("experiment", "16_5_A");
    d.set("run_id", runId);
    d.set("timestamp", startedAt);

    // -------------------------------------------------------------------------
    // HOST
    // -------------------------------------------------------------------------

    d.set("host::application", "Ableton Live");
    d.set("host::container", "Max for Live");
    d.set("host::version", hostVersion);

    // -------------------------------------------------------------------------
    // PLUGIN
    // -------------------------------------------------------------------------

    d.set("plugin::name", pluginName);
    d.set("plugin::version", pluginVersion);
    d.set("plugin::format", pluginFormat);
    d.set("plugin::identifier", pluginIdentifier);

    // -------------------------------------------------------------------------
    // A0 VIABILITY
    // -------------------------------------------------------------------------

    d.set("viability::load", viability.load);
    d.set("viability::editor_open", viability.editor_open);
    d.set("viability::audio_path", viability.audio_path);
    d.set("viability::midi", viability.midi);
    d.set("viability::snapshot", viability.snapshot);

    // -------------------------------------------------------------------------
    // A1 PARAMETER COUNT
    // -------------------------------------------------------------------------

    if (parameterCount === null)
        d.set("parameters::count", "UNKNOWN");
    else
        d.set("parameters::count", parameterCount);

    // -------------------------------------------------------------------------
    // A1 PARAMETER LIST
    // -------------------------------------------------------------------------

    var list = [];

    for (var i = 0; i < parameterNames.length; i++)
    {
        var nameObservation = parameterNames[i];

        var rec = {
            index: nameObservation.index,
            name: nameObservation.name,
            query_timestamp: nameObservation.observed_at
        };

        var valueObservation =
            parameterValues[String(nameObservation.index)];

        if (valueObservation)
        {
            if (valueObservation.normalized !== undefined)
                rec.normalized = valueObservation.normalized;

            if (valueObservation.symbolic !== undefined)
                rec.symbolic = valueObservation.symbolic;

            // Preserve the actual value observation timestamp.
            rec.value_observation_timestamp =
                valueObservation.observed_at;
        }

        list.push(rec);
    }

    d.set("parameters::list", list);

    // -------------------------------------------------------------------------
    // RECORDER CONTRACT
    // -------------------------------------------------------------------------

    d.set(
        "recorder_contract::semantic_interpretation",
        recorderContract.semantic_interpretation
    );

    d.set(
        "recorder_contract::classification",
        recorderContract.classification
    );

    d.set(
        "recorder_contract::value_interpretation",
        recorderContract.value_interpretation
    );

    d.set(
        "recorder_contract::preserve_raw_representation",
        recorderContract.preserve_raw_representation
    );

    d.set(
        "recorder_contract::mutation_testing",
        recorderContract.mutation_testing
    );

    d.set(
        "recorder_contract::restore_testing",
        recorderContract.restore_testing
    );

    d.set(
        "recorder_contract::persistence_testing",
        recorderContract.persistence_testing
    );

    d.set(
        "recorder_contract::runtime_behavior_testing",
        recorderContract.runtime_behavior_testing
    );

    // -------------------------------------------------------------------------
    // STATUS
    // -------------------------------------------------------------------------

    d.set(
        "status",
        "COMPLETE"
    );

    d.set(
        "artifacts",
        ["owned_host_surface.json"]
    );

    // -------------------------------------------------------------------------
    // WRITE FILE
    // -------------------------------------------------------------------------

    var file =
        new File(
            "owned_host_surface.json",
            "write",
            "TEXT"
        );

    if (!file.isopen)
    {
        outlet(1, "export_failed");
        return;
    }

    file.writestring(
        d.stringify()
    );

    file.close();

    outlet(
        1,
        "exported",
        "owned_host_surface.json"
    );
}


// -----------------------------------------------------------------------------
// TIMESTAMP
// -----------------------------------------------------------------------------

function timestampId()
{
    var d = new Date();

    function z(n)
    {
        return (n < 10 ? "0" : "") + n;
    }

    return (
        d.getFullYear().toString() +
        z(d.getMonth() + 1) +
        z(d.getDate()) +
        "T" +
        z(d.getHours()) +
        z(d.getMinutes()) +
        z(d.getSeconds())
    );
}
