SENT 25 Oct 2026 to jlmauro11@gmail.com, cc themaurogroup+kinvault@mail.grokbot.com, reply in the ETHKROS package thread (to Joe's 25 Oct 1:12 PM ET message). Approved by Jared. Folds in the "extra edge" reply drafted 24 Oct.

---

Joe,

Thanks for v2. For your AI, here are my answers on everything still open, plus the reply to your extra-edge ideas so it is all in one place.

1. LEVERAGE SUGGESTION

Fine with the onboarding questionnaire suggesting a 1x start and a 2x ceiling, labelled as a suggestion. Members still choose their own.

2. ALERT APPROVAL: TWO STREAMS INSTEAD

I cannot approve every alert by hand, so I'd separate two things:

- Signal feed (automated, no approval). Every confirmed signal goes out with that setup's odds, drawdown, sample size and any confluence, labelled as a computed signal, not a trade. Members read the statistics and make their own decision.
- Live trades (mine). Only the positions I actually take, logged automatically from my Coinbase account, with my leverage. These are the calls that carry my name.

That fits your tiers: Signal and Prime get the feed, Inner Table gets my live trades.

The feed can also give heads-ups before a signal confirms. A signal confirms a fixed number of candle closes after the low, so once a low has held for one or two closes we can post the chance it confirms and the setup's odds if it does, and update both at every close as confluence builds. Historically, a low that had held one close went on to confirm 51-69% of the time on ETH and 55-67% on BTC, depending on the chart; after two closes, 71-88% on ETH and 77-86% on BTC.

Why approval would not work: with the regime filter on, the signal fires about 160 times a year across both assets, roughly 3 a week. Since the filter turned on on 2 September there have been 22, 11 on ETH and 11 on BTC. By chart, per regime-on year: 1D about 40 ETH and 39 BTC, 2D about 19 each, 3D about 12-13 each, 5D about 7 each, 8D about 3-4 each.

3. LIVE CALLS INNER TABLE ONLY

Agreed, it matches the two streams above.

4. THE "BTC 3D + 2 OR MORE ETH CHARTS" ROWS

Rechecked under the same rules as the capabilities document. Both reproduce exactly.

- ETH 1D with a BTC 3D signal before and 2 or more other ETH charts already signalled: 79% (48 signals) against 48% without the BTC 3D signal (33). Ahead in both periods: 91% vs 62% in 2016-21, 69% vs 25% in 2022-26. It can go in.
- ETH 2D, same setup: 80% (20) against 64% (25), but in 2016-21 it trailed its without group (73% vs 79%), so it fails the both-periods rule. Leaving it out is right.

5. CALCULATOR

Nothing more needed. Wiring it to the drawdown figures by chart covers it.

6. WALKTHROUGH

Happy to go through the package together this week. Pick a time that works for you.

7. YOUR EXTRA-EDGE IDEAS

How each idea compares with what we have already tested, under the same rules (entry quality only, regime on, win = +20% within 60 days, both periods checked):

- Live cycle-length settings (Hilbert / Ehlers cycle period): not tested. The indicator uses fixed lengths; lengths that adapt to the measured cycle have not been tried. Worth testing.
- Ehlers super smoother on the stochastic RSI: not tested. Worth testing alongside the first.
- Phase-difference entry, one bar before the full cross: the signal is not a line cross; it is a confirmed low. The closest test was entering one or two bars before confirmation. One bar early, a third to a half of those entries were on lows that never confirmed (ETH 1D 31%, 2D 34%, 3D 36%, 5D 45%). Two bars early came out about the same as waiting. Entering earlier did not improve the odds. The heads-ups in section 2 give members that information without changing the entry.
- Funding, open interest and volume before entry: tested across funding level and direction, long/short ratio and open-interest change, alone and combined with the existing tags. None lifted the win rate without cutting most of the winning signals, and the open-interest read flipped direction between 2022-24 and 2024-26. One read held in both periods as a caution: funding below its 90-day median at entry ran 7 to 17 points worse, and it is reported with every signal. A volume spike at the low and money-flow levels both failed; volume rising into the confirmation was a near miss, not adopted.
- Weekly-chart agreement before a 2-day signal: covered by two filters in the capabilities document. Higher timeframe rising: ETH 2D 79% with it against 52% without (84% and 71% in the two periods). Same-asset agreement: ETH 2D 71% against 58%.
- Stepped, volatility-based exits: exits stay my judgement. Five mechanical exit rules were tested and all did worse than simply holding.
- Timing entries around funding resets: not tested. It affects the cost of holding, not the signal.

On your process: agreed that anything new gets backtested first. Every test is written down before it runs, split by chart and by period, and checked against the filters we already have. A variant that passes runs alongside the current setup as a logged, computed signal first; putting money on it comes after it has held up live. Next on our side: test the two Ehlers ideas and send the results.

As before, every figure here is entry quality only, a historical rate and not a return or forecast. No position has been taken on any signal to date.

Jared
