# Kustomize overlays

`base/resources.yaml` is generated from the Helm chart's defaults by `render-base.sh`, so the two renders agree; a test
fails if the committed base has drifted from the chart. `overlays/dev` and `overlays/prod` set the namespace, the
replica counts and the image tag. Apply one with:

```bash
kubectl apply -k deploy/kustomize/overlays/prod
```

The base expects a Secret named `ei-secrets` with the keys listed in `docs/DEPLOYMENT.md`, in the overlay's namespace.
The image is a placeholder repository; set the overlay's `images` entry to the registry you use.
