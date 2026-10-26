SENT 26 Oct 2026 ~01:21 UTC (25 Oct 21:21 ET), Gmail message 1a175cc38fe38718, approved by Jared.
To jlmauro11@gmail.com, cc themaurogroup+kinvault@mail.grokbot.com.
Source: analysis/joeideas.py, RESULTS_joeideas.txt, RESULTS_joeideas_extra.txt (25 Oct 2026).

---

Joe,

For your AI: results of testing the ideas from your F1 review. Same rules as the capabilities document: regime on, entry at the confirmation close, win = price reached +20% within 60 days, 2016-21 and 2022-26 checked separately, all ten charts (ETH and BTC, 1D to 8D). Each test and its pass rule were written down before it ran. Entry quality only; no position has been taken on any signal.

SUMMARY

Idea                                          Result                                   Verdict
1. Live cycle length (Ehlers dominant cycle)  Almost no change to the signals          Not adopted
2. Super smoother on the stochastic line      Tags no better, mostly worse             Not adopted
3a. Enter when the phase gap starts closing   Earlier, but many lows never confirm     Not adopted
3b. Enter on the full cross                   Later and pricier; mixed                 Not adopted
4. Funding / open interest / volume           Already tested 23 Oct                    Not adopted
5a. Weekly momentum rising                    No real lift                             Not adopted
5b. Weekly momentum above its signal line     Strong on ETH, not on BTC since 2022     Watch on ETH
6. Stepped volatility exits                   Exits stay discretionary                 Not tested
7. Timing entries around funding resets       Saves about 0.01% of position            Not worth it

1. LIVE CYCLE LENGTH

The momentum line and its stochastic used a length that changed every bar with the market's measured cycle (Ehlers' Hilbert-transform method), in two versions: half the cycle and the full cycle. The measured cycle ran 17 to 30 bars on every chart (10th to 90th percentile).

It barely changes anything. 90-100% of the adaptive signals land within 3 bars of today's, the signal count is within 3%, and win rates move by 0 to 3 points either way. Half-cycle was better in both periods on 3 of 10 charts, full-cycle on 1 of 10. The pass rule needed 7. Example: ETH 2D 63% against 62% today.

2. SUPER SMOOTHER ON THE STOCHASTIC

This does not change which lows become signals; it changes the tags the stochastic drives (prime dot and diamond). With a 3-bar smoother, the prime dot and diamond did better than today on 0 of 10 charts; with Ehlers' 10-bar default, on 2 and 1 of 10. The pass rule needed 6. Pooled by asset, the diamond got worse on both. Example: ETH 2D diamond 59% smoothed against 71% today.

3. PHASE-DIFFERENCE ENTRY

The two lines are the momentum line and its stochastic.

3a, enter when the gap between them starts closing: in practice one to two bars earlier than the confirmation. 29-44% of those entries were on lows that never confirmed, and the result was at least as good as waiting in both periods on only 1 of 10 charts; the rule needed 7. ETH 5D: 54% against 70% at confirmation.

3b, enter on the full cross (stochastic crossing up through momentum): 2 to 5 bars later than the confirmation. It skipped 23-42% of signals because no cross came within 15 bars, and paid more for the rest: about 1% more on 1D and 2D, 3.5-10% on 3D and 5D, 16-25% on 8D. It was at least as good in both periods on 5 of 10 charts (ETH 2D 68% against 62%); the rule needed 7. Not adopted.

4. FUNDING, OPEN INTEREST AND VOLUME

Not re-run; tested on 23 Oct and recorded as not adopted. None of the positioning reads lifted the win rate without cutting most of the winning signals. The one stable read, funding below its 90-day median at entry (7-17 points worse), is already reported with every signal as a caution.

5. WEEKLY AGREEMENT

Weekly bars, last weekly bar closed by the entry day, tested on 1D to 5D signals.

5a, weekly momentum rising: about +4 points on ETH and +2 on BTC pooled, and mostly negative once the existing higher-timeframe filter is accounted for. Not adopted.

5b, weekly momentum above its own signal line: a near miss.

Asset   With     Without   2016-21 with / without   2022-26 with / without   Touched -30%, with / without
ETH     70%      55%       81% / 63%                53% / 43%                18% / 33%
BTC     59%      46%       73% / 53%                36% / 36%                 8% / 19%

On ETH it held in both periods, roughly halved the share of signals that touched -30%, and added value whether the signal's own chart had momentum above its signal line (71% against 66%) or below it (67% against 47%). On BTC all of the gain was in 2016-21. It failed two parts of the rule: ahead in both periods on 4 of 8 charts (needed 6), and only +3 points for BTC when the higher timeframe was not rising (needed +5). Not adopted. We will log it next to every ETH signal and report how it does live. The result reproduced exactly from a second, independent source of weekly prices.

6. STEPPED, VOLATILITY-BASED EXITS

Not tested by design. Exits are my judgement; five mechanical exit rules were tested earlier and all did worse than simply holding.

7. TIMING ENTRIES AROUND FUNDING RESETS

Measured on the Binance USDT perpetuals (8-hour funding, the longest continuous record we hold), across 378 signal entries per asset since January 2020. Funding at entry was a median 0.010% per 8-hour interval. Holding a long for 60 days paid a median 1.66% of position size on ETH and 1.35% on BTC (90th percentile 6.4% and 5.0%). The most that timing an entry around a reset can save is one interval, about 0.01% of position, so it is not worth delaying an entry for.

WHAT CHANGES

Nothing in the setup changes. One item goes on forward watch: weekly momentum above its signal line, on ETH, logged alongside each signal as information, not as a filter. Funding cost over a typical hold could go into the member material as an education point.

Jared
