# engineering-influence-sdk

A small typed Python client for the REST API of
[engineering-influence](https://github.com/adammatthewsteinberger/engineering-influence), the
autonomous book-writing pipeline (fiction and non-fiction) that produces KDP-ready
self-publishing packages, with a synchronous and an asynchronous flavour.

```python
from engineering_influence_sdk import EngineeringInfluenceClient

client = EngineeringInfluenceClient("https://pipeline.example.com", api_key="...")
job = client.start_pipeline("my-book", "My Book", ("Evidence first.",), ("thesis", "book"))
client.close()
```

`AsyncEngineeringInfluenceClient` has the same methods, awaited. The key is sent as
`Authorization: Bearer <key>`.

Requires Python 3.12 or newer. Licensed under MIT.
