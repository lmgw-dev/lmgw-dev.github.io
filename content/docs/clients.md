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
    if chunk.choices:  # with stream_options.include_usage, the last chunk has only usage
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

`/mcp` also passes the servers' resources through, with their URIs namespaced by tool prefix, so
an MCP Apps host can read a tool's view with `resources/read`. `tools/list` stamps every tool of a
registered server with `_meta["lmgw/server"]` (its label, its name and the tool's own name), and
app-only tools stay out of model runs. When two servers offer a tool of the same name, both move to
`<server>__<tool>`. When a result has both text and `structuredContent`, the model reads the text,
and clients and views get the structured part.

## Embeddings, rerank and tokens

- `POST /v1/embeddings` takes OpenAI's request shape. Local embedding models appear with the
  `embed/` prefix by default.
- `POST /v1/rerank` takes a `query` and `documents` (Jina's spelling) or `texts` (TEI's).
- `POST /v1/count_tokens` takes `{model, input}` and counts a text for any model, with the
  backend's own tokenizer where it has one. `POST /v1/messages/count_tokens` and `POST /tokenize`
  are there for clients that expect Anthropic's or llama.cpp's routes.

## Apps: device keys, the Chat and its feed

A desktop or phone client like [Kai](@/kai.md) needs more than model calls: Chat threads it shares
with the dashboard, a feed of changes, a key of its own and a way to offer its own tools. lmgw has
these as general features of its API, open to any client.

- **Pairing.** **Usage → Keys & budgets → Pair a device…** mints a device key and shows it once,
  inside an `lmgw-pair:?v=1&url=…&name=…&key=…` link that a client can register a URL scheme
  handler for. A device key works on `/v1` like a client key, with its own scopes and budget, and
  on the Chat API under `/chat/api/`. It never reaches the admin side.
- **The feed.** `GET /chat/api/feed` is one Server-Sent Events stream per client. Stored events
  (`thread.*`, `folder.*`, `profile.*`, `approval.*`, `task.*`, `device.revoked`) carry an SSE
  `id:`, the cursor to resume from with `?since=<cursor>` or `Last-Event-ID`. Live events
  (`turn.*`, `voice.*`, `hold`, `state`, `resync`, `revoked`) carry none, and `hello` says what is
  live when the stream opens.
- **Ongoing conversations.** A folder can be marked as one conversation that continues.
  `POST /chat/api/folders/{id}/current` answers its current thread, starting a new one after the
  folder's idle time, or at once with `{"new": true}`.
- **Voice in a thread.** `GET /v1/realtime?chat_thread=<id>` binds a realtime session to a Chat
  thread: its turns are stored there, and its tools are the thread's.
- **Personality profiles.** `GET /chat/api/profiles` lists them with `default_profile_id`, the
  profile new threads start with. A thread's `profile_id` (`null` for none) is set through
  `POST /chat/api/threads/{id}/settings`, and a folder's defaults take one too. A folder whose
  default is `null` inherits the Chat's default, it does not mean "none".

[`lmgw-client`](https://github.com/lmgw-dev/lmgw/tree/main/crates/lmgw-client) is the Rust crate
Kai and the dashboard's voice panel use for these: sans-IO, with the feed decoder, the realtime
voice state and the wire types. The
[client apps design record](https://github.com/lmgw-dev/lmgw/blob/main/docs/design/2026-10-06-client-apps-design.md)
has the details.

## Approvals for MCP tools

An entry of a thread's `mcp_tools` takes `require_approval` in OpenAI's shapes: `"never"` (the
default), `"always"`, or `{"always": {"tool_names": [...]}, "never": {"tool_names": [...]}}`. A
folder's defaults take it too. A turn that reaches a gated call stops there: it streams a `tool`
frame with `"event": "approval"` for each waiting call and ends with `pending_approvals`, and the
waiting reply in `GET /chat/api/threads/{id}` lists the same calls as `pending_approvals`.

Any Chat client decides them, with a verdict for every waiting call:

```http
POST /chat/api/threads/42/approvals
content-type: application/json

{"decisions": [
  {"approval_request_id": "mcpr_1", "approve": true},
  {"approval_request_id": "mcpr_2", "approve": false, "reason": "not now"}
]}
```

The answer streams the resumed reply, which runs as the key that started the turn. The first
decision wins (`409 approval_decided` for a later one), and a new message in the thread declines
whatever still waits. The feed records `approval.requested` and `approval.decided`, each with the
call's `call_id`, the same id the turn's `ready` and `result` frames carry. A realtime session bound
to the thread gets OpenAI's `mcp_approval_request` item, answers with `mcp_approval_response` and
`response.create`, and hears `lmgw.approval.decided` when another client decided first.

A device can only tighten the rules: a settings write that would gate fewer calls is
`403 approval_loosen_refused`. It approves only calls within its own reach
(`403 approval_out_of_scope`), though it may decline any.

## Late tool results

An MCP server can answer a tool call with a task (MCP Tasks). The turn then goes on without the
result, and the result enters the thread when it arrives, never while a turn runs. The next turn
sees it as a call of `lmgw__job_result` and its result, in the order things happened.

- `GET /chat/api/threads/{id}/tasks` lists the thread's tasks that still run or whose results wait
  to enter, each with `id`, `tool`, `status` and `waiting_for`.
- `POST /chat/api/threads/{id}/tasks/{task}/cancel` cancels one, `{task}` being its `id`.
- `POST /chat/api/threads/{id}/answer` asks the model to answer results that arrived while nobody
  was talking. With none waiting it is `409 nothing_to_answer`, and while a turn runs
  `409 turn_running`.
- The feed says `task.started` when a call becomes a task and `task.done` when its result entered
  the thread. A realtime session bound to the thread gets `lmgw.task.done`, and a
  `response.create` with no new words has the model answer it aloud.
- `device.revoked` on the feed names a paired device whose key was deleted, so a client that runs
  work that device started can cancel it.

## Tools hosted by a device

A device paired with a label under **hosts tools as** can serve MCP tools of its own. It opens a
WebSocket to `GET /mcp/host` with its device key, and the roles reverse: lmgw is the MCP client on
the link, the device the server, one JSON-RPC message per text frame. lmgw's `initialize` carries
the link's limits in `params._meta["lmgw/host_limits"]`, and each forwarded `tools/call` names who
it runs for in `_meta["lmgw/caller"]` and the approval that let it through in
`_meta["lmgw/approval"]`. The tools appear as `<label>__<tool>` to the owner and lmgw's own Chat,
and to keys and agents whose tool scope names the label.

A key without the grant is refused `403 host_not_granted` before the upgrade, and a request with an
`Origin` header `403 cross_origin_refused`. A newer link of the same device takes over (close
4000), a revoked key closes the link with 4003, and a device that declares the tasks capability can
run its tools as MCP tasks, as above.
