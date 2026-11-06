+++
title = "Kai mobile"
description = "The Android client of lmgw: talk to your own models from your phone, in the same ongoing conversation as Kai on the desktop, with notifications and approvals from your gateway. Every model call goes through your lmgw."
[extra]
kicker = "An Android client of lmgw"
status = "Alpha · 0.2.0"
status_kind = "amber"
+++

Kai mobile is the phone side of [Kai](@/kai.md): the same ongoing conversation, held in lmgw's
Chat, now on Android. It is a native app (Kotlin and Compose around a Rust core) that runs no
models and has no account. Speech recognition, the chat model and the voice all come from your
lmgw, and without an lmgw to pair with the app does nothing. Version 0.2.0 needs lmgw 0.6.0; 0.1.1 was the first release.

## What it does

- **Talk to Kai.** Voice calls over WebRTC, with turn-taking handled for you, push-to-talk, mute,
  stopping Kai by speaking, captions and a ring that follows the voice. Echo cancelling (in software,
  or half duplex), Bluetooth and headset routing, headset buttons and audio focus are handled:
  another app's audio pauses the call instead of ending it. If another device holds the
  conversation's call, Take over asks first.
- **Browse every thread.** A Threads page lists your Chat folders and threads in lmgw's order, with
  search across active, archived or all threads. Pin, archive, move, rename or delete from a
  thread's menu. On a wide screen (a foldable, say) the list and the thread sit side by side.
- **Voice in any thread.** Talk beside an opened thread starts a call there, or moves the running
  call at its next quiet point.
- **Or type.** The conversation is the one you also read in lmgw's dashboard and continue with Kai
  on the desktop: Markdown replies, tool notices under the answer, and a New conversation action.
- **Assistant mode.** Set Kai as Android's assistant (a card in the app walks you through it) and
  its overlay opens from the assist gesture, a Quick Settings tile or a launcher shortcut. Closing
  the overlay before you spoke ends the call. After a turn the call goes on, and Expand moves it
  into the app.
- **Approvals by tap.** When a tool asks first, one card shows on the overlay, the voice screen and
  in the conversation, and as a notification with Approve and Decline. Approving needs an unlocked
  phone; declining works locked.
- **Notifications from your gateway.** A foreground service holds lmgw's Chat feed open while the
  phone is paired, so replies and the answer to a job that outlived the turn reach you with the app
  closed, with no push provider in between. Notifications show no content on the lock screen.
- **Nothing in between.** The phone talks to your lmgw only, over mutual TLS, with a key made in
  the Android Keystore that never leaves it. No Google services, no analytics, no message cache.
- **Settings in plain words,** and a choice between the shared Kai conversation and one only on this
  phone.
- Two-screen layouts, TalkBack and font-scale support.

## Status

Alpha. It has had little time on real phones, so expect
rough edges, and settings, screens and the wire to lmgw can still change between releases. Bug
reports are welcome as [issues](https://github.com/lmgw-dev/kai-mobile/issues).

## Known gaps

- Images and attachments in messages.
- A spoken yes or no for approvals (use the card or the notification).
- A local message cache: the conversation is read again at start.
- Markdown tables.
- Phone tools such as alarms and calendar, and screen context for the assistant.
- The lock screen as a place to talk.
- Automatic certificate renewal: the pairing's certificate lapses after about a year, and you pair
  again.
- Whether your phone maker lets the side button or power key reach the assistant varies.
- There is no in-app updater, and there is no iOS app.

## Requirements

- **Android 12 (API 31) or later,** 64-bit ARM (`arm64-v8a`).
- **lmgw 0.6.0 or newer,** with its device listener on (pairing turns it on) and a chat model.
  Voice needs speech-to-text and text-to-speech models, set up as for voice mode in lmgw's Chat.
- **A network path from the phone to lmgw's device port:** the same Wi-Fi, or a VPN such as
  WireGuard. A pairing link can carry several addresses and the app follows whichever answers. The
  device port is a TLS listener of its own, next to the dashboard's port, so the machine running
  lmgw has to admit it through its firewall: TCP for the app, TCP and UDP for calls. Calls use UDP
  and lmgw has no STUN or TURN server, so the phone must reach lmgw directly.

## Install

1. Download `kai-mobile-<version>.apk` and `SHA256SUMS` from
   [Kai mobile's releases](https://github.com/lmgw-dev/kai-mobile/releases).
2. Check the download with `sha256sum --check SHA256SUMS` in the folder that holds both.
3. Open the APK on the phone. Android asks once to allow installs from the app you opened it with
   (your browser or file manager). From a computer, `adb install --user current kai-mobile-<version>.apk`
   does the same.

To update, install the newer APK over the old one; the pairing stays.

## Pair it with lmgw

1. In lmgw's dashboard, open **Usage → Keys & budgets**, and on the **Devices** card choose
   **Pair a device**. Name it, pick what it may reach, and review the step that shows exactly that.
   The device listener is off until the first pairing turns it on. For a device that is not on
   lmgw's own computer, lmgw offers to widen it from loopback to the network, after a confirmation
   that names the exposure.
2. lmgw shows a QR code and the same link as text. The link is a credential for as long as its
   token lives (ten minutes by default) and works once: nobody else should see it.
3. In Kai mobile, scan the QR code with the camera, or tap the link, or paste it. The app makes its
   key in the Keystore, enrols the public half with the link's one-time token and shows a short
   confirmation code.
4. lmgw's Devices card shows the same code. When they match, press **Confirm**. Until you do, lmgw
   refuses the device, so a photographed QR code gets a stranger a row that you see and delete,
   never a working device.

The card also disables or revokes a device and re-pairs it with a new link. The app says what
happened and asks you to pair again.

The conversation lives in the Chat folder "Kai", which the phone shares with Kai on the desktop and
creates if no one has. In lmgw's Chat, open that folder's settings, choose its model and switch on
**Ongoing conversation**. Until the folder is ready, the app lists these steps, and voice and
sending wait for them.

## Source and licence

The source is at [github.com/lmgw-dev/kai-mobile](https://github.com/lmgw-dev/kai-mobile), under
the MIT licence like lmgw and Kai. The README there describes the build, and its design record
explains the pairing and the device link in detail.
