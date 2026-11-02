#!/bin/bash
# Optional setup for firmware that exposes a real max-power mode.
set -euo pipefail
if (( EUID != 0 )); then
    echo 'Run this optional setup with sudo or pkexec.' >&2
    exit 1
fi
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
test -x /usr/sbin/tuned-adm
test -f /etc/tuned/ppd.conf
/usr/bin/python3 - <<'PY'
from pathlib import Path
import configparser
choices = Path('/sys/firmware/acpi/platform_profile_choices').read_text().split()
if 'max-power' not in choices:
    raise SystemExit('This firmware does not advertise max-power; use standard Performance instead.')
config = configparser.ConfigParser()
config.read('/etc/tuned/ppd.conf')
if not config.has_section('profiles') or not config.has_section('main'):
    raise SystemExit('Unexpected TuneD PPD configuration; no changes made.')
PY
test ! -e /etc/tuned/profiles/legion-max-power || {
    echo 'The legion-max-power profile already exists; inspect it before applying setup again.' >&2
    exit 1
}
backup_dir=$(mktemp -d /etc/tuned/before-max-power.XXXXXXXX)
chmod 700 "$backup_dir"
for name in active_profile profile_mode ppd.conf ppd_base_profile; do
    if [[ -e "/etc/tuned/$name" ]]; then
        cp -a "/etc/tuned/$name" "$backup_dir/$name"
    fi
done
systemctl is-enabled tuned.service > "$backup_dir/tuned-enabled-state" || true
printf 'Previous configuration saved in %s\n' "$backup_dir"
install -D -m 644 "$source_dir/examples/tuned/legion-max-power/tuned.conf" /etc/tuned/profiles/legion-max-power/tuned.conf
systemctl stop tuned-ppd.service
trap 'systemctl start tuned-ppd.service' EXIT
/usr/bin/python3 - <<'PY'
from pathlib import Path
import re
path = Path('/etc/tuned/ppd.conf')
lines = path.read_text().splitlines(keepends=True)
section = ''
updated = set()
for index, line in enumerate(lines):
    match = re.match(r'\s*\[([^]]+)\]', line)
    if match:
        section = match.group(1).strip()
    if section == 'main' and re.match(r'\s*default\s*=', line):
        lines[index] = 'default=performance\n'
        updated.add('default')
    if section in ('profiles', 'battery') and re.match(r'\s*performance\s*=', line):
        lines[index] = 'performance=legion-max-power\n'
        updated.add(section)
if 'default' not in updated:
    index = next(i for i, line in enumerate(lines) if re.match(r'\s*\[main\]', line))
    lines.insert(index + 1, 'default=performance\n')
if 'profiles' not in updated:
    index = next(i for i, line in enumerate(lines) if re.match(r'\s*\[profiles\]', line))
    lines.insert(index + 1, 'performance=legion-max-power\n')
path.write_text(''.join(lines))
Path('/etc/tuned/ppd_base_profile').write_text('performance\n')
PY
systemctl enable --now tuned.service
/usr/sbin/tuned-adm profile legion-max-power
systemctl start tuned-ppd.service
trap - EXIT
test "$(cat /sys/firmware/acpi/platform_profile)" = max-power
echo 'Max Power configured and selected. Reload the applet to update its label.'
