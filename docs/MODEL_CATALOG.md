# The model catalog

**BLUF:** The catalog is a TOML file you supply that says what each model costs. A run needs it because it sets
money aside before every call. This package ships no prices, since they change and it cannot vouch for them, and a
model with no price in force when the process starts is refused (`MODEL_UNPRICED`), never guessed. The free local
model needs no catalog.

A run reserves money before every model call, so it must know what a call costs. The catalog
is the file that says. **You supply it**: prices change, and this package cannot vouch for any
vendor's current prices, so it ships none. A model with no price in force on a date is refused
(`MODEL_UNPRICED`), never guessed.

`TomlModelCatalogLoader` reads the file. Each `[[model]]` names a model and its limits, and
each `[[model.price]]` under it is a set of prices that takes effect on a date. The run uses
the latest entry whose `effective` date is on or before the day the worker (or `ei book create`) started, so you
keep old entries and add a new one when a vendor changes prices. The price is looked up once, at start: restart a
long-running worker when a new price takes effect.

A `[[model]]` needs `provider`, `model`, `family`, `context_window`, `max_output_tokens`, `usage_policy_url` and at
least one `[[model.price]]`.

## Why it ships no prices

> **Daniel:** It would be friendlier to ship a price list. Why make me type in what my provider charges?
>
> **Professor Feynman:** Suppose I handed you last year's train timetable and you missed your train. Whose fault?
>
> **Daniel:** Yours, for handing it to me as if it were current.
>
> **Professor Feynman:** A price list in a package is last year's timetable the day it ships. If it were low, your
> five dollar cap would quietly let eight dollars through. So the file is yours, each price has the date it took
> effect, and you add a new entry when a price changes instead of editing the old one.
>
> **Daniel:** And if I forget to add this year's price?
>
> **Professor Feynman:** Then the latest entry that is not in the future is used, which is what you last told it.
> With no entry at all the model is refused before a cent is spent. The limit of the picture: a timetable is wrong
> in an obvious way. A slightly wrong price is not, so check the estimate against your first real bill.
>
> **Daniel:** My prices, dated, never guessed. And nothing here applies to the local model, which is free.

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
