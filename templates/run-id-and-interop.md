# run_id + Interop contract — canonical (Campus AI OS 5.2.0, Phase 3.5)

**This file is the ONE owner of the run-id and back-socket rules every team follows.**
Teams no longer carry their own copy of these rules. Each team's `references/run-id-and-interop.md`
is a ≤5-line *delta* (its run directory, slug rule, legacy id shape, and a pointer to anything
genuinely team-specific) that names this file.

Same ownership pattern as `context-files.md`, `ledger-paths.md` and `registration-block-spec.md`:
the kernel owns the template (`templates/run-id-and-interop.md`), the campus holds the copy
(`.campus-os/run-id-and-interop.md`, written at founding by campus-start and refreshed by
update-workspace), every team reads the campus copy — so a fix here reaches every installed team
without any of them repackaging.

## How to find THIS file
1. `.campus-os/run-id-and-interop.md` on the campus (always present on a founded or upgraded campus).
2. Else `templates/run-id-and-interop.md` inside the installed Campus AI OS plugin.
A team never bundles a third copy. If neither exists the campus is not installed: stop with the
no-campus line ("This team runs on Campus AI OS — it's free. Install it first, then run me again.").

## 0. Where kernel tools run — the campus kit (`{kernel}`)
The installed plugin and the campus can sit on different machines (Cowork: the plugin in a cloud
container, the campus mounted in a separate device shell). A tool run from the plugin there cannot
see the campus. So the campus holds a copy of the kernel tools it needs, the **kernel kit**:
`.campus-os/kernel/`, same folder layout as the plugin, with `KIT.json` (kit version + a sha256 per
file). Founding writes it; `/update-workspace` and `/campus-doctor` refresh it.
- **`{kernel}`** in every command below = `.campus-os/kernel` on the campus. Run from the campus root
  **in the shell that can see the campus folder** (in Cowork: the device shell, not the plugin's container).
- **Always run kit Python tools as `python3 -I -B`.** `-I` keeps the kit folder from being searched
  before the standard library (a planted `secrets.py` would otherwise load), and `-B` writes no
  bytecode into the kit. The kit holds only the files the plugin lists: any other file, cache
  (`__pycache__`, `.pyc`) or link means do not run it.
- **Before the first tool call in a session, check the kit against the PLUGIN, never against itself.**
  The campus can be shared or written by other teams, and anyone who can edit a kit file can edit
  `KIT.json` too, so the expected hashes always come from the installed plugin's
  `tools/kit-manifest.json`:
  - *One shell sees plugin and campus* (Claude Code, Codex): run the plugin's own copy,
    `python3 -I -B <plugin>/tools/kernel_kit.py check --campus-root <campus> --manifest <plugin>/tools/kit-manifest.json`
    (it also fails on any file the manifest does not list).
  - *Only the campus is visible* (Cowork): read `tools/kit-manifest.json` from the plugin with file
    tools, then hash the kit with a command you type yourself, not with a kit tool, which could be
    the edited file: `python3 -I -B -c 'import hashlib,os;k=".campus-os/kernel";[print("LINK" if os.path.islink(p) else hashlib.sha256(open(p,"rb").read()).hexdigest(), os.path.relpath(p,k)) for d,ds,fs in os.walk(k) for p in sorted(os.path.join(d,x) for x in ds+fs) if os.path.islink(p) or os.path.isfile(p)]'`.
    It lists every file and link in the kit. Each line must be in the manifest's `files` with the
    same hash; the only other line allowed is `KIT.json`. Any extra line (an unlisted file, a cache,
    a `LINK`) or any manifest file missing → the kit fails. Also compare `KIT.json`'s
    `kernel_version` with the manifest's.
  - All hashes match, nothing extra, and the versions are equal → use the kit. Stale, missing,
    changed, extra, or a link → do not run it; run `/update-workspace` (it moves unlisted files to
    `.campus-os/kernel-quarantine/` and re-copies the kit; a link is left for the owner), or this once use
    the plugin's own `tools/` if one shell sees both. `newer` (the kit says a later version than the
    plugin) → do not run it either: either the plugin on this machine is old (tell the owner to update
    it) or the stamp was planted. Never copy an older kit over a newer one unless the owner says the
    stamp is wrong (`kernel_kit.py install --repair`).
- **No Python, no kit that passes the check, and no shell that sees both:** do the step by hand and say so in the run's
  report. A hand-made run_id uses the real current UTC time (never a round placeholder such as
  `…-000000000`), and `results.json` records `"run_id_minted_by": "hand"`. Never claim a validator ran.

