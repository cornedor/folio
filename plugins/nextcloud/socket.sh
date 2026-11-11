# Where the Nextcloud client listens, for `ask` and `watch` to read in.
# Without XDG_RUNTIME_DIR the client falls back as Qt does.
socket="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}/runtime-$USER}/Nextcloud/socket"
