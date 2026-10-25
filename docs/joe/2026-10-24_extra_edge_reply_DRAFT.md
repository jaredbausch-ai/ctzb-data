DRAFT, not sent. Reply to Joe's 24 Oct "ETH Cross: ideas to scrape a little extra edge".
To jlmauro11@gmail.com, cc themaurogroup+kinvault@mail.grokbot.com.

---

Joe,

For your AI: how each idea from the review compares with what we have already tested. Same rules as the capabilities document: entry quality only, regime on, win = +20% within 60 days, both periods checked.

1. Live cycle-length settings (Hilbert / Ehlers cycle period). Not tested. The indicator uses fixed lengths; lengths that adapt to the measured cycle have not been tried. Worth testing.

2. Ehlers super smoother on the stochastic RSI. Not tested. Worth testing alongside 1.

3. Phase-difference entry, one bar before the full cross. The signal is not a line cross; it is a confirmed low, and the alert fires when the low confirms. The closest test is entering one or two bars before confirmation (23 Oct). One bar early, a third to a half of those entries were on lows that never confirmed (ETH 1D 31%, 2D 34%, 3D 36%, 5D 45%). Two bars early came out about the same as waiting. Entering earlier did not improve the odds.

4. Funding, open interest and volume before entry. Tested 23 Oct across funding level and direction, long/short ratio and open-interest change, alone and combined with the existing tags. None of them lifted the win rate without cutting most of the winning signals, and the open-interest read flipped direction between 2022-24 and 2024-26. One read held in both periods as a caution: funding below its 90-day median at entry ran 7 to 17 points worse. That is reported with every signal. Volume: a volume spike at the low and money-flow levels both failed; volume rising into the confirmation was a near miss (+7 and +15 points in the two periods), not adopted.

5. Weekly-chart agreement before a 2-day signal. Covered by two filters in the capabilities document. Higher timeframe rising (the 8-day chart turning up at entry): ETH 2D 79% with it against 52% without, 84% and 71% in the two periods. Same-asset agreement (two or more other ETH charts already signalled): ETH 2D 71% against 58%.

6. Stepped, volatility-based exits. Exits are Jared's judgement and stay that way. Five mechanical exit rules were tested and all did worse than simply holding.

7. Timing entries around funding resets. Not tested. It affects the cost of holding a position, not the signal itself.

On the process: agreed that anything new gets backtested first. On our side every test is written down before it runs, split by chart and by period, and checked against the filters we already have, so a new idea is not just an old one under another name. A variant that passes would run alongside the current setup as a logged, computed signal first. Putting assets on it is a decision for once it has held up live.

Next on our side: test 1 and 2 under those rules and send the results.

Jared
