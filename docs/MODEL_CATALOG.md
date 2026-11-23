# The model catalog

A run reserves money before every model call, so it must know what a call costs. The catalog
is the file that says. **You supply it**: prices change, and this package cannot vouch for any
vendor's current prices, so it ships none. A model with no price in force on a date is refused
(`MODEL_UNPRICED`), never guessed.

`TomlModelCatalogLoader` reads the file. Each `[[model]]` names a model and its limits, and
each `[[model.price]]` under it is a set of prices that takes effect on a date. The run uses
the latest entry whose `effective` date is on or before the day of the call, so you keep old
entries and add a new one when a vendor changes prices.

## Units

Prices are whole **micro-dollars per million tokens**: `3000000` means $3.00 per million
tokens. They are integers so that no cost is ever rounded on the way in; the arithmetic after
that always rounds up, so a run is never charged less than it owes.

| Key | Meaning |
|---|---|
| `input`, `output` | the plain input and output rates |
| `cache_read`, `cache_write` | the rates for prompt tokens read from or written to the cache |
| `batch_discount_percent` | the percentage taken off a batch call, 0 to 100 |
| `long_context_threshold_tokens` | a prompt longer than this is billed at the long-context rates; omit for none |
| `long_context_input_percent`, `long_context_output_percent` | those rates as a percentage of the standard ones, never below 100 |

## Example

These numbers are made up. They show the shape and nothing else: replace the provider, the
model and every price with the values from your provider's price list.

```toml
[[model]]
provider = "example"
model = "example-model"
family = "example"
context_window = 200000
max_output_tokens = 8000
usage_policy_url = "https://example.com/usage-policy"

[[model.price]]
effective = "2026-01-01"
input = 3000000
output = 15000000
cache_read = 300000
cache_write = 3750000
batch_discount_percent = 50

[[model.price]]
effective = "2026-07-01"
input = 2000000
output = 10000000
cache_read = 200000
cache_write = 2500000
batch_discount_percent = 50
long_context_threshold_tokens = 200000
long_context_input_percent = 200
long_context_output_percent = 150
```

## Content levels

A novel's brief may set `violence` (`none`, `mild`, `moderate`, `graphic`) and `heat` (`none`, `sweet`, `steamy`,
`explicit`), mildest first. This project does not know any provider's usage policy and does not claim to, so the
ceiling for a model is something **you** record, after reading the `usage_policy_url` you already give it:

```toml
[[model]]
# ...the keys above...
max_violence = "moderate"
max_heat = "sweet"
```

A model with no ceiling recorded is held to `mild` violence and `sweet` heat, so a brief that asks for more is refused
before anything is spent, with a message that names the setting to change. A brief that sets no level is never
refused. A model on your own machine is the same: you record what you are willing to ask of it. The check is the
`ContentPolicy` service; the novel stages (M7.3) call it before their first paid call. It is a guard against asking a
model for what its provider has said it will not write, not a content filter and not legal advice.

## What goes wrong

- `MODEL_CATALOG_INVALID` names the entry (`model #2 (example/example-model) is missing 'family'`).
  A price entry needs all of `effective`, `input`, `output`, `cache_read`, `cache_write` and
  `batch_discount_percent`.
- Two prices for one model with the same `effective` date are refused, because the run could not
  tell which one applies.
- `MODEL_UNPRICED` means the day of the call is before the model's first `effective` date, or the
  model is not in the catalog at all.
