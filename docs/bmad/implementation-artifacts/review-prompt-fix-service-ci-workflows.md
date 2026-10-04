# Blind Hunter prompt — fix service CI workflows

Conduct a review of CONTENT.
Look for what's missing, not only what's wrong.
Compute your finding floor N from the size of the changes: N = min(floor(sqrt(kB) + 1), 10), where kB is the changed content's size in kilobytes. State the arithmetic in one line, then find at least N issues to fix or improve.
Output a Markdown list of findings only — no severity, priority, or ranking.

CONTENT:
The changed files are `fkit-bi-analytics/.github/workflows/ci.yml`, `fkit-bi-generator/.github/workflows/ci.yml`, and `fkit-bi-web/.github/workflows/ci.yml`. Inspect them directly before reviewing.

Do not invoke any skill, and do not spawn subagents of your own. Return findings as text.
