+++
title = "API reference"
description = "The complete HTTP API of lmgw: the OpenAI-, Anthropic- and llama.cpp-compatible routes, lmgw's own extensions and MCP, the device Chat API, the dashboard API with Knowledge, labs and ops, and the agent run API, generated from the gateway's OpenAPI document."
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

This page covers every route, grouped as the document groups them. **Inference** is what any key
reaches; the **Chat API** needs a paired device's key; the **Dashboard API** and **Ops** belong to
the owner (the dashboard's session or an owner key), and **Agent runtime** to an agent container's
own token. Each operation names its capability and who holds it. Developers who only build on
lmgw can download the smaller developer document, which leaves the owner's plane out.
