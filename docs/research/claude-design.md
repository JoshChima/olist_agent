# Claude Design: inputs and outputs (as of 2026-10-31)

## Summary

- Claude Design (launched 2026-04-17 by Anthropic Labs) now runs inside any Claude conversation as the "Design" artifact template; the standalone claude.ai/design site goes read-only after 2026-12-14.
- Inputs: text prompts; uploads (images, DOCX/PPTX/XLSX, PDFs, logos, fonts, slide decks); screenshots and wireframes; live-site element capture; Figma files (when building a design system); a linked or uploaded code repo / GitHub repo; a local codebase via `/design-sync` in Claude Code.
- Outputs: PDF, PPTX, Google Slides, standalone HTML, .zip archive, PNG/PDF per artboard (from `/design`); a "handoff bundle" sent to a local coding agent or Claude Code on the web; connectors to Adobe, Canva, Miro, Lovable, Replit, v0, Vercel, Wix, Netlify, Gamma.
- Reusable design systems exist: created by chatting with Claude (brand assets, Figma, decks), by `/design-sync` from a React repo, or by migrating from standalone; managed in Settings > Design Systems; published / set as default / locked by admins; edited via "Remix"; each is an artifact usable in any chat including Claude Code.
- Documented Claude Code bridge: `/design-sync` (repo -> design system), `/design` (draft / import / export designs from Claude Code), and "Handoff to Claude Code" from a design. Bundle contents and output code format (React / Tailwind / shadcn) are not documented in primary sources; no Figma export is documented.

## 1. Inputs

- Design systems: "Bring in one or several design systems from a GitHub repo, design files, raw uploads, or your local codebase using the /design-sync command in Claude Code." https://support.claude.com/en/articles/14604416-get-started-with-claude-design
- Codebase: you can link a code repository so Claude understands existing components and styling; linking very large repositories from Claude Code avoids lag. https://support.claude.com/en/articles/14604416-get-started-with-claude-design
- Code-based design system: "If your design system lives in code, like a React component library, link or upload the repository." https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design
- Figma, connected apps, uploads (for design systems): "Ask Claude to build a design system from your connected apps, uploaded files, Figma files, decks, logos, and fonts." https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design
- Screenshots and existing design files: "Prototypes: Screenshots, web flows, and existing design files." https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design
- Visual references for a design: screenshots, images, wireframes, existing assets, or an existing deck/document whose style you want replicated. https://support.claude.com/en/articles/14604416-get-started-with-claude-design
- Document uploads: "Import from your codebase, or DOCX, PPTX, and XLSX files." https://claude.com/product/design
- Live site: a web capture tool grabs elements from a live site so "prototypes look like the real product" (launch post). https://www.anthropic.com/news/claude-design-anthropic-labs
- Onboarding: "Claude builds a design system for your team by reading your codebase and design files." https://www.anthropic.com/news/claude-design-anthropic-labs
- `/design-sync [hint]`: "Convert your repo's React design system and upload it to Claude Design, so designs it produces use your real components." A first sync "can take a few hours on a large repo". https://code.claude.com/docs/en/commands
- Unconfirmed: a standalone design-tokens file (JSON / CSS variables) as a first-class import; only "design files" and "raw uploads" are named. Unconfirmed: pasting a plain URL of an existing site as a design source (only the web capture tool is described).

## 2. Outputs

- Export menu on a project: Download as .zip, Export as PDF, Export as PPTX, Export to Google Slides, Export as standalone HTML. https://support.claude.com/en/articles/14604416-get-started-with-claude-design
- Handoff to Claude Code has two options: send to a local coding agent, or send to Claude Code Web. https://support.claude.com/en/articles/14604416-get-started-with-claude-design
- "Claude packages everything into a handoff bundle that you can pass to Claude Code with a single instruction." https://www.anthropic.com/news/claude-design-anthropic-labs
- "Export to PPTX, PDF, or HTML, hand off to Claude Code, or send to the apps you already use daily." https://claude.com/product/design
- Connectors: "Claude Design connects with Adobe, Canva, Gamma, Lovable, Miro, Replit, Vercel, and Wix." https://claude.com/product/design (the support article also lists Netlify and v0: https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- Admin guide: exports to "HTML bundles, PPTX, PDF, and Google Slides"; handoff to engineering by "exporting design intent for use with Claude Code". https://support.claude.com/en/articles/14604406-claude-design-admin-guide-for-team-and-enterprise-plans
- Every artifact gets a link, private by default; share as view / comment / edit. https://claude.com/product/design and https://support.claude.com/en/articles/14604416-get-started-with-claude-design
- In Claude Code, `/design` canvases: "You can export each artboard as PNG or PDF." https://code.claude.com/docs/en/artifacts
- Project archive: individual projects export as a .zip from "Share". https://support.claude.com/en/articles/17440474
- Unconfirmed: that the handoff bundle or any export is React, Tailwind, or shadcn/ui code. Primary sources say "HTML bundles" and "design intent" only; third-party claims of Tailwind-token component trees are not verified.
- Unconfirmed / not offered: Figma export. No primary source lists Figma as an export target.

