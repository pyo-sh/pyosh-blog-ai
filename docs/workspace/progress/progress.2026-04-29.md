# Progress 2026-04-29

## Root workspace cleanup - remove tracker/orchestrator tooling, preserve docs log

Removed deprecated root-repo skills and Figma MCP setup first, then removed the remaining runtime tooling for the old orchestration stack: `tools/agent-tracker/` and `tools/orchctl/`.

### Changes

- Deleted root skills: `brainstorming`, `frontend-design`, `subagent-creator`, `writing-plans`, `dev-orchestrator`
- Deleted Figma MCP setup and docs: `.mcp.json`, `mcp/figma-console/`, `mcp/figma-remote/`
- Deleted runtime tooling: `tools/agent-tracker/`, `tools/orchctl/`
- Updated `tools/docker/Dockerfile` to remove the build-time `tools/agent-tracker/setup.sh` dependency so Docker image builds do not fail after deletion

### Notes

- Historical records under `docs/` were intentionally preserved; future lookup should rely on git history and `/dev-log`
- Active documentation still needs a follow-up pass for references to removed tracker/orchestrator tooling (for example `README.md`, `tools/ARCHITECTURE.md`)
- This cleanup was not tied to a GitHub Issue
