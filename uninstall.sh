#!/bin/bash
# Remove the applet's known files, preserving TuneD settings and other files.
set -euo pipefail
stage_root=${DESTDIR:-}
if [[ -n "$stage_root" && "$stage_root" != /* ]]; then
    echo 'DESTDIR must be an absolute staging path.' >&2
    exit 1
fi
if [[ -z "$stage_root" && "$EUID" != 0 ]]; then
    echo 'Run this uninstaller with sudo or pkexec.' >&2
    exit 1
fi
install_dir="${stage_root%/}/opt/mate-power-profile-switcher"
rm -f -- "${stage_root%/}/usr/share/dbus-1/services/org.mate.panel.applet.LocalPowerProfilesAppletFactory.service" \
          "${stage_root%/}/usr/share/mate-panel/applets/org.mate.panel.LocalPowerProfilesApplet.mate-panel-applet"
for name in power-profile-switcher.py panel-item.py install.sh uninstall.sh configure-tuned.sh \
            README.md LICENSE org.mate.panel.applet.LocalPowerProfilesAppletFactory.service \
            org.mate.panel.LocalPowerProfilesApplet.mate-panel-applet examples/tuned/legion-max-power/tuned.conf; do
    rm -f -- "$install_dir/$name"
done
for directory in examples/tuned/legion-max-power examples/tuned examples ''; do
    if [[ -d "$install_dir/$directory" ]]; then
        rmdir -- "$install_dir/$directory" 2>/dev/null || true
    fi
done
echo 'Removed applet files. Any extra files and TuneD settings have been preserved.'
