# Changelog

All notable changes to the Campus AI OS kernel. Format follows Keep a Changelog; versions follow Semantic Versioning (security fixes are patch releases). Released entries are never rewritten; corrections go in a later entry. The packaged artifact hash for every release is in the sibling `campus-ai-os-v{version}.PACKAGE.json`, never retyped here.

## [Unreleased]

_Nothing yet._

## [5.2.11] - 2026-09-23

Repairs the one release blocker from the Codex re-audit of the packaged 5.2.10 artifact, and carries the pack-neutral wording the first niche builds need. Patch: no new keys, no migration beyond the version marker.

### Fixed
- **Write instructions still sent a co-primary to the shared ledger.** An assigned Claude Code or Codex client resolves `role: primary` with `owns_clock: false`, but the sanctioned team-plugin wording in `templates/ledger-paths.md`, `/campus-first-win` and `/full-onboarding` told it to append to `dean/.activity.jsonl`. They, and the same wording in `hr-recruit`, `promote-skills`, `templates/model-routing.md`, `playbooks/README.md` and the one-recording playbook, now name the ledger the seat resolves to; only the clock owner writes the shared file. Team plugins cut earlier keep the old phrase until their next release; `ledger-paths.md` says how to read it.
- `QUICKSTART.md` was headed "Campus AI OS v4.1", also in the public 5.2.9 release. Root doc titles no longer carry a version.
- `README.md` and `QUICKSTART.md` said "education business" whatever the pack; the business noun now comes from the active pack.

### Changed
- `/campus-first-win` also offers the active pack's own domain skills when the pack declares any beyond the three defaults; the education default is unchanged.

### Added
- `tests/test_ledger_writers_5211.py` - runs the real resolver for a non-clock primary and fails if any shipped instruction writes the shared ledger without the clock-owner qualifier.
- `tests/test_kernel_cargo_5211.py` - doc titles, pack-neutral business noun, first-win pack skills.

## [5.2.10] - 2026-09-20

Co-primary reaches every written contract, and the minimum pack plumbing a second niche pack needs. Additive: every new `pack.json` key is optional, a campus founded on 5.2.9 needs no migration beyond the version marker, and the education build assembles file-identical to the source tree.

### Fixed
- **Co-primary had not reached every contract.** The resolver sends a primary client that is not the clock owner to its own ledger shard, but `templates/ledger-paths.md` still said "Primary: `dean/.activity.jsonl`", the generated contract listed `claude-code` and `codex` as satellite by default, and the brain templates and the Codex adapter told every client to append to the shared ledger. All now say one thing: append only to the ledger `resolve-seat.py` returns; only the `clock_owner` client writes the shared ledger. `contracts/campus.json` gains `seat.ledger.clock_owner`, `co_primary` and `write_rule`; `seat.ledger.primary` keeps its value because readers resolve the shared ledger by that key. The remaining Codex lane rules stay with SEC-05.
- **A second in-tree pack failed NICHE-024 by design.** `templates/registry.json` is one derived file; the label-parity check compared it against whichever pack was being checked. It now belongs to the active pack. A non-active pack's registry template is derived when that pack is assembled, by the same generator, so no second copy is stored.
- `tools/build_niche.py --check` and `tools/gen_department_entries.py` defaulted to the literal `education`. Both now default to the active pack.

### Added
- **`packs/active.json`** - one pointer, `{"active_pack": "..."}`, naming the pack this tree is built for. `campus-start`, its interview reference, `wiki-ingest` and `wiki-query` resolve the pack through it; `--assemble` rewrites it for the pack being built.
- **`shared_skills[]`** (optional, `pack.json`) - a pack borrows another pack's domain skills. `--assemble` keeps them; ownership is read from the skill's own `pack:` tag, so it still resolves after the owning pack's folder is removed.
- **`hires[]`** (optional, `pack.json`) - a pack may carry pre-vetted hire manifests in the `.campus-os/hires/*.json` shape. Key and gate only; routing to a hire is not part of this release.
- Gate checks **NICHE-025** (active pack pointer; no skill spells a pack folder), **NICHE-026** (shared skills) and **NICHE-027** (pack hires: full 40-character pin, https repo, license, never above `draft-only`).
- `tests/test_phase7_pack_plumbing.py` - 17 fixtures: contract and template parity with the resolver, the pointer, a second in-tree pack, per-pack registry derivation, the file-identical round trip for the active pack, borrowed-skill survival, and hire-manifest rejection cases.
- `packs/professor/pack.json` declares `shared_skills` and an empty `hires`.
- `README.md` links to the public repository.

## [5.2.9] - 2026-09-14

First release prepared for public GitHub distribution (`trainingsites/campus-ai-os`). Scope is the co-primary seat model only; SEC-04/05/06 ride a dedicated security train at 5.3.0 or later by owner decision (2026-09-13).

### Fixed
- `tests/test_phase0_coprimary.py` doctor fixtures issued their host binding against the frozen fixture clock while the doctor reads wall-clock time, so the suite began failing on its own three days after 5.2.8. The two doctor fixtures now issue the binding relative to real time; resolver fixtures keep the frozen clock.

