"""Closed catalogs of apps, sites, editor commands, and actions.

The brain may only ever select from these catalogs. Nothing outside
this file can become an executed action.
"""

from __future__ import annotations

APPS: dict[str, dict] = {
    "chrome": {"names": ["chrome", "google chrome"], "process": "Google Chrome"},
    "safari": {"names": ["safari"], "process": "Safari"},
    "firefox": {"names": ["firefox", "mozilla firefox"], "process": "Firefox"},
    "arc": {"names": ["arc"], "process": "Arc"},
    "vscode": {
        "names": ["vs code", "vscode", "visual studio code", "code"],
        "process": "Code",
        "editor": True,
    },
    "intellij": {
        "names": ["intellij", "intellij idea", "idea", "intellij idea ultimate"],
        "process": "IntelliJ IDEA",
        "editor": True,
    },
    "cursor": {"names": ["cursor"], "process": "Cursor", "editor": True},
    "xcode": {"names": ["xcode"], "process": "Xcode", "editor": True},
    "android_studio": {
        "names": ["android studio"],
        "process": "Android Studio",
        "editor": True,
    },
    "terminal": {"names": ["terminal"], "process": "Terminal"},
    "iterm2": {"names": ["iterm", "iterm2", "iterm 2"], "process": "iTerm2"},
    "finder": {"names": ["finder"], "process": "Finder"},
    "slack": {"names": ["slack"], "process": "Slack"},
    "rancher": {
        "names": ["rancher", "rancher desktop"],
        "process": "Rancher Desktop",
    },
    "docker": {"names": ["docker", "docker desktop"], "process": "Docker Desktop"},
    "mail": {"names": ["mail", "apple mail"], "process": "Mail"},
    "notes": {"names": ["notes", "apple notes"], "process": "Notes"},
    "calendar": {"names": ["calendar"], "process": "Calendar"},
    "music": {"names": ["music", "apple music"], "process": "Music"},
    "photos": {"names": ["photos"], "process": "Photos"},
    "spotify": {"names": ["spotify"], "process": "Spotify"},
    "zoom": {"names": ["zoom"], "process": "zoom.us"},
    "discord": {"names": ["discord"], "process": "Discord"},
    "notion": {"names": ["notion"], "process": "Notion"},
    "obsidian": {"names": ["obsidian"], "process": "Obsidian"},
    "postman": {"names": ["postman"], "process": "Postman"},
    "figma": {"names": ["figma"], "process": "Figma"},
}

SITES: dict[str, dict] = {
    "facebook": {"names": ["facebook", "fb"], "url": "https://www.facebook.com"},
    "github": {"names": ["github", "git hub"], "url": "https://github.com"},
    "gmail": {"names": ["gmail", "google mail"], "url": "https://mail.google.com"},
    "youtube": {"names": ["youtube", "you tube"], "url": "https://www.youtube.com"},
    "google": {"names": ["google"], "url": "https://www.google.com"},
    "twitter": {
        "names": ["twitter", "x", "x dot com", "twitter x"],
        "url": "https://x.com",
    },
    "linkedin": {"names": ["linkedin", "linked in"], "url": "https://www.linkedin.com"},
    "stackoverflow": {
        "names": ["stackoverflow", "stack overflow"],
        "url": "https://stackoverflow.com",
    },
    "reddit": {"names": ["reddit"], "url": "https://www.reddit.com"},
    "amazon": {"names": ["amazon"], "url": "https://www.amazon.com"},
    "chatgpt": {"names": ["chatgpt", "chat gpt"], "url": "https://chat.openai.com"},
}

EDITOR_COMMANDS: dict[str, dict] = {
    "undo": {"phrases": ["undo"], "keys": "Cmd+Z"},
    "redo": {"phrases": ["redo"], "keys": "Cmd+Shift+Z"},
    "save": {"phrases": ["save"], "keys": "Cmd+S"},
    "new_line": {"phrases": ["new line"], "keys": "Enter"},
    "delete_line": {"phrases": ["delete line"], "keys": "Cmd+Shift+K or Ctrl+Shift+K"},
    "select_word": {"phrases": ["select word"], "keys": "Cmd+D or Alt+Up"},
    "select_line": {"phrases": ["select line"], "keys": "Cmd+L"},
    "go_to_line": {"phrases": ["go to line"], "keys": "Cmd+G or Ctrl+G"},
    "format": {"phrases": ["format", "format code"], "keys": "Alt+Shift+F or Cmd+Alt+L"},
    "comment": {"phrases": ["comment", "comment line"], "keys": "Cmd+/"},
    "find": {"phrases": ["find"], "keys": "Cmd+F"},
    "replace": {"phrases": ["replace"], "keys": "Cmd+Alt+F or Cmd+H"},
    "run": {"phrases": ["run"], "keys": "Ctrl+R or Shift+F10"},
    "debug": {"phrases": ["debug"], "keys": "Ctrl+D or Shift+F9"},
    "copy": {"phrases": ["copy"], "keys": "Cmd+C"},
    "paste": {"phrases": ["paste"], "keys": "Cmd+V"},
    "cut": {"phrases": ["cut"], "keys": "Cmd+X"},
}

ACTIONS: tuple[str, ...] = (
    "open_app",
    "activate_app",
    "quit_app",
    "new_window",
    "close_window",
    "minimize",
    "fullscreen",
    "open_url",
    "new_tab",
    "close_tab",
    "next_tab",
    "prev_tab",
    "search_web",
    "focus_editor",
    "dictate",
    "editor_command",
    "code_snippet",
    "volume_up",
    "volume_down",
    "mute",
    "screenshot",
    "say",
)

DESTRUCTIVE_ACTIONS: frozenset[str] = frozenset(
    {"quit_app", "close_window", "close_tab"}
)

SNIPPETS: dict[str, str] = {
    "class": "class {name}:\n    pass",
    "function": "def {name}():\n    pass",
    "if": "if {cond}:\n    pass",
    "if_else": "if {cond}:\n    pass\nelse:\n    pass",
    "for": "for {item} in {items}:\n    pass",
    "main": 'if __name__ == "__main__":\n    main()',
}
