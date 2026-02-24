---
name: get-shit-done
description: Structured spec-driven workflow for planning and executing software projects with Codex CLI.
---

# Get Shit Done (GSD) Skill for Codex CLI

## When to use
- Use this skill when the user asks for GSD or uses a `$gsd-*` command.
- Use it for structured planning, phase execution, verification, or roadmap work.

## How to run commands
Codex CLI supports custom commands with `$` prefix. Commands starting with `$gsd-` are custom skills.

Commands are installed as individual skills in `.codex/skills/`. Load the corresponding skill:

`.codex/skills/gsd-<command>/SKILL.md`

Example:
- `$gsd-new-project` -> `.codex/skills/gsd-new-project/SKILL.md`
- `$gsd-help` -> `.codex/skills/gsd-help/SKILL.md`

## File references
Command files and workflows include `@path` references. These are mandatory context. Use the read_file tool to load each referenced file before proceeding.

## Tool mapping
- "exec_command tool" -> use the `exec_command` tool (shell commands, git)
- "read_file" -> use the `read_file` tool (read files with offset/limit)
- "apply_patch" -> use the `apply_patch` tool (create/edit files with freeform diff)
- "grep_files" -> use the `grep_files` tool (regex search across files)
- "list_dir" -> use the `list_dir` tool (directory listing)
- "request_user_input" -> use the `request_user_input` tool (ask user questions)
- "spawn_agent" -> use `spawn_agent` to create sub-agents, `send_input` to message them, `wait` to collect results
- "web_search" -> use the `web_search` tool

## User questioning policy (mandatory)
- When asking users questions, prefer `request_user_input` over plain-text prompts.
- All user-facing question text must be Chinese:
  - `header`
  - `question`
  - `options[].label`
  - `options[].description`
- Do not show English-only question prompts to users.
- If free-form details are required, still open with a Chinese `request_user_input` question first, then collect details through `Other`.

## Output expectations
Follow the XML or markdown formats defined in the command and template files exactly. These files are operational prompts, not documentation.

## Paths
Resources are installed under `.codex/get-shit-done`. Individual skills are under `.codex/skills/gsd-*/`. Use those paths when command content references platform paths.
