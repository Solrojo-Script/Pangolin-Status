#!/bin/sh
set -eu

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/extension
uuid=pangolin-status@solrojo
destination=${XDG_DATA_HOME:-"$HOME/.local/share"}/gnome-shell/extensions/$uuid

if [ "$(id -u)" -eq 0 ]; then
    printf '%s\n' 'Run the installer as your regular GNOME user.' >&2
    exit 1
fi

if ! command -v pangolin >/dev/null 2>&1 && [ ! -x /usr/local/bin/pangolin ]; then
    printf '%s\n' 'Pangolin CLI was not found. See the requirements in the README.' >&2
    exit 1
fi

install -d "$destination"
install -m 644 "$source_dir/metadata.json" "$source_dir/pangolin.svg" \
    "$source_dir/status.js" "$destination/"
install -m 644 "$source_dir/extension.js" "$destination/"
printf 'Installed in %s\n' "$destination"
printf '%s\n' 'Log out and back in, then enable Pangolin Status in the Extensions app.'
