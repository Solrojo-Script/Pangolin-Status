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

python3 - <<'PY'
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk
PY

install -d "$destination"
install -m 644 "$source_dir/metadata.json" "$source_dir/pangolin.svg" \
    "$source_dir/status.js" "$source_dir/stylesheet.css" \
    "$source_dir/pangolin-window.py" "$source_dir/pangolin-wordmark.png" "$destination/"
install -m 644 "$source_dir/extension.js" "$destination/"
python3 - "$destination" <<'PY'
import os
from pathlib import Path
import shutil
import sys
destination = Path(sys.argv[1])
data = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
applications = data / 'applications'
icons = data / 'icons/hicolor/scalable/apps'
applications.mkdir(parents=True, exist_ok=True)
icons.mkdir(parents=True, exist_ok=True)
shutil.copy2(destination / 'pangolin.svg', icons / 'io.github.solrojo.PangolinStatus.svg')
helper = str(destination / 'pangolin-window.py')
for character in ('\\', '"', '`', '$'):
    helper = helper.replace(character, '\\' + character)
(applications / 'io.github.solrojo.PangolinStatus.desktop').write_text(
    '[Desktop Entry]\nType=Application\nName=Pangolin Status\n'
    'Icon=io.github.solrojo.PangolinStatus\nNoDisplay=true\nTerminal=false\n'
    f'Exec=python3 "{helper}"\n')
PY
printf 'Installed in %s\n' "$destination"
printf '%s\n' 'Log out and back in, then enable Pangolin Status in the Extensions app.'
