---
name: more-paper-workflow
description: >-
  Use when the user asks for more-paper-workflow or its legacy names more-paper-workflow-pro-skill and more paper workflow pro skill (more paper, more-paper, more_paper, morepaper): research topic clarification, outline and keyword generation, structured literature search plans, multi-source literature search and scoring, paper PDF download routing, Zotero library organization, review matrices, paper writing, native paper flowcharts or architecture diagrams, scientific figure generation or reproduction, plot digitization, figure QA, citation audit, or polishing.
---

# more-paper-workflow Codex discovery shim

This file exists only because `.codex-plugin/plugin.json` declares
`"skills": "./skills/"`, so Codex plugin discovery expects an entry at
`skills/more-paper-workflow/SKILL.md`. It is a thin adapter, not a second
runtime contract and not a Claude Code requirement.

For every real workflow rule, read the complete
[canonical runtime contract](../../SKILL.md) before acting. Resolve every
relative path in that contract from the repository root two levels above this
file, which is also this plugin's root.

The canonical contract routes into `agents/`, `references/`, `scripts/`,
`static/`, and `commands/`; all of those directories are packaged with this
root plugin. Claude Code-style direct use should enter from the root
`SKILL.md`; Codex plugin installation keeps this shim so discovery can find the
same canonical contract.

Before routing, verify that `../../SKILL.md` and the selected exact entry below
exist. If either is absent, report `incomplete_plugin_installation` with the
missing path; never shorten or synthesize a filename such as
`agents/step_7.md`.

- Step 1: `agents/step_1_entry.md` → `agents/step_1_topic.md`
- Step 2: `agents/step_2_outline.md`
- Step 3: `agents/step_3_entry.md` → `agents/step_3_search_plan.md`
- Step 4: `agents/step_4_search_score.md`
- Step 5: `agents/step_5_download.md`
- Step 6: `agents/step_6_entry.md` → `agents/step_6_zotero.md`
- Step 7: `agents/step_7_entry.md` → `agents/step_7_writing.md`
- Step 8: `agents/step_8_entry.md` → `agents/step_8_polishing.md`
