The whole stack runs on a local minikube cluster: an optional in-cluster Postgres and RabbitMQ in the Helm chart, a
`deploy/minikube/up.sh` and `down.sh`, and `docs/MINIKUBE.md` with the steps and the traps. The image now includes the `s3`
extra, so the S3 artifact store works from the container. Compatible: both in-cluster services are off by default.
