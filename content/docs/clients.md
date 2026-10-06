+++
title = "Build on lmgw"
description = "lmgw speaks protocols your code already knows. Point an OpenAI or Anthropic client at it, read what each model can do from /v1/models, and add voice and tools when you need them."
weight = 1
[extra]
kicker = "Guide"
+++

There is no lmgw SDK, and you don't need one. The gateway copies the OpenAI and Anthropic
protocols, so the official SDKs, the OpenAI Agents SDK and anything else built on them work after
you change the base URL. Where lmgw adds something, it does so in headers and extra fields that a
client can ignore.

## Connect

lmgw listens on `127.0.0.1:8787` by default. Until you turn on **Require gateway API keys on /v1**
in its settings, any key or none is accepted; after that, use a key from **Usage → Keys &
budgets**.

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8787/v1", api_key="unused")

stream = client.chat.completions.create(
    model="my-model",
    messages=[{"role": "user", "content": "Write a haiku about VRAM."}],
    stream=True,
)
for chunk in stream:
    if chunk.choices:  # the last chunk carries only the token usage
        print(chunk.choices[0].delta.content or "", end="", flush=True)
```

The Anthropic SDKs take the bare address, because they add `/v1/messages` themselves:

```python
import anthropic

client = anthropic.Anthropic(base_url="http://127.0.0.1:8787", api_key="unused")

message = client.messages.create(
    model="my-model",
    max_tokens=512,
    messages=[{"role": "user", "content": "Hello!"}],
)
print("".join(block.text for block in message.content if block.type == "text"))
```

Both reach the same alias. A model served by llama.cpp answers an Anthropic client, and a Claude
model answers an OpenAI client: lmgw translates streaming, tool calls, images and reasoning in
both directions. A model that reasons puts a `thinking` block before its text, which is why the
sample joins only the text blocks.

## Find out what a model can do

`GET /v1/models` lists every alias with what lmgw knows about it, read from the GGUF file, the
running llama-server, a provider's catalog or your own overrides. A client can decide from this
whether to send images, offer tools or show a thinking toggle, instead of guessing from the name.

```json
{
  "id": "my-model",
  "object": "model",
  "owned_by": "llama-server",
  "context_length": 131072,
  "capabilities": {
    "task": "chat",
    "endpoints": ["/v1/chat/completions", "/v1/messages", "/v1/responses", "/v1/completions"],
    "input_modalities": ["text", "image"],
    "vision": true,
    "reasoning": { "kind": "toggle", "can_disable": true, "enabled": false },
    "tool_calls": { "kind": "native", "parallel": true },
    "source": "gguf+config"
  },
  "notes": ["Reasoning is OFF by default. Per request: header x-lmgw-reasoning: on|off, ..."]
}
```

That is an excerpt of one entry. `endpoints` names the routes that accept the model, `notes` explains its quirks in plain
sentences, and an unknown capability is left out rather than reported as missing.
[ModelCapabilities](/docs/api/#schema-ModelCapabilities) in the API reference has every field.

## Reasoning on demand

Thinking models differ in how they are switched: a template flag, an effort level, a token
budget. lmgw puts one set of request headers in front of all of them, on chat completions,
messages and responses:

- `x-lmgw-reasoning: on` or `off`
- `x-lmgw-reasoning-effort: low` (the levels a model takes are in its `capabilities.reasoning`)
- `x-lmgw-reasoning-budget: 2048`

When a route cannot express a control, the response says so in `x-lmgw-reasoning-ignored`.

## Which model answered

A local model can have a fallback, usually a cloud alias that takes over while the GPU hold pauses
local models, or while another program holds the memory the model needs. The response body keeps the alias you asked for in its `model` field, so
clients that check it keep working. The headers say what really happened:

- `x-lmgw-fallback` names the alias that answered instead, and `x-lmgw-fallback-reason` says why.
- `x-lmgw-images-omitted` counts images that went to a fallback without vision as text
  placeholders.
- `x-lmgw-candidate` names the local model that answered a candidate alias: one name for a primary
  model and alternates, answered by whichever of them is already loaded.

With no fallback, a request to a paused model fails with `503` and the code `gpu_hold`, so the
fallback settings decide whether a request may leave the machine. Chat models take the
gateway-wide hold fallback unless their own row says otherwise. The
[headers table](/docs/api/#headers) lists all of them.

## Voice

`ws://127.0.0.1:8787/v1/realtime` speaks OpenAI's Realtime protocol. The OpenAI Python SDK's
realtime client connects with the same base URL as above, since it turns `http` into `ws`. The
JavaScript SDK insists on `wss:`, so there, pass the URL to a client that takes one, such as the
Agents SDK's `OpenAIRealtimeWebSocket({ url })`. Behind it is a cascade of your own models: lmgw
detects the turns, transcribes them with a speech-to-text model, answers with a chat model and
speaks with a text-to-speech model. Pick the three under **Settings → Realtime**.

Sessions take audio or text output, PCM16 at 24 kHz, `server_vad`, `semantic_vad` and manual
turns, and barge-in. Function tools work as with OpenAI. WebRTC, SIP, ephemeral keys,
transcription-only sessions and G.711 are not implemented yet.

A session can also use the MCP servers lmgw serves, by label:

```json
{"type": "session.update", "session": {"type": "realtime", "tools": [
  {"type": "mcp", "server_label": "docs"}
]}}
```

lmgw runs the call before the response ends and reports it as an `mcp_call` item, and as in
OpenAI's API, the client sends `response.create` for the answer. The OpenAI Agents SDK for
JavaScript (`hostedMcpTool`) does that by itself. To offer a picker, `GET /v1/mcp/servers` lists the labels a key may use and
`GET /v1/mcp/servers/{label}` the tools behind one.

## Tools over MCP

`http://127.0.0.1:8787/mcp` is one MCP endpoint (Streamable HTTP) for every server registered in
lmgw, each under its own tool prefix, plus built-in tools that search library documentation
(`docs__*`) and your knowledge bases (`kb__*`). For Claude Code:

```sh
claude mcp add --transport http lmgw http://127.0.0.1:8787/mcp
```

A key's tool scope decides which of them a client sees. The same tools can be named in a
`/v1/responses` request with `{"type": "mcp", "server_label": ...}` on any alias lmgw answers
itself, which is every local model and every upstream not set to take `/v1/responses` directly.
lmgw resolves the label against its own servers and never connects to a URL a client sends.

## Embeddings, rerank and tokens

- `POST /v1/embeddings` takes OpenAI's request shape. Local embedding models appear with the
  `embed/` prefix by default.
- `POST /v1/rerank` takes a `query` and `documents` (Jina's spelling) or `texts` (TEI's).
- `POST /v1/count_tokens` takes `{model, input}` and counts a text for any model, with the
  backend's own tokenizer where it has one. `POST /v1/messages/count_tokens` and `POST /tokenize`
  are there for clients that expect Anthropic's or llama.cpp's routes.

## Apps that need more than inference

A desktop or phone client like [Kai](@/kai.md) needs more than model calls: Chat threads it shares
with the dashboard, a feed of changes, a key per device and a way to offer its own tools. lmgw
plans these as general features of its API, described in its
[client apps design record](https://github.com/lmgw-dev/lmgw/blob/main/docs/design/2026-10-06-client-apps-design.md).
Until they land, the routes in the [API reference](@/docs/api.md) are the stable surface.
