#!/usr/bin/env python3
"""A read-only Pangolin client status window; no server credentials are displayed."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit

ASSETS = Path(__file__).resolve().parent
APP_ID = 'io.github.solrojo.PangolinStatus'


def parse_status(output):
    """Accept the CLI's optional update notice before its JSON response."""
    try:
        status = json.loads(output[output.index('{'):output.rindex('}') + 1])
    except (ValueError, json.JSONDecodeError):
        return {}
    return status if isinstance(status, dict) else {}


def active_server(status, config_dir=None):
    """Read only the active account's endpoint; never return tokens or secrets."""
    root = config_dir or Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'pangolin'
    try:
        store = json.loads((root / 'accounts.json').read_text())
        active_id = store.get('activeUserId', store.get('activeuserid'))
        account = store.get('accounts', {}).get(active_id, {})
        if status.get('orgId') and account.get('orgId') != status['orgId']:
            return None
        host = account.get('host')
        if not isinstance(host, str) or not host:
            return None
        endpoint = urlsplit(host if '://' in host else 'https://' + host)
        if endpoint.scheme not in ('http', 'https') or not endpoint.hostname:
            return None
        return endpoint.hostname, endpoint.port or (443 if endpoint.scheme == 'https' else 80)
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def tcp_latency(endpoint):
    """Time a TCP connection to the configured server, excluding DNS lookup."""
    if not endpoint:
        return None
    try:
        addresses = socket.getaddrinfo(*endpoint, type=socket.SOCK_STREAM)
        for family, kind, protocol, _, address in addresses:
            try:
                with socket.socket(family, kind, protocol) as connection:
                    connection.settimeout(2)
                    start = time.monotonic()
                    connection.connect(address)
                    return round((time.monotonic() - start) * 1000, 1)
            except OSError:
                continue
    except (OSError, ValueError):
        pass
    return None


def client_snapshot(cli):
    snapshot = {'connected': False, 'name': socket.gethostname(), 'ip': None, 'latency_ms': None}
    try:
        result = subprocess.run([cli, 'status', 'client', '--json'],
                                capture_output=True, text=True, timeout=3, check=True)
        status = parse_status(result.stdout)
    except (OSError, subprocess.SubprocessError):
        return snapshot
    snapshot['connected'] = (status.get('connected') is True and
                             status.get('registered') is True and
                             status.get('terminated') is False)
    if not snapshot['connected']:
        return snapshot
    settings = status.get('networkSettings') or {}
    try:
        snapshot['ip'] = str(ipaddress.ip_interface(settings.get('tunnelIP', '')).ip)
    except (ValueError, TypeError):
        pass
    snapshot['latency_ms'] = tcp_latency(active_server(status))
    return snapshot


