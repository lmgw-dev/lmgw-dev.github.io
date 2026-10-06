+++
title = "API reference"
description = "The HTTP API of lmgw's inference plane: the OpenAI-, Anthropic- and llama.cpp-compatible routes, lmgw's own extensions and MCP, generated from the gateway's OpenAPI document."
template = "api.html"
weight = 2
+++

## Base URLs and keys

| Client | Base URL |
| --- | --- |
| OpenAI SDKs and tools | `http://127.0.0.1:8787/v1` |
| Anthropic SDKs, Claude Code (`ANTHROPIC_BASE_URL`) | `http://127.0.0.1:8787` |
| Realtime voice sessions | `ws://127.0.0.1:8787/v1/realtime` |
| MCP clients | `http://127.0.0.1:8787/mcp` |

`127.0.0.1:8787` is lmgw's default address; **Settings → Network & access** changes it. The
Anthropic SDKs want the bare address because they add `/v1/messages` themselves.

`/v1` and `/mcp` accept requests without a key until **Require gateway API keys on /v1** is on.
From then on, send a key from **Usage → Keys & budgets** as `Authorization: Bearer <key>`, or as
`x-api-key: <key>` the way Anthropic clients do. A key can be limited to some aliases and tools,
and carry a budget and rate limits.

Errors come in the shape of the protocol you called: OpenAI's on the OpenAI routes, Anthropic's on
`/v1/messages`. A local model paused by the GPU hold answers `503` with the code `gpu_hold`, unless
it has a fallback, which then answers instead and is named in `x-lmgw-fallback`.

This page covers what a client can reach with an inference key. The dashboard's own API (`/api`)
is documented in the app, on its **API reference** page.
