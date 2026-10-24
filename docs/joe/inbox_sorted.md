# Joe — inbox sorted

Sorted 24 Oct 2026. Covers everything from Joe (jlmauro11@gmail.com,
joseph@themaurogroup.com) received 21–24 Oct. Repeats and revised versions
are merged under one item, latest version first. Everything older than
21 Oct is answered or closed.

## Needs something from Jared

### 1. Coinbase read-only key: reissue (22 Oct, 2 emails)

| Sent | What changed |
|---|---|
| 22 Oct 12:37 UTC | **Latest.** Gives the allowlist IP: `67.191.123.90` (his Mac Studio, Comcast home line, may change after a modem reboot) |
| 22 Oct 12:36 UTC | First version. Same request, IP left as a placeholder "[IP ADDRESS]" |

He says the CoinStats key works and pulls the Aave side. The 4 Oct Coinbase
key never reached his side. He wants a fresh view-only key.

**Not answered yet.** Jared creates the key in Coinbase himself. The thread
CCs his Grok bot, so the key goes in a separate email.

### 2. ETHKROS package and pitch (24 Oct, 3 emails)

| Sent (UTC) | Subject | What it has |
|---|---|---|
| 10:33 | ETHKROS: full package for review | **The main one.** Combined PDF (pitch deck repositioned as a private VIP club, business plan, marketing strategy), financial model `ETHKROS_VIP_Model.xlsx`, HTML deck with website and trading pages |
| 13:12 | ETHKROS preview (enlarged) for your review | `ETHKROS_Previews.pdf` |
| 13:12 | ETHKROS preview (enlarged) – HTML slideshow | `ETHKROS_Previews.html`, the same preview as an HTML file because it was too big to go with the PDF. Arrow keys flip pages, F for full screen |

The two previews are one item in two formats.

**Asks:** go over the package with him today. He wants it "in flight in the
next two weeks."

### 3. Test website (24 Oct, 4 emails)

| Sent (UTC) | Subject | What changed |
|---|---|---|
| 13:31 | ETHKROS site, no password needed now | **Latest.** Password removed; just open the link |
| 13:30 | ETHKROS site updated, please review this version | Final "ETHKROS" spelling throughout; dashboards and alert samples refreshed. The address still says "ethcross" because it is a temporary test URL |
| 13:29 | ETHKROS site to review | Same link; "throw it through Claude and send me your feedback" |
| 13:27 | ETH Cross test site, live for your walkthrough | **The detailed one.** Full feature list (below), plus a password that no longer applies |

Link: `https://ethcross-test-b718d9ca.netlify.app`. Everything on it is test
or sample data.

What the 13:27 email says is on the site:

| Page | Content |
|---|---|
| Home | Overview of tiers and tools |
| Pitch | Leverage suggested per member from a questionnaire: 1x default, hard cap 2x, "liquidation is not an option" |
| Free / public tier | Delayed calls, hashed record, weekly recap, methodology notes, misses and corrections kept on record |
| Signal — $249/mo or annual | VIP entry signals, live alerts on all timeframes tagged with entry, invalidation and leverage band, weekly report and archive, Telegram and Discord alerts, bi-weekly AMA |
| Prime — $799/mo, by application | Signal plus a monthly session; demo application form |
| Onboarding questionnaire | 6 questions that suggest a starting leverage |
| Position-size and liquidation calculator | **Waiting on Jared's stats:** "your average pullback from entry and median drawdown" |
| Member dashboards, alert samples | One per tier; email, Telegram and Discord samples |

Tier pricing is not the same across the emails. The 10:33 package email
describes a $2,500/month "Inner Table" where members "see our live trades
and can follow-trade them". The 13:27 site email lists Signal $249 and
Prime $799 and does not mention the Inner Table.

**Asks:** walk through the site (he'll be on it at the same time), send
notes as you go, and send the two drawdown figures for the calculator.

### 4. ETH Cross: ideas to scrape a little extra edge (24 Oct 13:12, 1 email)

He ran a review asking whether wave or physics math could add an edge.

**Ask:** "feed this to Claude and send me how it compares with your current
setup."

The ideas, next to what the repo already has on each:

| His idea | Already in the repo |
|---|---|
| Live cycle-length settings (Hilbert / Ehlers cycle period sets the RSI and stoch lengths) | Not tested |
| Ehlers super smoother on the stochastic RSI | Not tested |
| Phase-difference entry, about one bar before a full cross | Closest test: `analysis/confirmlag.py` (23 Oct), buying 1 or 2 bars before confirmation |
| Funding, open interest and volume check before entry; size down when pressure is extreme | `analysis/derivtest.py` (23 Oct): on the failed list in PRETRADE. Funding below its 90-day median is kept as a caution read (`posread.py`) |
| Weekly-chart agreement before taking a 2-day signal | Cross-timeframe agreement, PRETRADE §5 |
| Stepped, volatility-based exits | Exits are discretionary, settled. Five mechanical exit rules tested, all lost to holding |
| Timing entries around funding resets | Not tested; a cost question, not entry quality |

His proposed process: anything both sides confirm gets backtested, runs on a
percentage of assets beside the current setup, and is only migrated once it
proves better.

### 5. ETHKROS Carry Trade LTV model (24 Oct 15:16, 1 email)

Attachment `ETHKROS_Carry_Trade_LTV.html`. He says this version resets loan-to-value
to 30% once a year, stops at year 20, runs on "the forecast-median BTC path
from your write-up", buys at an 80/20 BTC/ETH split, and is laid out in
five-year sections with no flat-price columns.

**Ask:** "I'd like you to take it over the finish line."

The write-up it refers to ("Your Bitcoin Leveraged", sent 20 Oct) carries two
BTC paths: a central trend estimate of about $236k for end-2030, and the
forecast median from published research of $467k, which the write-up labels
bull-biased.

## No action needed (acknowledgements)

| Date | Thread | What he said |
|---|---|---|
| 22 Oct | Intro to Unchained | Joe declined the rescheduled intro ("still deciding whether Unchained is the right fit"). Matt from Unchained replied asking if he can answer questions. You were CC'd |
| 21 Oct | Stablecoin rules finalized | Thanks; asks to be kept posted when the OCC application process and the AML rules come out |
| 21 Oct | Where both charts sit | Agreed on staying flat; watching whether ETH holds $2,408 on the weekly close and whether the 25 and 28 Oct signals confirm |
| 21 Oct | The Coinbase record for the 4.669 BTC | His goal: confirm the $1M loan proceeds are accounted for, and track the assets going forward through the read-only key. Superseded by item 1 |
| 21 Oct | Old ETH wallet with 1.36 ETH | He'll look for the seed phrase and do the restore with you in person |
| 21 Oct | Your Bitcoin Leveraged | Having it reviewed; will come back with questions |

On 24 Oct 14:19 UTC you forwarded his 21 Oct "Your Bitcoin Leveraged" reply
back to him with no note added.

## Attachments not opened

The Gmail connection here can read message text but cannot download
attachments, so none of the PDF, XLSX or HTML files above have been opened.
To review them, attach them in chat.
