# Model profiles and `ei doctor --models`

**BLUF:** A profile is a few lines of TOML that say how to reach one model: which adapter, which server, and which
environment variable holds the key. You need one only to use a model you pay for. `ei doctor --models` checks
every profile against the price catalog before a run spends anything, and sends nothing unless you add `--probe`.

A **profile** says how to reach one model: which adapter speaks to it, where the server is, and
which environment variable holds its key. You supply the file, as you do the price catalog
([`MODEL_CATALOG.md`](model-catalog.md)). A hosted API and a server on your own machine are both
just profiles.

`ei doctor --models` checks them before a run spends anything.

## A profile is an address, not a key

> **Daniel:** I put my API key in the profile file and the loader rejected it.
>
> **Professor Feynman:** Where do you write down a friend's address, and where do you keep your house key?
>
> **Daniel:** The address goes in my phone. The key stays in my pocket.
>
> **Professor Feynman:** A profile is the address: the server, the model's name, how to speak to it. It names the
> pocket the key is in, an environment variable, and never holds the key itself. So the file is safe to share,
> commit and print.
>
> **Daniel:** And if I misspell `api_key_env` itself?
>
> **Professor Feynman:** The file is refused, because an unknown line is an error here. Otherwise a typo would
> leave the key blank and you would call the server with no credentials. Misspell the variable's name instead and
> the file loads, but `ei doctor --models` fails its key check. The picture stops short in one place: an address
> can be right and the house still empty. So `--probe` knocks, once per profile, by asking the server to list its
> models.
>
> **Daniel:** Address in the file, key in the environment, a misspelt line refused, the doctor for a misspelt
> variable, and `--probe` to check someone is home.

## The profile file

Each `[[profile]]` has these keys. A `base_url` that carries a user name or password is refused, and so is
`reasoning_effort` on an `anthropic` profile. An unknown key is refused, because a misspelt `api_key_env`
would otherwise leave the key blank and the profile would call a server with no credentials.

| Key | Meaning |
|---|---|
| `name` | what you call it; unique in the file |
| `adapter` | `anthropic` or `openai_compatible` |
| `provider`, `model` | pick the price in the catalog; they must match a catalog entry |
| `base_url` | where the server is. Optional for `anthropic` (`https://api.anthropic.com`), required otherwise |
| `api_key_env` | the NAME of the environment variable that holds the key, never the key. Blank only for `openai_compatible`: that is how a local model is described |
| `output_cap_field` | `max_tokens` (the default, what local servers expect) or `max_completion_tokens` (current OpenAI models) |
| `reasoning_effort` | `low`, `medium` or `high`, sent to an `openai_compatible` server for a model that reasons before it answers. The reasoning counts against the reply's token cap, so a model that reasons at length can use a whole stage's cap before writing a word; `low` avoids that. Blank sends nothing |

A value in `api_key_env` that is not shaped like a variable name (capitals, digits and
underscores) is refused, and the error does not repeat it, so a pasted key cannot be saved in a
file that gets committed.

### Example: a hosted model and a local one

The provider names and the model are made up. Use the names in your own catalog.

```toml
[[profile]]
name = "hosted"
adapter = "anthropic"
provider = "example"
model = "example-model"
api_key_env = "ANTHROPIC_API_KEY"

[[profile]]
name = "local"
adapter = "openai_compatible"
provider = "local"
model = "llama3.1:8b"
base_url = "http://127.0.0.1:11434"
```

The local model still needs a catalog entry, because a run reserves a cost before every call.
It costs nothing per token, so its prices are zero:

```toml
[[model]]
provider = "local"
model = "llama3.1:8b"
family = "llama"
context_window = 128000
max_output_tokens = 4096
usage_policy_url = "https://example.com/the-models-licence"

[[model.price]]
effective = "2026-01-01"
input = 0
output = 0
cache_read = 0
cache_write = 0
batch_discount_percent = 0
```

Ollama, vLLM and llama.cpp all serve `/v1/chat/completions` on the address you give. Set
`usage_policy_url` to the licence of the weights you run; this package cannot vouch for it.

## The command

```bash
ei doctor --models --catalog catalog.toml --profiles profiles.toml
```

`--catalog` and `--profiles` default to `EI_MODEL_CATALOG` and `EI_MODEL_PROFILES`. It needs the
`runtime` extra.

| Check | Passes when |
|---|---|
| `price` | the catalog has a price for the profile's `provider` and `model` in force today |
| `key` | the variable named by `api_key_env` is set and not blank, or the profile needs none. The value is never printed |
| `transport` | shown only when it fails: a key would go over plain `http` to a host that is not this machine |
| `probe` | only with `--probe`; see below |

**By default nothing is sent anywhere.** The checks read two files and the environment.

`--probe` is opt-in. For each profile whose key is in place it sends one `GET /v1/models` to the
profile's server, with the key, and reports `available`, `authentication failed`,
`credits exhausted` or `window exhausted` from the answer. It never asks a model to complete
anything. It shows that the server is reachable and accepts the key. It does **not** show that
the account has credit, or that the model you named is served (a listing can be paged, so a
missing name proves nothing). A redirect is reported and not followed, because following one
would send your key to a host you did not configure. A profile whose key would go over plain
`http` to another machine is not probed at all (the `transport` check already fails it).

There is no check that bills. A real run, capped by a budget you set, is the `paid` smoke test in
[LIVE_SMOKE_TEST.md](live-smoke-test.md).

Exit status: `0` every check held, `1` a check failed (or the `runtime` extra is missing), `2` a
file could not be read or is invalid.
