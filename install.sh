#!/bin/bash
# Install the applet source and system discovery files. Does not change power modes.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
stage_root=${DESTDIR:-}
if [[ -n "$stage_root" && "$stage_root" != /* ]]; then
    echo 'DESTDIR must be an absolute staging path.' >&2
    exit 1
fi
if [[ -z "$stage_root" ]]; then
    if (( EUID != 0 )); then
        echo 'Run with sudo or pkexec, or set DESTDIR for an unprivileged staging install.' >&2
        exit 1
    fi
    /usr/bin/python3 - <<'PY'
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('MatePanelApplet', '4.0')
from gi.repository import Gtk, MatePanelApplet
PY
fi
install_dir="${stage_root%/}/opt/mate-power-profile-switcher"
files=(power-profile-switcher.py panel-item.py install.sh uninstall.sh configure-tuned.sh
       README.md LICENSE examples/tuned/legion-max-power/tuned.conf
       org.mate.panel.applet.LocalPowerProfilesAppletFactory.service
       org.mate.panel.LocalPowerProfilesApplet.mate-panel-applet)
for name in "${files[@]}"; do
    test -f "$source_dir/$name" || { echo "Missing source file: $name" >&2; exit 1; }
done
install -d -m 755 "$install_dir"
if [[ "$source_dir" != "$install_dir" ]]; then
    for name in "${files[@]}"; do
        install -D -m 644 "$source_dir/$name" "$install_dir/$name"
    done
fi
chmod 755 "$install_dir/"{power-profile-switcher.py,panel-item.py,install.sh,uninstall.sh,configure-tuned.sh}
install -D -m 644 "$install_dir/org.mate.panel.applet.LocalPowerProfilesAppletFactory.service" "${stage_root%/}/usr/share/dbus-1/services/org.mate.panel.applet.LocalPowerProfilesAppletFactory.service"
install -D -m 644 "$install_dir/org.mate.panel.LocalPowerProfilesApplet.mate-panel-applet" "${stage_root%/}/usr/share/mate-panel/applets/org.mate.panel.LocalPowerProfilesApplet.mate-panel-applet"
printf 'Installed in %s\n' "$install_dir"
if [[ -z "$stage_root" ]]; then
    echo 'As your desktop user, run: /usr/bin/python3 /opt/mate-power-profile-switcher/panel-item.py'
fi