## 1. run_id — minted once, inherited everywhere
- **Mint** with the campus minter: `python3 -I -B {kernel}/tools/mint_run_id.py mint <slug> --team <team> --campus-root .`
  (the Foundry's `mint-run-id` is a thin adapter over the same module). Canonical shape:
  `{slug}-{YYYYMMDD-HHMMSSfff}` (UTC, millisecond), plus `-xxxx` only on a same-millisecond collision.
  The model never invents a run_id.
- **Inherit** a `run_id` that arrives on a fed `brief.json` or a playbook-stage input **unchanged**.
  Never re-mint an inherited id. One run_id per run, stamped on every output and on the ledger line.
- **Read permissively.** Older ids (`{team}-{YYYYMMDD-HHMMSS}`, `{YYYYMMDD}-{slug<=24}-{4char}`,
  `…T…Z` stamps) parse via `{kernel}/tools/mint_run_id.py parse` and are never rejected on read. New writes
  use the canonical shape only.

## 2. Run directory — one path builder
`outputs/{YYYY-MM}/runs/{team}/{slug}/{run_id}/` on a campus (playbooks: `runs/playbooks/{slug}/{run_id}/`).
`{slug}` is a short kebab-case name for the run's subject; the team's delta says what the subject is.
The minter creates the directory; drafts, `MANIFEST.json` and `results.json` land in **that** directory.
The registry `results` field (`…/runs/{team}/{slug}/results.json`) names the *prefix*; the run_id level
below it is canonical (Phase 3.5 decision; the aggregator scans `runs/**/results.json`, so both levels read).
Ask `{kernel}/tools/mint_run_id.py path --team T --slug S [--run-id R]` rather than formatting the path yourself.

## 3. results.json — the back socket, envelope v1.1
Canonical definition: `schemas/results.schema.json` in the kernel (byte-identical copy in the Foundry).
Validate or classify with `{kernel}/tools/validate_results.py`. Write shape, every run:

| Field | Value |
|---|---|
| `schema_version` | `"1.1"` |
| `profile` | `"completion-only"` for saleable teams; `"full"` only for owner-side emitters |
| `run_id` / `team` / `slug` | the run's id, the emitting team's registry id, the slug |
| `generated_at` | ISO 8601 with zone (UTC `Z`) |
| `assets[]` | one entry per artifact: `type`, `path`, `status`, `tier`, `url`, `external_ref`, `completion` (optional `performance`, `attribution`) — may be empty |
| `completion` | run-level self-report: `execution_success`, `artifact_passed`, `owner_approved` — three booleans, never inferred from assets |
| `bindings[]` | optional in 5.2.0: `stage`, `employee`, `employee_type`, `version`, `reason`, `alternatives[]`, `outcome` |
| `external_ref`, `permission`, `outcome` | optional, opaque to the envelope |

Append-only and per-team: a team writes its **own** `results.json` in its **own** run directory and never
rewrites another team's ledger. Reporting aggregates; it does not require teams to share a file.

## 4. Completion-only — the honest draft state (saleable teams)
The floor is **draft-first**. On a buyer install every asset is `status: "draft"`, `tier: "local"`,
`url: null`, `external_ref: null`, `attribution: {}`, and `performance` is **absent**. Absent ≠ failure.
Never invent an `external_ref` for a draft — a thing the owner has not published has no stable handle,
and a fabricated one poisons the join key outcome backfill depends on.
- `execution_success` = the run finished. `artifact_passed` = every asset passed its own done-check.
  `owner_approved` = the owner said yes (or a standing grant the owner wrote covered it). Producing a
  draft is success; it is not approval; the two are never collapsed.
- Connector-pulled `performance` and CTA→purchase `attribution` are **owner-side only** — they need the
  buyer's analytics / CRM / payment stack and are never wired into a saleable team.
- Where a team may publish under a grant the owner wrote (per platform, per verb, in that team's config),
  the published asset records `status: "published"` plus the platform's real `external_ref`, and names
  the grant. A bundle ships zero grants.

## 5. MANIFEST.json — run state (resumability)
One per run, in the run directory: `started`, `last_updated`, `status`, `current_step`,
`completed_steps[]` (objects: `skill`, `step_no`, `started`, `ended`, `outcome`), `failed_steps[]`,
`done_checks[]`, `checkpoints[]` (human gates), `config_snapshot`. Internal run state, never a socket.

## 6. Sockets
**Front:** accept owner `raw-input` or a fed `brief.json` / playbook-stage input carrying a `run_id`
(inherit it); never hard-require another team. **Back:** emit `results.json` for `results-aggregator`,
`/atlas-report` and the campus morning brief.

## 7. Ledger-lint — terminal assertion before a run is "done"
1. `run_id` identical everywhere it appears (MANIFEST, every asset, the ledger line).
2. Every asset carries `status` + `tier`; every produced asset has a done-check result.
3. No asset is `published`, `sent` or `scheduled` unless a named owner grant authorized it —
   otherwise the draft-first floor was breached.
4. No orphan artifact on disk missing from `assets[]`.
5. `results.json` classifies `v1.1-valid` (`{kernel}/tools/validate_results.py FILE`).
In draft state `external_ref: null` and `attribution: {}` are correct and are never flagged.

## 8. CTA attribution — a contract, never a vendor literal
Assets that carry a CTA link may carry `attribution: { method, token }` with `token = run_id` and
`method` an opaque, install-resolved adapter string — **only** when the owner has wired a live
attribution surface. No `utm_`, coupon, analytics or vendor name in any skill body. No surface (the
saleable default) → `attribution: {}` and honest absence.

*Source of truth for these rules: this file (kernel-owned). Read contract for pre-v1.1 ledgers:
`wiki/concepts/team-interop-spec-v1.md` (Interop v1 §3–§5, kept as history).*
