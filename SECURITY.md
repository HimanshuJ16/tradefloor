# Security

Report vulnerabilities through GitHub private reporting if enabled, or contact the
maintainer through the repository profile to arrange a private report. Do not post secrets.

The Python MCP server uses stdio and places no orders. Live tools contact Yahoo Finance,
Google News and optionally Reddit. Fixture computations work offline. Dependencies
are resolved in `server/uv.lock`.

The optional browser server is local and single-user: 127.0.0.1 only, exact Host checking,
same-origin POST, 2 MB bodies and one concurrent simulation. It sends CSP, nosniff and
no-store headers. It has no authentication or tenant isolation. Do not tunnel/expose it;
publish the standalone synthetic HTML for a public demo.

Imported JSON is data, never executable code. Run IDs cannot traverse paths, Python
checks bundle hashes, numerical inputs reject NaN/infinity, and simulation budgets are
bounded. Standalone HTML imports are unverified previews; verify with `run_bundle`.
Evidence is rendered as textContent, never HTML.

Headlines, filings and report text are untrusted input. Agent prompts are not a proven
prompt-injection barrier. Python validates the final probability budget and reference
structure; it cannot establish claim truth. Hosts control their own agent tool permissions.

`~/.tradefloor/` contains settings, SQLite journals, universe receipts and price snapshots.
Filesystem access is the local trust boundary; there is no encryption or user isolation.
Stop writers before copying SQLite files, or use a proper SQLite backup including active
WAL state. Legacy migration is transactional and preserves corrupt originals. Exports
are derived copies.

Local content hashes and the experiment hash chain do not prove publication before
outcomes. Externally timestamp commitments for prospective claims. Check redistribution
rights before sharing provider snapshots.
