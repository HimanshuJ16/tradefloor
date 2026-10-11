# Data policy

MIT licenses Tradefloor's code. Dependencies have their own licenses. Retrieved market
prices, news and filings do not become MIT licensed when included in a run bundle.

The default live source is unofficial Yahoo access through yfinance. The
[yfinance project](https://github.com/ranaroussi/yfinance) describes research/educational
use and directs users to Yahoo's terms. Obtain the appropriate vendor/rights-holder
permissions before commercial use or redistribution. This project grants neither.

Public browser fixtures and standalone exports are synthetic, from fixed seeds. They
contain no Yahoo history, scraped headlines or real company claims. User and provider
snapshots are local by default: inspect `inputs` and its rights metadata before sharing.

| Historical requirement | Current behavior |
|---|---|
| No future feature rows | Cutoff truncation; forming bars excluded |
| Actual historical availability | Refreshed adjusted Yahoo history, not a vintage archive |
| Historical universe | Receipts captured before cutoff, otherwise current-selection warning |
| News/earnings availability | Historical current-RSS excluded by agents; earnings boosts disabled |
| Corporate-action settlement | Adjusted daily history rebased to frozen reference price |
| Venue schedule | exchange_calendars with explicit proxies/coverage; verify exceptional sessions |

Current-universe scans have selection bias. Synthetic settlements and manually supplied
outcomes are not prospective market performance. Intraday retention is limited; archive
data locally with permission before the evaluation horizon exceeds provider retention.

No third-party simulator code was copied. TradingAgents and MiroFish are conceptual
inspirations. Importing source from either requires a separate license review; MiroFish
source cannot simply be relabeled MIT.
