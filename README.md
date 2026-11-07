# Pangolin Status

A GNOME Shell extension that shows a Pangolin icon in the top bar while the Pangolin CLI client is connected. Hover over the icon to see the connection status. Click it to open a compact status window with a Pangolin icon in the title bar, the official Pangolin wordmark, a green Connected indicator, the client hostname, tunnel IP, and server latency.

The status window refreshes every five seconds and changes to Disconnected if the client disconnects. Close the window with **Close** or **Esc**. It does not change your Pangolin connection.

The extension reads the existing local CLI session through `pangolin status client --json`. It checks immediately when enabled and every five seconds after that. Configure and connect the client separately.

## Client details and latency

- **Client** is the local computer hostname, not the account username.
- **IP** is `networkSettings.tunnelIP` reported by the CLI, without its subnet suffix.
- **Server latency** times a TCP connection to the active account's configured Pangolin server, excluding DNS lookup. It is not the RTT to a peer, VPN site, or exit node. No authentication is sent for this measurement. If the endpoint cannot be determined or reached, the window shows **Unavailable**.
- The helper reads the selected account locally from `~/.config/pangolin/accounts.json` (or `$XDG_CONFIG_HOME/pangolin/accounts.json`) only to locate its server. No server address, account identifier, credential, or token is included in this repository, the status output, or the window.
- Data queries run in a separate process with a deadline, so they do not block GNOME Shell or the window.

The icon and wordmark come from the [official Pangolin brand assets](https://github.com/fosrl/pangolin/tree/main/public/logo). Pangolin is an upstream project; this extension is independently maintained.

## Requirements

- Python 3 with PyGObject, GTK 4, and libadwaita (`python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1` on Zorin OS/Ubuntu).
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

The installer also registers a hidden desktop entry and the Pangolin icon so GNOME can identify the status window. This does not add an extra launcher to Wofi.

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
rm -f -- "${XDG_DATA_HOME:-$HOME/.local/share}/applications/io.github.solrojo.PangolinStatus.desktop"
rm -f -- "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps/io.github.solrojo.PangolinStatus.svg"
```
