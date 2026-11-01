# PR evidence: screenshots

A PR that changes what a page looks like carries before and after screenshots in its **Evidence** section.

## Capture

Use the project's Playwright MCP server (`.mcp.json`; tools `mcp__playwright__*`). It drives Microsoft Edge, which every Windows machine has, in a fresh profile each session. The plugin's own Playwright server (`mcp__plugin_playwright_playwright__*`) asks for Google Chrome, which this machine lacks, so it fails.

1. `browser_resize` to 1280×1000, the width the earlier evidence uses.
2. `browser_emulate_media` with `colorScheme: "light"`, then again with `"dark"`. Always set the scheme: the OS is in dark mode, so an unset scheme gives dark.
3. `browser_navigate` to the page with a fixed `?clock=` (2017-11-24 in the AIE-48 evidence), so before and after show the same day.
4. `browser_take_screenshot` with a `filename` straight into the evidence folder below.

Before shots come from the deployed app, which is `main`: the URL is in the latest CD run's log (`gh run view <id> --log | grep -o 'https://[^ ]*azurecontainerapps.io' | sort -u`). After shots come from your branch, run locally.

Fallback when the MCP server won't start: headless Edge from PowerShell, with one profile directory per scheme (`preferredColorScheme` 1 is light, 0 is dark).

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --hide-scrollbars `
  --user-data-dir=<scratch>\edge-light --window-size=1280,1000 --virtual-time-budget=15000 `
  --blink-settings=preferredColorScheme=1 --screenshot=<file>.png <url>
```

Headless capture can catch Recharts mid-animation, so bars may be missing. Say so in the PR rather than retaking until they appear.

## Store

Commit the images under `docs/evidence/<issue>/` (e.g. `docs/evidence/aie-48/`), in their own commit. They stay outside `app/`, the Docker build context, so they never deploy. Name them `before-<page>.png` and `after-<page>-<light|dark>.png`.

Screenshots stay in the repo. Uploading them to Linear or anywhere else sends files to a third party, and those links don't render on GitHub.

## Embed

Link each image by the raw URL of the commit that added it, so it renders in the PR and survives the branch being deleted:

```markdown
![Orders after, dark](https://github.com/JoshChima/olist_agent/raw/<sha>/docs/evidence/aie-48/after-orders-dark.png)
```

A table with one row per page and before, light and dark columns reads best. [JoshChima/olist_agent#25](https://github.com/JoshChima/olist_agent/pull/25) is the worked example.
