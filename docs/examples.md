# Voice examples

All examples assume `--dry-run` prints the plan without touching AX.
Drop `--dry-run` on macOS to actually execute (destructive actions also
need `--yes`).

## Desktop control

```sh
uv run python -m mac_voice --text "open chrome" --dry-run
# 1. open_app {'app': 'chrome'}

uv run python -m mac_voice --text "open rancher" --dry-run
# 1. open_app {'app': 'rancher'}

uv run python -m mac_voice --text "go to vs code" --dry-run
# 1. focus_editor {'app': 'vscode'}

uv run python -m mac_voice --text "open chrome and open facebook in a tab" --dry-run
# 1. open_app {'app': 'chrome'}
# 2. open_url {'site': 'facebook', 'url': 'https://www.facebook.com', 'new_tab': True}
```

More desktop utterances:

| Say | Plan |
|-----|------|
| "open safari" | open_app safari |
| "open terminal" | open_app terminal |
| "open slack" | open_app slack |
| "open docker" | open_app docker |
| "quit slack" | quit_app slack [confirm] |
| "close window" | close_window [confirm] |
| "close tab" | close_tab [confirm] |
| "minimize" | minimize |
| "fullscreen" | fullscreen |
| "new window" | new_window |
| "volume up" / "louder" | volume_up |
| "volume down" / "quieter" | volume_down |
| "mute" | mute |
| "take a screenshot" | screenshot |

## Browser

```sh
uv run python -m mac_voice --text "open github in a tab" --dry-run
uv run python -m mac_voice --text "search for typesafe jev" --dry-run
uv run python -m mac_voice --text "new tab" --dry-run
uv run python -m mac_voice --text "next tab" --dry-run
uv run python -m mac_voice --text "previous tab" --dry-run
```

Known sites: facebook, github, gmail, youtube, google, twitter/x,
linkedin, stackoverflow, reddit, amazon, chatgpt. Any other domain like
"open example.com" routes as a raw URL. Free text like "search for cats"
routes to search_web with a Google URL.

## Voice coding

```sh
uv run python -m mac_voice --text "undo" --dry-run
# 1. editor_command {'command': 'undo'}

uv run python -m mac_voice --text "save" --dry-run
uv run python -m mac_voice --text "new line" --dry-run
uv run python -m mac_voice --text "in intellij type public static void main" --dry-run
# 1. focus_editor {'app': 'intellij'}
# 2. dictate {'text': 'public static void main'}
```

More coding utterances:

| Say | Plan |
|-----|------|
| "redo" | editor_command redo |
| "delete line" | editor_command delete_line |
| "select word" | editor_command select_word |
| "select line" | editor_command select_line |
| "go to line 42" | editor_command go_to_line with line 42 |
| "format code" | editor_command format |
| "comment line" | editor_command comment |
| "find" | editor_command find |
| "run" | editor_command run |
| "in vs code type hello world" | focus_editor vscode + dictate |
| "say build done" | say |
| "insert snippet main" | code_snippet main |

## Compound commands

"and", "then", and commas split one utterance into ordered steps:

- "open chrome and open gmail in a tab" gives open_app chrome, then open_url gmail in a new tab.
- "undo then save" gives two editor_command steps in order.
- "open chrome, open github" gives open_app chrome, then open_url github.
