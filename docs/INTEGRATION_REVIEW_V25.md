# V25 — GitHub and cloud AI integration review (2026-10-16)

## Selected and implemented

| Module | Benefit | State and limits |
|---|---|---|
| Public document evidence lab | Review pasted KAP/news text with traceable excerpts | Working deterministic local extraction; no third-party request in local mode. User text is sent to the application's backend. |
| Anthropic Claude Messages adapter | Structured passage selection | Optional, server configuration and explicit per-request consent/access code required. No live provider credentials available during validation. |
| Google Gemini generateContent adapter | Alternative structured passage selection | Same restrictions. Provider/model support must be verified with the configured account. |
| Evidence validation | Discard invented quotations | Exact substring check, source offsets, SHA-256, UTC review date, JSON export. Does not establish source authenticity or completeness. Category is a heuristic/model judgment. |
| Restricted AI boundary | Reduce prompt injection and accidental data disclosure | No tools, arbitrary URL fetch, broker, portfolio data or file access. Fixed endpoints, strict schema, instruction heuristic blocks suspicious cloud inputs. Not a complete injection defense. |
| GitHub release integrity | Prevent obsolete builds replacing latest | Workflow concurrency, current-main check and SHA256SUMS.txt. Hashes detect transfer changes; they are not code signing. |
| Dependabot | Surface dependency updates | Weekly pip/npm/GitHub Actions PRs. No automatic merge. Requires GitHub's processing; adding config does not prove first scan completed. |

## Configuration

Default: cloud OFF. Do not embed credentials in installers or frontend assets.
Set environment variables on the backend host (or inherited environment when launching desktop):

- `BIST_CLOUD_ENABLED=1`
- `BIST_CLOUD_ACCESS_TOKEN`: a random secret of at least 24 characters; enter it only in the module's access-code field.
- Claude: `ANTHROPIC_API_KEY`, `BIST_CLAUDE_MODEL` (your account's supported structured-output model ID).
- Gemini: `GEMINI_API_KEY`, `BIST_GEMINI_MODEL` (supported model ID).

Restart the backend after configuration. Status means configured, not authenticated or tested. API keys are never returned to the browser. Text and access code are not persisted by this feature. Only the text is transmitted to the selected provider; source label stays on the backend. Provider data retention and billing terms still apply. Never paste private holdings or personal information. Standard deployment infrastructure can have its own request logging; review it separately.

Limits: 24,000 input characters, 3,000 maximum output tokens, four requests/minute, forty/rolling day per process (including failures), no retry/fallback. Counters reset on restart and are not shared across workers; set provider-side spending limits. Default OFF plus access token prevents anonymous use of your API balance. HTTPS should terminate at the hosting platform for remote use. Do not expose a desktop loopback backend externally.

## Investigated but not bundled

- **GitHub Models**: retired July 30, 2026; inference API is unavailable. Do not build a new dependency on its old Azure/GitHub endpoints. Copilot is a development assistant, not the app's market-data or inference API.
- **Microsoft Qlib**: quantitative ML research framework; candidate for an isolated experiment after BIST data adaptation, corporate actions, reproducibility and out-of-sample comparison. Installing it alone adds no validated trading edge.
- **vectorbt**: candidate for batch strategy experiments. Existing engine has next-open/cost/embargo assumptions; changing engines without parity tests would change historical results.
- **Ollama**: useful future on-device inference option. Runtime/model downloads, memory and platform testing need their own installer design. No silent model download or public local-model endpoint was added.
- **Pandera**: richer dataframe validation candidate. Current feature uses strict Pydantic API/output contracts without increasing runtime dependencies; dataframe-wide migration needs separate data-path work.
- Autonomous agents / arbitrary MCP plugins: not attached to execution, files or personal portfolios. The useful first scope is bounded document extraction with inspectable source evidence.

## Primary sources

- https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-July-30-2026/
- https://platform.claude.com/docs/en/api/messages/create
- https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- https://ai.google.dev/gemini-api/docs/generate-content/structured-output
- https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency
- https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference
- https://github.com/microsoft/qlib
- https://github.com/polakowo/vectorbt
- https://github.com/ollama/ollama
- https://github.com/unionai-oss/pandera
