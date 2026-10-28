# Live data feed to Joe's side — sent 28 Oct 2026

Sent to joseph@themaurogroup.com, cc his Grok bot, 28 Oct 2026 ~14:40 ET.
Full write-up with diagrams: `2026-10-28_live_feed_proposal.pdf` (this folder), exported from the Claude doc
(claude.ai/artifact/WhTqUpk8u5o1iEzWLX5cUS), for Jared to walk through at the next meeting.

Finding: the GitHub job scores everything every 3-4h, but only the daily copy task
(4:17 AM ET) carries part of it (some datasets) to the ETH Setup Standard page. Joe's
Grok knows only what was emailed. His portal snapshot's source is unconfirmed. His side
lacks the full scope, including confluences.

Proposal: one feed written by the GitHub job every run -> one small backend
(Cloudflare proposed) serving views per audience behind keys (admin with approve per
signal, Prime, Signal, delayed Free) -> every screen reads (admin portal + Grok, member
site + alerts, public page, our dashboard). Versioned format, fields added not renamed.
"Computed signal, not a fill - entry quality only" carried in every record. Repo to go
private before paid views go live.

Open decisions for the meeting: who builds the admin portal and member screens; where
the backend runs; who can approve; free-tier delay; alert channels; what Grok reads and
writes back; when the repo goes private.

## Follow-up sent 28 Oct 2026 ~19:25 ET (reply in the same thread, cc his Grok)
Joe replied 15:01 ET with his lean on all six decisions (who builds: Jared feed+backend,
Joe's side portal+member screens under ETHKROS; Cloudflare in ETHKROS's name, both admins;
approvals Joe+Jared only, logged, never automatic; free tier delay >= 24h, ideally until the
entry window closes; email + member site at launch, Telegram once stable, live calls Inner
Table only; Grok read-only, no write-back at launch). The proposal doc and PDF were updated
to record those leans. The follow-up email carries the whole write-up as text, diagrams
described in words (the PDF could not be attached from the session; Jared has it). Still
open: repo private timing, Grok's format/update rate, when Telegram is added.
