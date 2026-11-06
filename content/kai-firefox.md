+++
title = "Kai for Firefox"
description = "A Firefox extension that gives Kai hands and eyes in the browser and puts lmgw's Chat in a sidebar beside the page. It talks only to Kai."
[extra]
kicker = "A Firefox extension for Kai"
status = "Alpha · first release"
status_kind = "amber"
+++

Kai for Firefox lets [Kai](@/kai.md), the voice assistant for the KDE Plasma desktop, read and
operate the pages open in Firefox, and puts lmgw's Chat in a sidebar beside the page. It works
whether you talk to Kai, type in lmgw's Chat or use [Kai mobile](@/kai-mobile.md), with the sidebar
open or not. Version 0.1.0 is the first release.

## What it does

- **Browser tools for Kai.** Where you are (your tab, the focus, the selection), tabs, reading
  (outline, controls, links, fields, the article or all text, tables, find, PDFs in Firefox's
  viewer), screenshots for a vision model, acting (press, fill, choose, check, attach a file, hover,
  drag, scroll, keys), numbered hints over the controls in view, zoom, Reader view, bookmarks,
  history and downloads, and source, DOM, CSS and script tools for developers. Every result from a
  page starts with the tab's title and address, so page text is never mistaken for your words.
- **Hands and eyes.** Ask, and Kai acts on the tab in front of you: "read the article", "what does
  the error say", "fill in the form". With hints shown, "press 14" works.
- **What changed, said out loud.** Kai can say on its own that a page loaded, a dialog opened or a
  field shows an error, without a model turn.
- **Reading aloud.** A page read paragraph by paragraph, with pause, resume and skip.
- **Firefox's own pages and dialogs.** Kai reads and presses a page's dialogs, a site's permission
  prompts and Firefox's own pages through the desktop's accessibility.
- **The Chat beside the page.** The sidebar (toolbar button or `Ctrl+Alt+K`) is lmgw's Chat in a
  narrow column: folders, threads, search, tools, approvals, attachments and the composer, the same
  threads as in the dashboard and on your phone. **Page** attaches the page's readable text to the
  open thread.

Accessibility is a supported use and is tested: acceptance runs through Kai's real tool path, with
no mouse or keyboard input from the tester.

## Privacy and control

- **The extension talks only to Kai,** through Firefox's native messaging. It holds no key or token,
  opens no connection to lmgw, runs no service of its own, and has no telemetry. Kai reaches lmgw
  with its own device certificate.
- **Site rules,** set in Kai's settings by host, domain or origin: `act` reads and acts, `read` only
  reads, `none` reaches nothing and leaves the site's tabs out of Kai's tab list.
- **Acting asks first** by default. A switch in Kai's Firefox section lets Kai act unasked, but only
  on the tab you brought to the front, on the site where you last acted. **Ask before committing**
  still asks before a buy, send or delete, a form that goes to another site or a site your history has
  never seen.
- **Kai never reads** `about:logins`, the password manager or a password field.
- **Page text can steer a model.** Every page is text from a stranger and can carry instructions
  aimed at the model. The rules keep the common case quick and the risky steps visible; they do not
  make such instructions harmless. With a cloud model, page text goes to that provider like the rest
  of the conversation.

## Status

Alpha, and the first public release. Not built yet: other browsers, private windows, Firefox's file
and save dialogs and address bar, voice in the sidebar (use Kai's talk key), changing a site's rule
from the sidebar, and settings per Firefox profile. A Flatpak or Snap Firefox cannot reach Kai yet.

## Requirements

- **Firefox 154 or newer,** as a regular package such as Fedora's RPM.
- **[Kai](@/kai.md) 0.3.0 or newer** on the same computer, paired with lmgw. Its RPM installs the
  native-messaging host and registers it with Firefox.
- **lmgw 0.6.0,** because the sidebar is built on its Chat.
- For Firefox's own pages and dialogs, the desktop's accessibility has to be on when Firefox starts.

## Install

Open `kai-firefox.xpi` from [the latest release](https://github.com/lmgw-dev/kai-firefox/releases) in
Firefox and confirm, or use **about:addons → ⚙ → Install Add-on From File…**. Kai's settings window
can offer it too (**Firefox → Install Kai for Firefox**). The add-on is signed by Mozilla as an
unlisted add-on, so it is not on addons.mozilla.org; Firefox updates it from the repository's
releases. Kai takes the link only from a Firefox that Plasma started (the application menu, a link
or autostart), not one started from a terminal.

## Source and licence

The source is at [github.com/lmgw-dev/kai-firefox](https://github.com/lmgw-dev/kai-firefox). It is under the MIT licence, like Kai and lmgw.
