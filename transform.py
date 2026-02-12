#!/usr/bin/env python3
"""
Transform GSD from Claude Code to Codex CLI.
Handles all mechanical text replacements across all .md files.
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. Tool name replacements (context-aware)
# ============================================================
# These are ordered carefully - longer matches first to avoid partial replacements

TOOL_REPLACEMENTS = [
    # Exact tool references in frontmatter and prose
    (r'\bAskUserQuestion\b', 'request_user_input'),
    (r'\bWebSearch\b', 'web_search'),
    (r'\bWebFetch\b', 'web_fetch'),  # Note: Codex doesn't have this, but keep name consistent
    (r'\bTodoWrite\b', 'update_plan'),
    (r'\bNotebookEdit\b', 'apply_patch'),
    (r'\bEnterPlanMode\b', 'request_user_input'),  # No direct equivalent
    (r'\bExitPlanMode\b', 'request_user_input'),    # No direct equivalent
]

# Tool names that need context-aware replacement (avoid false positives)
# These are common English words, so we only replace them in specific contexts
CONTEXT_TOOL_REPLACEMENTS = [
    # "the Read tool" / "Use Read" / "Read tool" / "Read(" / "`Read`"
    (r'(?:the |use |Use |a )Read\b(?= tool| to )', lambda m: m.group().replace('Read', 'read_file')),
    (r'\bRead tool\b', 'read_file tool'),
    (r'\bRead\(', 'read_file('),
    (r'`Read`', '`read_file`'),
    (r'\bRead,\s', 'read_file, '),

    (r'(?:the |use |Use |a )Write\b(?= tool| to )', lambda m: m.group().replace('Write', 'apply_patch')),
    (r'\bWrite tool\b', 'apply_patch tool'),
    (r'\bWrite\(', 'apply_patch('),
    (r'`Write`', '`apply_patch`'),
    (r'\bWrite,\s', 'apply_patch, '),

    (r'(?:the |use |Use |a )Edit\b(?= tool| to )', lambda m: m.group().replace('Edit', 'apply_patch')),
    (r'\bEdit tool\b', 'apply_patch tool'),
    (r'\bEdit\(', 'apply_patch('),
    (r'`Edit`', '`apply_patch`'),
    (r'\bEdit,\s', 'apply_patch, '),

    (r'(?:the |use |Use |a )Bash\b(?= tool| to | command)', lambda m: m.group().replace('Bash', 'exec_command')),
    (r'\bBash tool\b', 'exec_command tool'),
    (r'\bBash\(', 'exec_command('),
    (r'`Bash`', '`exec_command`'),
    (r'\bBash,\s', 'exec_command, '),

    (r'(?:the |use |Use |a )Grep\b(?= tool| to )', lambda m: m.group().replace('Grep', 'grep_files')),
    (r'\bGrep tool\b', 'grep_files tool'),
    (r'\bGrep\(', 'grep_files('),
    (r'`Grep`', '`grep_files`'),
    (r'\bGrep,\s', 'grep_files, '),

    (r'(?:the |use |Use |a )Glob\b(?= tool| to )', lambda m: m.group().replace('Glob', 'list_dir')),
    (r'\bGlob tool\b', 'list_dir tool'),
    (r'\bGlob\(', 'list_dir('),
    (r'`Glob`', '`list_dir`'),
    (r'\bGlob,\s', 'list_dir, '),
]

# Frontmatter tools: field replacement (comma-separated list)
FRONTMATTER_TOOL_MAP = {
    'Read': 'read_file',
    'Write': 'apply_patch',
    'Edit': 'apply_patch',
    'Bash': 'exec_command',
    'Grep': 'grep_files',
    'Glob': 'list_dir',
    'Task': 'spawn_agent',
    'AskUserQuestion': 'request_user_input',
    'WebSearch': 'web_search',
    'WebFetch': 'web_fetch',
    'TodoWrite': 'update_plan',
}


def replace_frontmatter_tools(content):
    """Replace tool names in YAML frontmatter tools: field."""
    def replace_tools_line(m):
        prefix = m.group(1)  # "tools: " or "  - "
        tools_str = m.group(2)
        tools = [t.strip() for t in tools_str.split(',')]
        new_tools = []
        seen = set()
        for t in tools:
            mapped = FRONTMATTER_TOOL_MAP.get(t, t)
            if mapped not in seen:
                new_tools.append(mapped)
                seen.add(mapped)
        return prefix + ', '.join(new_tools)

    # Match "tools: Read, Write, ..." in frontmatter
    content = re.sub(r'^(tools:\s*)(.+)$', replace_tools_line, content, flags=re.MULTILINE)
    return content


def replace_allowed_tools(content):
    """Replace tool names in allowed-tools: YAML list."""
    lines = content.split('\n')
    new_lines = []
    in_allowed_tools = False
    seen_tools = set()

    for line in lines:
        if re.match(r'^allowed-tools:\s*$', line):
            in_allowed_tools = True
            new_lines.append(line)
            seen_tools = set()
            continue

        if in_allowed_tools:
            m = re.match(r'^(\s+-\s+)(\S+)\s*$', line)
            if m:
                prefix = m.group(1)
                tool = m.group(2)
                mapped = FRONTMATTER_TOOL_MAP.get(tool, tool)
                if mapped not in seen_tools:
                    new_lines.append(f"{prefix}{mapped}")
                    seen_tools.add(mapped)
                continue  # Skip duplicate mappings (Write/Edit both → apply_patch)
            else:
                in_allowed_tools = False

        new_lines.append(line)

    return '\n'.join(new_lines)


# ============================================================
# 2. Path replacements
# ============================================================

def replace_paths(content):
    """Replace .claude/ paths with .codex/ paths."""
    # Absolute paths with home dir
    content = re.sub(
        r'/Users/[^/]+/\.claude/',
        '~/.codex/',
        content
    )
    # Relative .claude/ references
    content = re.sub(r'(?<!\w)\.claude/', '.codex/', content)

    # Agent file references: .md → .agent.md (only for gsd-* agents)
    content = re.sub(
        r'(agents/gsd-[a-z-]+)\.md\b',
        r'\1.agent.md',
        content
    )

    return content


# ============================================================
# 3. Command prefix replacements
# ============================================================

def replace_command_prefixes(content):
    """Replace /gsd: and /gsd- command prefixes with $gsd-."""
    # /gsd:command-name → $gsd-command-name
    content = re.sub(r'/gsd:([a-z])', r'$gsd-\1', content)
    # /gsd-command-name → $gsd-command-name (but not in file paths)
    content = re.sub(r'(?<!/)/gsd-([a-z])', r'$gsd-\1', content)
    return content


# ============================================================
# 4. Task() → spawn_agent() replacement
# ============================================================

def replace_task_calls(content):
    """Replace Task() patterns with spawn_agent()."""
    # Task( → spawn_agent(
    content = re.sub(r'\bTask\s*\(', 'spawn_agent(', content)

    # subagent_type= → agent_name=
    content = re.sub(r'\bsubagent_type\s*[=:]\s*', 'agent_name=', content)

    # "Task tool" → "spawn_agent tool"
    content = re.sub(r'\bTask tool\b', 'spawn_agent tool', content)
    content = re.sub(r'`Task`', '`spawn_agent`', content)

    return content


# ============================================================
# 5. Platform name replacements
# ============================================================

def replace_platform_names(content):
    """Replace Claude Code references with Codex CLI."""
    content = content.replace('Claude Code', 'Codex CLI')
    content = content.replace('claude code', 'codex cli')
    # "for Claude" in platform context
    content = re.sub(r'for Claude(?!\s+(?:model|AI|LLM|Opus|Sonnet|Haiku))', 'for Codex', content)
    return content


# ============================================================
# 6. Codex-specific: commands/ → skills/ structure reference
# ============================================================

def replace_commands_to_skills(content):
    """Replace commands/gsd/ references with skills/gsd- for Codex."""
    content = re.sub(r'commands/gsd/([a-z-]+)\.md', r'skills/gsd-\1/SKILL.md', content)
    content = re.sub(r'\.codex/commands/', '.codex/skills/', content)
    return content


# ============================================================
# Main transform pipeline
# ============================================================

def transform_file(filepath):
    """Apply all transformations to a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()

    content = original

    # Apply in order (order matters!)
    content = replace_frontmatter_tools(content)
    content = replace_allowed_tools(content)

    # Simple tool replacements (non-ambiguous names)
    for pattern, replacement in TOOL_REPLACEMENTS:
        content = re.sub(pattern, replacement, content)

    # Context-aware tool replacements
    for pattern, replacement in CONTEXT_TOOL_REPLACEMENTS:
        if callable(replacement):
            content = re.sub(pattern, replacement, content)
        else:
            content = re.sub(pattern, replacement, content)

    content = replace_paths(content)
    content = replace_command_prefixes(content)
    content = replace_task_calls(content)
    content = replace_platform_names(content)
    content = replace_commands_to_skills(content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    """Transform all .md files in the repo."""
    changed = 0
    total = 0

    skip_dirs = {'.git', 'node_modules', '.github'}

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for fname in files:
            if not fname.endswith('.md') and not fname.endswith('.json'):
                continue
            # Skip package-lock.json
            if fname == 'package-lock.json':
                continue

            filepath = os.path.join(root, fname)
            total += 1

            try:
                if transform_file(filepath):
                    changed += 1
                    rel = os.path.relpath(filepath, REPO_ROOT)
                    print(f"  CHANGED: {rel}")
            except Exception as e:
                rel = os.path.relpath(filepath, REPO_ROOT)
                print(f"  ERROR: {rel}: {e}", file=sys.stderr)

    print(f"\nDone: {changed}/{total} files modified")


if __name__ == '__main__':
    main()
