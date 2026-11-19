The `toolchain` CI job caches the downloaded TeX packages and downloads them in short, retried attempts, because the runner's mirror sometimes throttled a connection until the job hit its time limit.