## 3. Reusable design systems

- Three creation paths: chat ("Ask Claude to build a design system from your connected apps, uploaded files, Figma files, decks, logos, and fonts"), Claude Code ("If your design system already exists as React components, run /design-sync in Claude Code"), or migrate from standalone. https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design
- Contents: a design system "captures your colors, typography, components, and layout patterns"; migrated ones have a "guide, tokens, and components" that Claude can tidy ("Let Claude clean it up"). https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design and https://claude.com/product/design
- Management: "which you can manage in Settings > Design Systems." https://claude.com/product/design
- Publish: "When you're happy with the design system, turn on the 'Published' toggle." Projects created from the Claude Design home screen then use it. https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design
- Edit: "Click the 'Remix' button in the upper right corner to open the chat interface" and edit through chat. https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design
- Sharing scope: "all projects created within that organization automatically use it"; organizations may keep multiple systems (per brand or sub-team); admins can restrict publish / default / delete and "lock a team to a single approved design system". https://support.claude.com/en/articles/14604406-claude-design-admin-guide-for-team-and-enterprise-plans and https://claude.com/product/design
- Portability: "Each design system becomes an artifact Claude can use in any conversation, including in Claude Code." https://claude.com/product/design
- Migration keeps owner and sharing; empty or starter-theme systems are not moved; a moved system "can't be edited on its page yet" but editors can ask Claude to change it. https://support.claude.com/en/articles/17440474
- Plan availability: beta on Pro, Max, Ultra, Team, Enterprise; off on Enterprise until enabled under Organization settings > Artifacts. https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design
- Claude Code side: the built-in design skill "looks for an existing design system in your project" (e.g., tokens in CLAUDE.md or a theme file) and treats it as higher precedence than its own choices. https://code.claude.com/docs/en/artifacts

## 4. Design in Claude Design, implement in Claude Code

- "From Claude Code, use /design to import a design into your codebase, export your code as a live prototype, or let Claude build the whole thing from start to finish." https://support.claude.com/en/articles/14604416-get-started-with-claude-design
- "Pull in your design system from Claude Code using /design-sync or work directly in Claude Code with /design." https://claude.com/product/design
- Handoff: "hand it off to Claude Code, which continues from your existing work instead of starting over from a screenshot." https://claude.com/blog/claude-design-stays-on-brand-for-daily-work
- `/design [brief]` drafts artboards "published as a Claude Design artifact"; requires Claude Code v2.1.265+, artifacts enabled, and the Design template on. `/design consent` / `/design revoke` grant or withdraw Claude's access to Claude Design; `/design-login` authorizes `/design-sync`. https://code.claude.com/docs/en/commands
- A design artifact's URL can be given to Claude Code in another session ("Update https://claude.ai/code/artifact/..."), or attached from `/artifacts`; Claude reads shared artifacts and saves the full source locally. https://code.claude.com/docs/en/artifacts
- Changelog: `/design-sync` upload prompt shows the folder, project and files it will upload or delete (v2.1.314); notice that standalone closes 2026-12-14 (v2.1.302). https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- Standalone deadline: "The standalone site at claude.ai/design stays open until December 14, 2026." https://claude.com/product/design
- Unconfirmed: a dedicated "DesignSync" tool name beyond the `/design-sync` command; the exact file layout Claude Code writes when importing a design; whether `/design-sync` targets the in-Claude design systems or only the standalone site (the commands doc says it "uploads to the standalone claude.ai/design site").
