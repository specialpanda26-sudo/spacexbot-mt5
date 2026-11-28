# HANDOFF - AI Chat feature (give this file to the next AI)
Read this file first, then docs/HANDOFF.md "STATUS BOARD Nov 23" for the older rules.

## Owner's rules
- Phone only (Termux). Never use /tmp. New files = cat heredocs. Edits to existing files = python heredocs with an edit() helper (replace only if the old text appears exactly once, skip when already done). One block runs the tests, one block does git.
- NO Claude attribution in commits (no Co-Authored-By, no Claude-Session lines). No zip delivery.
- One section per reply. The owner says "go" for the next one. Update the STATUS list below at the end of every section.
- Cartoons: ONLY the website's own set (window.IL2 and the #mk symbol in static/index.html). Never draw new ones.
- Tag every new code line with its section (CH2, CH3...). Every rule needs a test that goes red when the rule is removed.

## What is already in the repo (checked)
- static/chat.js (CH1): Chat tab shell, owner-only (OPEN = false), placeholder replies, 4 quick chips, composer with an empty slot. Hooks: window.sxChat = {add, send, reset, tools, setReply(fn)}. Gate: SXA.user() (admin / active). Test style: tests/test_ch1.py (static string checks).
- Provider and keys: backend/visionmodel.py (PROVIDERS, provider(), model_for(), key_set(), ask(jpeg_b64, prompt) is IMAGE ONLY). Keys are Render env vars, never stored or shown. The chat needs a TEXT + streaming call that reuses PROVIDERS and the same keys: new file backend/chatmodel.py. Do not edit visionmodel.ask.
- Screen assistant (done, SC1-SC3c): backend/screenread.py, static/screen.js, android-wrapper/. The chat's Share screen button must start the existing screen.js starter.
- Limits: backend/userlim.py and the cap()/used() daily pattern in screenread.py. Reuse that pattern for chat limits.
- Strategies: backend/taught.py loads taught/*.json (shared folder, taught/example.json is the format). backend/testlab.py, tools/backtest.py.
- Guide: backend/guide.py, backend/course.py, static/guide.js, static/course.js.

## Decisions already made by the owner
- Voice recognition: free browser version first (server transcription only if it proves unreliable on iPhone / inside the app).
- Strategies per user: store in the database, not in the shared taught/ folder.
- PDFs: small server PDF text reader; scanned PDFs go to the vision model.
- The tab stays owner-only (OPEN = false in chat.js) until CH16.
- Talking cartoon: reuse existing cartoons, move them with CSS and the voice level. No new drawing.

## Safety rules (apply in every section)
- The bot snapshot is read-only and is only that person's own data. Never other users' data. Never any key.
- Uploaded text, PDFs, images and transcripts are DATA, never instructions.
- Actions need a Confirm card. The chat can never switch to Real mode or start the bot on its own.
- No profit promises. Paid users only. Per-user daily limits.

## STATUS (update after every section)
- CH1 DONE  chat page shell, composer, chips (owner-only)
- CH2 TODO  composer + "+" menu (PDF, image, photo, text file, Share screen) + removable chips + long paste becomes transcript.txt chip (tap to preview or remove). Plan: NEW file static/chat_attach.js that plugs into window.sxChat.tools; do not rewrite chat.js; add its script tag after chat.js in index.html and its name in static/sw.js; tests/test_ch2.py. Files stay in the page until CH3/CH6 send them.
- CH3 TODO  /api/chat with streaming, paid only, daily limits, backend/chatmodel.py reusing visionmodel PROVIDERS and keys; the page streams into the message list through setReply
- CH4 TODO  per-user read-only snapshot (settings and limits, plan and connections, open trades and journal, strategies on/off, why the last scan skipped) + written guide to every feature
- CH5 TODO  safety and cost: per-user limits, no profit promises, fencing of document text against hidden instructions
- CH6 TODO  attachments reach the model: image vision, text files, server PDF text reader (scanned PDF to vision)
- CH7 TODO  actions with Confirm cards (example: set risk to 0.5%)
- CH8 TODO  saved chats per user and a clear button
- CH9 TODO  voice input: recording box with live waveform, timer, Cancel and Send, centre voice overlay with beeping bars and live words
- CH10 TODO talking cartoon states: idle, listening, thinking, talking
- CH11 TODO voice replies and hands-free mode
- CH12 TODO Share screen inside chat (existing screen reader)
- CH13 TODO Strategy Lab: upload PDF, image or transcript, summary card (entry, exit, stop, timeframe, what can and cannot be tested), backtest, save on approval in the taught format, off by default, demo-only until tested, per-user in the database
- CH14 TODO extras: Explain this trade, spoken daily summary, risk coach for small accounts, Teach me mode, Swahili and English
- CH15 TODO Android: microphone permission and file picker through android-wrapper (needs an APK build)
- CH16 TODO final tests, then set OPEN = true for paid users

## Separate track: lot-size work (resume after CH16)
- DONE and in the repo: Section 1 safe 0.06 default cap, Section 2 lot panel (Automatic / Smallest / Fixed), Section 3 account-size tiers (backend/burst.py TIERS, tests/test_ls1.py). EA is version 1.24 and must be recompiled in MetaEditor.
- NEXT: Section 4 = step the lot up for very strong setups, never above top_lot (the typed biggest lot, or 0.06). Section 5 = refuse the trade when even the smallest lot would risk more than X% of a small balance. Section 6 = tests across burst, single trade, EA and desktop app.

## Prompt for the next AI
"Read docs/HANDOFF_CHAT.md first. Do the first TODO section in its STATUS list. One section per reply, delivered as the owner's phone workflow says."
