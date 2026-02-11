# IoT.2 vs samples/mockup — Analysis and Next Steps

This document captures the detailed comparison, schema validation, and updated recommendations for aligning `samples/mockup` with the PICMG IoT.2 requirements. It preserves the full findings from the interactive review and provides a prioritized list of implementation items and which changes are schema-compliant vs. those that would require an IoT.2 erratum.

---

## Summary of findings

- The sample mockup contains a fully populated `XAxisMover` AutomationNode and associated
  `Chassis` and `Controls`/`Sensors`. Many IoT.2 expectations are already present (proper
  `SENSOR_ID_x` / `EFFECTER_ID_x` naming, AutomationNode actions, Cables linking to
  Chassis).  
- Key mismatches: several instrumentation-related values are placed under `Oem.PICMG`
  rather than exposed via schema-compliant properties or links; sensor threshold shape differs from
  IoT.2/Redfish expected threshold properties; FRU binary/Assembly is not present.

## Schema validation brief

- AutomationInstrumentation schema (AutomationInstrumentation_v1) does not define
  `Position`, `Velocity`, or `Acceleration` properties; it exposes navigation properties
  such as `NodeControl` and `PID` (Control links) and a set of excerpt sensor nav props
  (TemperatureCelsius, Voltage, CurrentAmps). Therefore moving `Oem.PICMG.Position`
  to a top-level AutomationInstrumentation.Position is not allowed by the schema.
- Control schema (Control_v1) defines a top-level `DataSourceUri` property and a
  `Sensor` NavigationProperty; embedding a custom sensor object with `DataSourceURI`
  and `Reading` is non-standard. The schema expects either a `DataSourceUri` string and/or
  a `Sensor` navigation link/excerpt.
- Sensor schema expects standard threshold fields (UpperCaution, UpperCritical, etc.).
  The mockup's nested `Thresholds` object is not the canonical shape.
- Assembly/AssemblyData and `BinaryDataURI` are supported by the Assembly schema and are
  appropriate for storing FRU binary data.

## Updated, schema-compliant recommendations (per earlier report)

1. AutomationInstrumentation: do not add new top-level Position/Velocity properties. Instead:
   - Keep vendor convenience copies under `Oem.PICMG` if desired.
   - Create `Control` resources for pfinal/vprofile/aprofile effecters and set `DataSourceUri`
     on those `Control` resources to reference the controlling sensor or external data.
   - Do not add `NodeControl` or `PID` navigation properties. Instead, reference
     Controls and Sensors using Control `DataSourceUri` and the `Sensor` navigation
     property, or keep vendor convenience copies under `Oem.PICMG` for tooling that
     requires them. We will not invent Control navprops solely to carry links.

2. Controls & Sensor linking:
   - Convert embedded `Sensor` objects inside `Control` resources to schema-compliant
     `DataSourceUri` (top-level string) and use the `Sensor` navigation property to hold
     an `@odata.id` link or excerpt copy. Remove duplicated `Reading` from `Control` and
     keep readings on the `Sensor` resource.
   - Clarification: Control resources are optional per IoT.1. When a node exposes
     Control resources, include a top-level `DataSourceUri` (and/or a `Sensor`
     navigation property) to reference the controlling `Sensor`. If a node does not
     expose Control resources, representing the relationship via AutomationInstrumentation
     navigation properties or under `Oem` vendor fields is acceptable—do not invent
     controls solely to carry sensor links.
  
  - Decision (mockup): preserve the current `Sensor` excerpt in the `Control` mockup
    files. The `Control` schema permits an excerpt/copy (including `Reading`) as a
    convenience snapshot; therefore `samples/mockup` will keep those excerpts intact.
    Rationale: this matches common Redfish mockups and improves client convenience
    (single-GET visibility). Note that this duplicates dynamic state; consumers and
    tests should treat the `Sensor` resource as the authoritative source of live
    `Reading` values, and the mockup excerpts are a persisted snapshot for convenience.

3. Thresholds:
   - No changes are required.  All mockup structures are found to be compliant.

4. Assembly / FRU:
   - Add an `Assembly` resource (or `AssemblyData`) and set `BinaryDataURI` to the raw FRU
     blob for nodes that provide FRU data. Map top-level FRU fields into the Chassis per IoT.2.

5. Collections:
   - Always reconcile collection index files with actual resources on disk; when adding new resources, merge members into collections and update `Members@odata.count`.

6. OEM usage:
   - Do not place required IoT.2 fields under `Oem`. Use `Oem` only for vendor-specific extras not required by IoT.2.

## Items that would require IoT.2 errata (i.e., non-compliant alternatives)

- Adding top‑level `Position` / `Velocity` properties to AutomationInstrumentation is
  not supported by the current schema. If the project needs these properties as first-class
  fields in AutomationInstrumentation (instead of links to Controls/Sensors), that change
  would require a formal IoT.2 schema extension or erratum proposing new AutomationInstrumentation
  properties. Document these as candidate errata.

## Concrete next steps (proposed order)

1. Create a small, schema-compliant patch to `samples/mockup` for `XAxisMover`:
   - Convert `Controls/EFFECTER_ID_4` to include `DataSourceUri` top-level pointing to
     the sensor; set `Sensor` as a link/excerpt instead of embedded object.
   - Add an `Assembly` resource under the chassis with a placeholder `BinaryDataURI`.
   - Preserve existing `Oem.PICMG` entries (do not remove) but add schema-compliant
     links/navigation properties so generic clients can discover instrumentation.

2. Translate thresholds on Aggregator sensors to canonical Redfish threshold fields and
   keep vendor shape under `Oem`.

3. If you want `Position`/`Velocity` as top-level AutomationInstrumentation properties,
   draft an IoT.2 erratum describing the new fields and rationale.

4. Run tests and validate the mockup against the Redfish schema (via existing schema
   validation tooling if available) and produce a short report.

---

## Files changed / created by this analysis
- `tools/pldm-mapping-wizard/IOT2_mockup_analysis.md` (this file)

---

If you confirm, I'll start with step 1.a (convert `Control.Sensor` embedded object into
`DataSourceUri` + `Sensor` link for `samples/mockup/Chassis/XAxisMover/Controls/EFFECTER_ID_4`),
make the minimal Assembly addition, and create a patch. I will leave the vendor `Oem` fields
in place and only add schema-compliant properties.

