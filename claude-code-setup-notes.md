# Claude Code Setup — forensiair

Setup log from getting Claude Code running on this project (Windows/PowerShell).

## What's done

- **Claude Code installed** via `irm https://claude.ai/install.ps1 | iex` (native build, currently v2.1.226+)
- **PATH issue fixed** — installer adds `claude` to PATH but existing terminal sessions don't see it until a full restart. Temporary per-session fix if needed:
  ```powershell
  $env:PATH += ";$env:USERPROFILE\.local\bin"
  ```
- **Postgres MCP server connected**, registered as `project-db`:
  ```powershell
  claude mcp add --transport stdio project-db -- npx -y @modelcontextprotocol/server-postgres postgresql://localhost:5432/forensiair
  ```
  (Update the connection string with real username/password if the local Postgres instance requires auth — format: `postgresql://USER:PASS@localhost:5432/forensiair`.)
- **GitHub CLI (`gh`) installed** via `winget install --id GitHub.cli`, authenticated via `gh auth login` (device code flow, signed in as `bgauri05`).

## Next steps

1. Open a terminal in this project folder, run `claude`.
2. Run `/init` inside Claude Code — scans the repo and generates a `CLAUDE.md` with project conventions/build/test commands.
3. From there, just describe tasks in plain English (fix a bug, add a feature, explain a file, etc.).

## Useful commands

- `/init` — generate CLAUDE.md
- `/clear` — reset conversation
- `/compact` — summarize/shrink context on long sessions
- `/permissions` — configure what needs approval before Claude acts
- `claude mcp add / remove / list` — manage MCP server connections (e.g. the Postgres one above)