def run_window(cli):
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

    class StatusWindow(Adw.ApplicationWindow):
        def __init__(self, application):
            super().__init__(application=application, title='Pangolin', resizable=False)
            self._process = None
            self._timeout = 0
            self._closed = False
            self._poll = 0
            self.set_default_size(380, -1)
            self.add_css_class('pangolin-client-window')
            layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            header = Adw.HeaderBar(show_start_title_buttons=False, show_end_title_buttons=False)
            title = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            title.append(Gtk.Image.new_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(str(ASSETS / 'pangolin.svg')))))
            title.get_first_child().set_pixel_size(20)
            title.append(Gtk.Label(label='Pangolin', css_classes=['heading']))
            header.set_title_widget(title)
            layout.append(header)
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22,
                              margin_start=28, margin_end=28, margin_top=20, margin_bottom=28)
            wordmark = Gtk.Picture.new_for_filename(str(ASSETS / 'pangolin-wordmark.png'))
            wordmark.set_content_fit(Gtk.ContentFit.CONTAIN)
            wordmark.set_size_request(256, 64)
            wordmark.set_halign(Gtk.Align.CENTER)
            content.append(wordmark)
            state = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            self.dot = Gtk.Label(label='●', css_classes=['pangolin-state-dot'])
            self.state_label = Gtk.Label(label='Checking…', css_classes=['heading'])
            state.append(self.dot)
            state.append(self.state_label)
            content.append(state)
            details = Gtk.Grid(column_spacing=24, row_spacing=14, hexpand=True)
            self.values = {}
            for row, (key, caption) in enumerate([('name', 'Client'), ('ip', 'IP'), ('latency_ms', 'Server latency')]):
                label = Gtk.Label(label=caption, xalign=0, css_classes=['dim-label'])
                value = Gtk.Label(label='—', xalign=1, hexpand=True, selectable=False,
                                  ellipsize=Pango.EllipsizeMode.MIDDLE, max_width_chars=28)
                details.attach(label, 0, row, 1, 1)
                details.attach(value, 1, row, 1, 1)
                self.values[key] = value
            self.values['name'].set_tooltip_text('Local client hostname')
            self.values['ip'].set_tooltip_text('Pangolin tunnel IP reported by the client')
            self.values['latency_ms'].set_tooltip_text('TCP connection to the configured Pangolin server, excluding DNS lookup. Not a peer or tunnel RTT.')
            content.append(details)
            layout.append(content)
            layout.append(Gtk.Separator())
            close = Gtk.Button(label='Close', css_classes=['flat'], height_request=48)
            close.connect('clicked', lambda *_: self.close())
            layout.append(close)
            self.set_content(layout)
            escape = Gtk.EventControllerKey()
            escape.connect('key-pressed', lambda _c, key, *_: (self.close() or True)
                           if key == Gdk.KEY_Escape else False)
            self.add_controller(escape)
            self.connect('close-request', self._shutdown)
            self._refresh()
            self._poll = GLib.timeout_add_seconds(5, self._refresh)

        def _refresh(self):
            if self._closed:
                return GLib.SOURCE_REMOVE
            if self._process:
                return GLib.SOURCE_CONTINUE
            try:
                proc = Gio.Subprocess.new([sys.executable, str(ASSETS / 'pangolin-window.py'),
                                           '--cli', cli, '--json'],
                                          Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
            except GLib.Error:
                self._update({})
                return GLib.SOURCE_CONTINUE
            self._process = proc
            self._timeout = GLib.timeout_add_seconds(8, self._query_timeout, proc)
            proc.communicate_utf8_async(None, None, self._finished)
            return GLib.SOURCE_CONTINUE

        def _query_timeout(self, proc):
            self._timeout = 0
            if self._process is proc:
                proc.force_exit()
            return GLib.SOURCE_REMOVE

        def _finished(self, proc, result):
            if self._closed or self._process is not proc:
                return
            self._process = None
            if self._timeout:
                GLib.source_remove(self._timeout)
                self._timeout = 0
            try:
                _, output, _ = proc.communicate_utf8_finish(result)
                snapshot = json.loads(output) if proc.get_successful() else {}
            except (GLib.Error, ValueError, TypeError):
                snapshot = {}
            self._update(snapshot)

        def _update(self, snapshot):
            connected = snapshot.get('connected') is True
            self.state_label.set_label('Connected' if connected else 'Disconnected')
            self.dot.remove_css_class('connected')
            self.dot.remove_css_class('disconnected')
            self.dot.add_css_class('connected' if connected else 'disconnected')
            self.values['name'].set_label(snapshot.get('name') or socket.gethostname())
            self.values['ip'].set_label(snapshot.get('ip') or 'Unavailable')
            latency = snapshot.get('latency_ms')
            self.values['latency_ms'].set_label(f'{latency:.1f} ms' if latency is not None else 'Unavailable')

        def _shutdown(self, *_):
            self._closed = True
            for source in (self._poll, self._timeout):
                if source:
                    GLib.source_remove(source)
            self._poll = self._timeout = 0
            if self._process:
                self._process.force_exit()
                self._process = None
            return False

    app = Adw.Application(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def activate(application):
        if application.get_active_window():
            application.get_active_window().present()
            return
        Gtk.Window.set_default_icon_name(APP_ID)
        # Use a dark window so the official white wordmark stays readable.
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        css = Gtk.CssProvider()
        css.load_from_data(b'.pangolin-state-dot { color: #9a90ad; } .pangolin-state-dot.connected { color: #57e389; } .pangolin-state-dot.disconnected { color: #f66151; }')
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        StatusWindow(application).present()

    app.connect('activate', activate)
    return app.run([])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', default=shutil.which('pangolin') or '/usr/local/bin/pangolin')
    parser.add_argument('--json', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.json:
        print(json.dumps(client_snapshot(args.cli)))
        return 0
    return run_window(args.cli)


if __name__ == '__main__':
    raise SystemExit(main())
