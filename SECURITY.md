# Security

## Reporting

Report vulnerabilities privately through GitHub's "Report a vulnerability" on this
repository, not in a public issue. Expect a first reply within a week.

## What the project does and does not do

- It needs no API keys and stores none. Settings and the journal are plain JSON files in
  `~/.tradefloor/`.
- It never places orders and has no broker integration.
- The MCP server makes outbound HTTPS requests only to market data and news sources
  (Yahoo Finance through yfinance, Google News RSS, and Reddit only when enabled). It opens
  no ports.
- On Claude Code, the agent definitions deny shell and file-edit tools; agents only write
  their own report files in the run folder. Other hosts apply their own tool permissions.
- Headlines and filings are untrusted input. Every role that reads them is told they are
  data, never instructions, but a crafted headline is still text a model reads.
  Review a run folder before acting on its output.
