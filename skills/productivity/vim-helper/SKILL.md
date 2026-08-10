---
name: vim-helper
description: Gives terse, pragmatic Vim, Neovim, and Zed Vim-mode answers and stores reusable answers in the user's Obsidian vault. Use when the user asks for Vim motions, text objects, commands, mappings, Neovim setup, Zed Vim-mode behavior, editor alignment, or quick Vim tips.
---

# Vim Helper

## Purpose

Answer Vim questions quickly, using the user's real Neovim and Zed setup as the source of truth.

## Sources Of Truth

- Neovim config: `~/.config/nvim`
  - LazyVim is tracked directly in dotfiles, not as a Kickstart submodule.
  - Check `init.lua`, `lua/config/*.lua`, `lua/plugins/*.lua`, `lazyvim.json`, and `lazy-lock.json`.
- Zed config:
  - `~/.config/zed/settings.json`
  - `~/.config/zed/keymap.json`
- Vault note: `30 Resources/Editor/Vim.md` in the user's chosen Obsidian vault.
  Resolve the vault from the user or active Obsidian context before the first
  write; do not guess when multiple vaults are available.

## Answer Style

Keep answers short, clean, and immediately usable. Prefer the direct keystroke or command first.

Default shape:

```md
**Thing The User Asked For**

Neovim:
- `command`

Zed:
- `command`

**Difference**
Only include when behavior differs.

**Setup**
Only include when config or plugin changes are needed.

**Optional Alignment**
Only include when Neovim and Zed differ and alignment is sensible.

Vault: saved under `Vim > Section > Heading`.
```

## Rules

- Include both Neovim and Zed by default for motions, commands, and editor workflows.
- If the user explicitly names one editor, answer that editor first and mention the other only if relevant.
- Before recommending a Neovim plugin, inspect the user's config and `lazy-lock.json`.
- Before recommending Zed bindings, inspect `settings.json` and `keymap.json`.
- If setup is needed, show the exact local file and minimal snippet.
- Do not edit Neovim or Zed config unless the user explicitly asks.
- Store reusable answers automatically in the vault note.
- Do not store one-off troubleshooting unless the user asks.
- If Neovim and Zed differ, store both in the vault.
- If an alignment change is sensible, include it under `Optional Alignment`, not in the quick answer.

## Vault Format

Use one consolidated note: `30 Resources/Editor/Vim.md`. Create the folder if needed.

Use searchable headings:

```md
# Vim
## Motions
### Delete inside quotes
## Editing
### Surround text
## Navigation
### Find file
## Setup
### Add a Neovim plugin
## Zed Vim Mode
### File finder binding
```

For differences, prefer compact tables:

```md
### Find file

| Target | Command | Notes |
|---|---:|---|
| Neovim | `<leader>sf` | Kickstart/Telescope style |
| Zed | `ctrl-t` | Local Zed keymap |
```

## Examples

See [EXAMPLES.md](EXAMPLES.md).
