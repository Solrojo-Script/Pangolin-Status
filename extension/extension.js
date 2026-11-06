import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {isClientConnected} from './status.js';

const POLL_SECONDS = 5;
const QUERY_TIMEOUT_SECONDS = 3;
const TOOLTIP_GAP = 6;
const LOCAL_CLI_PATH = '/usr/local/bin/pangolin';

export default class PangolinStatusExtension extends Extension {
    enable() {
        this._indicator = new PanelMenu.Button(0.0, 'Pangolin connected', true);
        this._indicator.add_style_class_name('pangolin-status-indicator');
        this._indicator.container.set_margin_left(4);
        this._indicator.container.set_margin_right(4);
        this._indicator.add_child(new St.Icon({
            gicon: new Gio.FileIcon({
                file: Gio.File.new_for_path(`${this.path}/pangolin.svg`),
            }),
            icon_size: 20,
            style_class: 'system-status-icon',
        }));
        this._indicator.track_hover = true;
        this._indicator.visible = false;

        this._tooltip = new St.Label({
            style_class: 'dash-label',
            visible: false,
            reactive: false,
        });
        Main.uiGroup.add_child(this._tooltip);

        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'right');
        this._indicator.connect('notify::hover', () => this._syncTooltip());

        this._cliPath = GLib.find_program_in_path('pangolin') ??
            (GLib.file_test(LOCAL_CLI_PATH, GLib.FileTest.IS_EXECUTABLE)
                ? LOCAL_CLI_PATH : null);
        this._refresh();
        this._pollId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            POLL_SECONDS,
            () => {
                this._refresh();
                return GLib.SOURCE_CONTINUE;
            }
        );
    }

    _refresh() {
        if (!this._indicator || this._process)
            return;

        if (!this._cliPath) {
            this._setConnected(false);
            return;
        }

        try {
            this._process = Gio.Subprocess.new(
                [this._cliPath, 'status', 'client', '--json'],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            );
        } catch (_) {
            this._setConnected(false);
            return;
        }

        const process = this._process;
        this._queryTimeoutId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            QUERY_TIMEOUT_SECONDS,
            () => {
                this._queryTimeoutId = null;
                if (this._process === process) {
                    this._setConnected(false);
                    process.force_exit();
                }
                return GLib.SOURCE_REMOVE;
            }
        );

        process.communicate_utf8_async(null, null, (proc, result) => {
            if (this._process !== proc)
                return;

            this._process = null;
            if (this._queryTimeoutId) {
                GLib.source_remove(this._queryTimeoutId);
                this._queryTimeoutId = null;
            }

            let connected = false;
            try {
                const [, output] = proc.communicate_utf8_finish(result);
                connected = proc.get_successful() && isClientConnected(output);
            } catch (_) {
                // A failed or incomplete query cannot confirm a connection.
            }
            this._setConnected(connected);
        });
    }

    _setConnected(connected) {
        if (!this._indicator)
            return;

        this._indicator.visible = connected;
        this._syncTooltip();
    }

    _syncTooltip() {
        if (!this._indicator || !this._indicator.visible || !this._indicator.hover) {
            this._tooltip?.hide();
            return;
        }

        this._tooltip.set({text: 'Pangolin connected', visible: true});
        const [stageX, stageY] = this._indicator.get_transformed_position();
        const monitor = Main.layoutManager.findMonitorForActor(this._indicator);
        const centeredX = stageX + (this._indicator.width - this._tooltip.width) / 2;
        const x = Math.max(monitor.x + TOOLTIP_GAP, Math.min(
            centeredX,
            monitor.x + monitor.width - this._tooltip.width - TOOLTIP_GAP
        ));
        this._tooltip.set_position(x, stageY + this._indicator.height + TOOLTIP_GAP);
    }

    disable() {
        if (this._pollId)
            GLib.source_remove(this._pollId);
        this._pollId = null;
        if (this._queryTimeoutId)
            GLib.source_remove(this._queryTimeoutId);
        this._queryTimeoutId = null;
        this._process?.force_exit();
        this._process = null;
        this._cliPath = null;
        this._tooltip?.destroy();
        this._tooltip = null;
        this._indicator?.destroy();
        this._indicator = null;
    }
}