### Changed
- **Co-primary seats.** A campus may now designate more than one client `primary` in `seat.json`, so an owner can work from any installed client and finish the job there — closing tasks, writing memory and wiki — instead of filing a proposal for another seat to merge. Single-primary campuses are unaffected: a `seat.json` with one primary and no `clock_owner` resolves exactly as before.
- **`clock_owner` names the single scheduling seat.** One campus, one clock is preserved by configuration rather than by role: `clock_owner` is the one client that runs recurring jobs, holds the host binding, and writes the shared ledger `dean/.activity.jsonl`. Every other primary appends to its own shard. The resolver returns `owns_clock` so a client can tell the difference. A co-primary `seat.json` without a valid `clock_owner` is refused and the caller stays satellite.
- **Doctor is co-primary aware.** Check 11a treats a stamp from any configured primary seat as expected instead of unresolved attribution, while an unrecognised seat is still reported. Check 11d validates the host binding against the clock owner; previously a co-primary config made it advise deleting a valid binding.

### Security
- Unchanged boundary, re-proven by fixture: an unknown machine fingerprint, an unassigned client, a sandbox with no binding, an expired binding, and a binding issued for a client that is not the clock owner all still resolve satellite. Co-primary widens who may write on one recognised installation; it does not widen what counts as recognised.

### Added
- `tests/test_phase0_coprimary.py` — 17 fixtures covering co-primary resolution, clock ownership, ledger routing, the unchanged satellite boundary, config integrity, legacy single-primary behaviour, and the two doctor checks. Suite is 226 tests.

## [5.2.8] - 2026-09-11

### Removed
- **Campus Map public/sales-demo build.** By owner decision after the 5.2.5 security audit, the map is private-only. `--public` (and `PUBLIC=1`) now exit with code 2 and a message; no `campus-map-public.html` can be produced. The 5.2.7 deny-by-default public schema is retired with it. A private map is never shared, so no "safe for strangers" mode exists to get wrong.

### Changed
- `campus-map` skill and command describe the map as private-only and document `--no-remote-fonts` / `CAMPUS_MAP_OFFLINE=1` for a no-network build. CSP and brand-field validation from 5.2.7 remain on every build.

### Security
- Nothing new. 5.2.6 and 5.2.7 closed every finding in the Campus Map generator; 5.2.8 removes the public output path so the SEC-01 class cannot recur. Still open from the audit, for a later train: SEC-04 (untrusted-content section in the instruction chain), SEC-05 (Codex adapter lane rules), SEC-06 (signed release provenance).

## [5.2.7] - 2026-09-11

### Security
- **Campus Map `--public` build now denies by default (SEC-01).** A public map carried raw ledger text and the full bodies of every linked document, brief and report. It now carries aggregates and kernel labels only: no ledger text, file paths, document bodies, brief or wiki titles, result rows, OKR or focus text, and no documents are read at all in public mode. Affects 5.0.0 through 5.2.6.
- **Brand and orchestrator fields could become markup (SEC-03 remainder).** `brand_name` reached `<title>` unescaped and font fields reached CSS unvalidated. The title is escaped, font names and the font import URL must match a narrow grammar or fall back to defaults, and remaining client-side sinks (staff line, scheduled last-run) are escaped. Affects 5.0.0 through 5.2.6.
- **Content Security Policy on every generated map.** Only the generator's own inline script (by hash) may run; styles inline; no other origins.
- **No network request from public builds (SEC-07).** Public maps and `--no-remote-fonts` (or `CAMPUS_MAP_OFFLINE=1`) builds load no web fonts. Private builds still load Google Fonts by default and say so in `SECURITY.md`.

### Added
- Fixtures: public-build canary across ledger, outputs, briefs, results, wiki, goals, scheduled and brand sources; malicious brand and orchestrator fields; CSP and no-network assertions.

## [5.2.6] - 2026-09-10

### Security
- **Campus Map generator: path traversal and symlink escape out of the campus root.** A ledger `output` path such as `outputs/../../secret.txt` passed the root check and its contents were inlined into the generated map, including `--public` builds. Paths are now rejected on any `..`, empty segment, URL scheme, absolute or drive form, or control character, and every document read is proven by real path to live under the campus root as a regular file. Affects 5.0.0 through 5.2.5. Reported by the Codex security audit of the 5.2.5 archive.
- **Campus Map inline viewer: stored XSS through markdown link targets.** Quote characters were not escaped and link targets were emitted verbatim, so a crafted link in any linked markdown file became a live event handler. Quotes are now escaped and link targets are limited to relative paths and http(s)/mailto. Affects 5.0.0 through 5.2.5. Same report.

### Added
- `CHANGELOG.md`, `SECURITY.md`, `README.md` ship with the kernel.
- Fixtures `test_campus_map_security.py` and `test_security_packaging.py`; the packager refuses to cut without a changelog entry for the version.

## [5.2.5] - 2026-09-09
### Fixed
- Doctor: a missing `seat.json` reports as not-applicable rather than red; exit code 1 whenever any line is red, per the skill contract. Found by the Cowork 5.2.4 cold install. <!-- version-literal-ok -->

## [5.2.4] - 2026-09-09
### Added
- Host binding for seat resolution; offers canon; ledger-paths promotion.

## [5.2.3] - 2026-09-08
### Fixed
- Registration spec is materialized on every upgrade path, not only the baseline path. Owner content in a kernel canon now shows the diff and asks rather than overwriting.

## [5.2.2] - 2026-09-08
### Fixed
- Doctor evidence ledger section skips `#` header comment lines.

## [5.2.1] - 2026-09-08
### Fixed
- Doctor version-lockstep check routes an owed upgrade to `/update-workspace` instead of a bare stamp.

## [5.2.0] - 2026-09-08
### Changed
- Single kernel tree; version lockstep across ten homes enforced by the packager; Codex manifest derived from the Claude manifest; machine-readable contract regenerated at cut.
