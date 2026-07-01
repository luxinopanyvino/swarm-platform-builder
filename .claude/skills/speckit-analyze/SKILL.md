---
name: "speckit-analyze"
description: "Análisis de consistencia (solo lectura) de un SPEC de docs/specs/ frente a su ADR y su bloque sdd-sync de tareas."
argument-hint: "SPEC objetivo (ruta docs/specs/… o id SPEC-XXX) + focos opcionales de análisis"
compatibility: "Adaptado a este repo: cruza SPEC ↔ ADR ↔ bloque sdd-sync; NO requiere el andamiaje .specify/"
metadata:
  author: "github-spec-kit (adaptado para swarm-platform-builder)"
  source: "templates/commands/analyze.md"
user-invocable: true
disable-model-invocation: false
---

> **Nota de adaptación.** Ayuda de autoría de [github/spec-kit](https://github.com/github/spec-kit)
> adaptada al SDD casero de este repo. Es el skill de **peor encaje**: spec-kit lo
> diseñó para cruzar `spec.md`+`plan.md`+`tasks.md`, artefactos que aquí no existen
> por-feature. Se reinterpreta para cruzar el **SPEC** (`docs/specs/`), su **ADR**
> (`docs/adr/`) y su **bloque `sdd-sync`** de tareas. La "constitution" es
> **`docs/governance/GOVERNANCE.md`**. Solo lectura; NO reemplaza `/sdd-sync` ni
> `scripts/validate_specs.py`.


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Identify inconsistencies, duplications, ambiguities, and underspecified items across a SPEC, its ADR, and its `sdd-sync` task block before implementation. Run this once a SPEC is (or is about to be) **Ready** and its task block is populated.

## Operating Constraints

**STRICTLY READ-ONLY**: Do **not** modify any files. Output a structured analysis report. Offer an optional remediation plan (user must explicitly approve before any follow-up editing).

**Constitution Authority**: The project governance (`docs/governance/GOVERNANCE.md`) is **non-negotiable** within this analysis scope. Governance conflicts (e.g., branch-naming contract §3, Definition of Done §6) are automatically CRITICAL and require adjusting the SPEC/ADR/tasks — not diluting or silently ignoring the rule. Changing a rule itself must happen in a separate, explicit governance update.

## Execution Steps

### 1. Initialize Analysis Context

Resolve the target artifacts (this repo uses `docs/specs/`, not the spec-kit `specs/NNN/` layout):

- **SPEC** = the file resolved from `$ARGUMENTS` (a path under `docs/specs/`, or an id `SPEC-XXX` → `docs/specs/SPEC-XXX-*.md`). If none/ambiguous, list `docs/specs/SPEC-*.md` and ask.
- **ADR** = the ADR the SPEC references under `docs/adr/` (may be absent — note it, do not abort).
- **TASKS** = the SPEC's structured `sdd-sync` task block (the same block `/sdd-sync` and `scripts/validate_specs.py` read). If absent, note it and analyze SPEC↔ADR only.

Treat remaining words in `$ARGUMENTS` as optional focus areas.

### 2. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context:

**From the SPEC:**

- Overview/Context
- Functional Requirements / acceptance criteria (AC#)
- Success Criteria (measurable outcomes)
- Edge Cases (if present)

**From the ADR (if present):**

- Decision, chosen approach and rejected alternatives
- Technical constraints / consequences

**From the `sdd-sync` task block:**

- Task ids (e.g. T#.# / epic-task ids), titles
- Referenced acceptance criteria / dependencies

**From governance:**

- Load `docs/governance/GOVERNANCE.md` for rule validation (branch contract, DoD, PR/entrega rules)

### 3. Build Semantic Models

Create internal representations (do not include raw artifacts in output):

- **Requirements inventory**: For each Functional Requirement (FR-###) and Success Criterion (SC-###), record a stable key. Use the explicit FR-/SC- identifier as the primary key when present, and optionally also derive an imperative-phrase slug for readability (e.g., "User can upload file" → `user-can-upload-file`). Include only Success Criteria items that require buildable work (e.g., load-testing infrastructure, security audit tooling), and exclude post-launch outcome metrics and business KPIs (e.g., "Reduce support tickets by 50%").
- **User story/action inventory**: Discrete user actions with acceptance criteria
- **Task coverage mapping**: Map each task to one or more requirements or stories (inference by keyword / explicit reference patterns like IDs or key phrases)
- **Governance rule set**: Extract rule names and MUST/SHOULD normative statements from GOVERNANCE.md (branch contract, DoD, entrega por PR)

### 4. Detection Passes (Token-Efficient Analysis)

Focus on high-signal findings. Limit to 50 findings total; aggregate remainder in overflow summary.

#### A. Duplication Detection

- Identify near-duplicate requirements
- Mark lower-quality phrasing for consolidation

#### B. Ambiguity Detection

- Flag vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria
- Flag unresolved placeholders (TODO, TKTK, ???, `<placeholder>`, etc.)

#### C. Underspecification

- Requirements with verbs but missing object or measurable outcome
- User stories missing acceptance criteria alignment
- Tasks referencing files or components not defined in spec/plan

#### D. Governance Alignment

- Any requirement or task element conflicting with a MUST rule in GOVERNANCE.md
- Missing mandated sections or quality gates from governance (e.g., DoD §6)

#### E. Coverage Gaps

- Requirements with zero associated tasks
- Tasks with no mapped requirement/story
- Success Criteria requiring buildable work (performance, security, availability) not reflected in tasks

#### F. Inconsistency

- Terminology drift (same concept named differently across files)
- Data entities referenced in plan but absent in spec (or vice versa)
- Task ordering contradictions (e.g., integration tasks before foundational setup tasks without dependency note)
- Conflicting requirements (e.g., one requires Next.js while other specifies Vue)

### 5. Severity Assignment

Use this heuristic to prioritize findings:

- **CRITICAL**: Violates a governance MUST, missing core spec artifact, or requirement with zero coverage that blocks baseline functionality
- **HIGH**: Duplicate or conflicting requirement, ambiguous security/performance attribute, untestable acceptance criterion
- **MEDIUM**: Terminology drift, missing non-functional task coverage, underspecified edge case
- **LOW**: Style/wording improvements, minor redundancy not affecting execution order

### 6. Produce Compact Analysis Report

Output a Markdown report (no file writes) with the following structure:

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | HIGH | SPEC-013:L120-134 | Two similar requirements ... | Merge phrasing; keep clearer version |

(Add one row per finding; generate stable IDs prefixed by category initial.)

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|

**Governance Alignment Issues:** (if any)

**Unmapped Tasks:** (if any)

**Metrics:**

- Total Requirements
- Total Tasks
- Coverage % (requirements with >=1 task)
- Ambiguity Count
- Duplication Count
- Critical Issues Count

### 7. Provide Next Actions

At end of report, output a concise Next Actions block:

- If CRITICAL issues exist: Recommend resolving before moving the SPEC to Ready or before `/resolve-task`
- If only LOW/MEDIUM: User may proceed, but provide improvement suggestions
- Provide explicit suggestions: e.g., "Refine the SPEC's acceptance criteria", "Update the referenced ADR", "Run /sdd-sync to reconcile the task block with the backlog", "Add a task in the sdd-sync block to cover 'performance-metrics'"

### 8. Offer Remediation

Ask the user: "Would you like me to suggest concrete remediation edits for the top N issues?" (Do NOT apply them automatically.)

## Operating Principles

### Context Efficiency

- **Minimal high-signal tokens**: Focus on actionable findings, not exhaustive documentation
- **Progressive disclosure**: Load artifacts incrementally; don't dump all content into analysis
- **Token-efficient output**: Limit findings table to 50 rows; summarize overflow
- **Deterministic results**: Rerunning without changes should produce consistent IDs and counts

### Analysis Guidelines

- **NEVER modify files** (this is read-only analysis)
- **NEVER hallucinate missing sections** (if absent, report them accurately)
- **Prioritize governance violations** (these are always CRITICAL)
- **Use examples over exhaustive rules** (cite specific instances, not generic patterns)
- **Report zero issues gracefully** (emit success report with coverage statistics)

## Context

$ARGUMENTS
