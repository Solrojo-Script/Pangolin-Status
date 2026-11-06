# Pangolin Status

A GNOME Shell extension that shows a Pangolin icon in the top bar while the Pangolin CLI client is connected. Hover over the icon to see the connection status.

The extension reads the existing local CLI session through `pangolin status client --json`. It checks immediately when enabled and every five seconds after that. Configure and connect the client separately.

## Requirements

- GNOME Shell 46, the version declared by the extension.
- The Pangolin CLI on GNOME Shell's `PATH` or at `/usr/local/bin/pangolin`.
- A configured client that supports `pangolin status client --json`.

## Installation

1. Download or clone this repository and open a terminal in its directory.
2. Run the installer as your regular desktop user.

   ```sh
   ./install.sh
   ```

3. Log out and back in so GNOME Shell loads the extension files.
4. Enable **Pangolin Status** in the **Extensions** app, or run:

   ```sh
   gnome-extensions enable pangolin-status@solrojo
   ```

5. Connect your Pangolin client. The icon appears when the CLI reports a connected, registered session that has not been terminated.

To update the extension, run the installer again and log out and back in.

## Troubleshooting

If the icon is missing, check that the extension is enabled and run this command locally to check the client status:

```sh
pangolin status client --json
```

## Uninstallation

```sh
gnome-extensions disable pangolin-status@solrojo
rm -r -- "${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/pangolin-status@solrojo"
```
