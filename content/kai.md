+++
title = "Kai"
description = "A voice client for the KDE Plasma desktop. Talk to your models at any time, see what Kai is doing in the tray and over the desktop, and keep one ongoing conversation. Every model call goes through lmgw."
[extra]
kicker = "A Plasma client of lmgw"
status = "In development"
+++

<div class="status-box">

Kai is being built and has no release yet. It will be published in the
[lmgw-dev organization](https://github.com/lmgw-dev) once its first version works. Until then this
page describes the plan, which can still change.

</div>

Kai is a separate program that lives in the Plasma tray. It holds no models of its own: speech
recognition, the chat model and the voice all run in lmgw, and Kai reaches them through the same
public API any other client uses. If lmgw is set up to talk, Kai can talk.

## The first version

- **Voice at any time.** A global shortcut starts listening, from any app. Press to toggle, or hold
  to talk. Kai keeps the audio from the moment you press, so a model that still has to load loses
  no words.
- **One ongoing conversation.** Everything you say goes into one conversation called "Kai", stored
  in lmgw's Chat, so you can read it or carry on typing in the dashboard. A new conversation starts
  after an idle time you choose, or when you ask for one.
- **State you can see.** The tray icon shows whether Kai is idle, listening, thinking, speaking,
  muted, or waiting because the GPU is on hold. While voice is active, a ring drawn over the
  desktop follows the voice, the same ring as in lmgw's Chat.
- **Desktop audio done properly.** Capture and playback go through PipeWire, with the echo modes of
  lmgw's Chat: a microphone that cancels echo itself, echo cancellation in Kai, headphones, or half
  duplex. You can talk over Kai to interrupt it.
- **Starts with the session.** An XDG autostart entry, no system service. Shortcuts are set in
  System Settings, and credentials live in KWallet.

## Later

- **Overlays the agent controls.** Small borderless views over the desktop, such as a weather card
  or an image, shown and hidden by tools. They are HTML, which makes Kai a host for MCP Apps.
- **Desktop tools.** Kai serves an MCP server to lmgw: start programs, look at a window with a
  vision model, remember things per app, and work with the browser. Every tool has its own policy
  (allow, confirm or deny), and a tool set to confirm asks you before it runs.

## What it needs from lmgw

Kai adds no special case to lmgw. What it needs goes into lmgw as general features, so any client
can use them:

- **Device keys.** A device pairs once, through a link or a QR code, and gets a key of its own:
  named, revocable, and kept out of the admin side of lmgw.
- **A change feed for the Chat.** Clients see new turns as they happen, wherever they were made.
- **Ongoing conversations.** A Chat folder can be marked as one conversation that continues, with a
  new thread after an idle time.
- **Device-hosted MCP.** A connected client offers its own tools through lmgw, where the dashboard
  chat, agents and other clients can use them.

lmgw's [client apps design record](https://github.com/lmgw-dev/lmgw/blob/main/docs/design/2026-10-06-client-apps-design.md)
has the details, and the first of these is being built now. [Build on lmgw](@/docs/clients.md)
shows what clients can use today.
