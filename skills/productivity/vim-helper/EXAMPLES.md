# Vim Helper Examples

## Motion

````md
**Delete Inside Quotes**

Neovim:
- `di"`

Zed:
- `di"`

Both should behave the same.

Vault: saved under `Vim > Editing > Delete inside quotes`.
````

## Plugin Needed

````md
**Surround Text**

Neovim:
- Not present in your config unless a surround plugin is installed.
- Add `nvim-surround` in `~/.config/nvim/lua/custom/plugins/init.lua`.

```lua
{
  'kylechui/nvim-surround',
  version = '*',
  event = 'VeryLazy',
  opts = {},
}
```

Then use `ysiw"`.

Zed:
- Check whether Zed Vim mode supports the same surround command before claiming parity.

Vault: saved under `Vim > Editing > Surround text`.
````

## Difference And Alignment

````md
**Find File**

Neovim:
- `<leader>sf`

Zed:
- `ctrl-t`

**Difference**
Neovim uses the Kickstart leader picker style. Zed uses the local `ctrl-t` binding.

**Optional Alignment**
To make Zed closer to Neovim, add this to `~/.config/zed/keymap.json`:

```json
{
  "context": "Workspace",
  "bindings": {
    "space s f": "file_finder::Toggle"
  }
}
```

Vault: saved under `Vim > Navigation > Find file`.
````
