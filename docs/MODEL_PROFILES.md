# Model profiles and `ei doctor --models`

A **profile** says how to reach one model: which adapter speaks to it, where the server is, and
which environment variable holds its key. You supply the file, as you do the price catalog
([`MODEL_CATALOG.md`](MODEL_CATALOG.md)). A hosted API and a server on your own machine are both
just profiles.

`ei doctor --models` checks them before a run spends anything.

## The profile file

Each `[[profile]]` has these keys. An unknown key is refused, because a misspelt `api_key_env`
would otherwise leave the key blank and the profile would call a server with no credentials.

| Key | Meaning |
|---|---|
| `name` | what you call it; unique in the file |
| `adapter` | `anthropic` or `openai_compatible` |
| `provider`, `model` | pick the price in the catalog; they must match a catalog entry |
| `base_url` | where the server is. Optional for `anthropic` (`https://api.anthropic.com`), required otherwise |
| `api_key_env` | the NAME of the environment variable that holds the key, never the key. Blank only for `openai_compatible`: that is how a local model is described |
| `output_cap_field` | `max_tokens` (the default, what local servers expect) or `max_completion_tokens` (current OpenAI models) |

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
would send your key to a host you did not configure.

There is no check that bills. A real completion test would belong behind the `paid` marker, with
your approval.

Exit status: `0` every check held, `1` a check failed (or the `runtime` extra is missing), `2` a
file could not be read or is invalid.
