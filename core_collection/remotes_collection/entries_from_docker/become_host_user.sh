#!/bin/sh
# become_host_user.sh <uid> <gid> <cmd...>   -- must start as root inside the container.
# Runs <cmd> as the given numeric uid:gid, whatever names (if any) the image already has for them.
set -e
uid=$1; gid=$2; shift 2

[ "$uid" = 0 ] && exec "$@"        # host user is root: nothing to change

# Make sure the numbers resolve to *some* name (sudo, getpass, ssh need a passwd entry); reuse existing ones.
if ! getent group "$gid" >/dev/null; then
    gname=axs_root; getent group "$gname" >/dev/null && gname="axs_root_$gid"
    groupadd -g "$gid" "$gname"
fi
if ! getent passwd "$uid" >/dev/null; then
    uname=axs_root; getent passwd "$uname" >/dev/null && uname="axs_root_$uid"
    useradd -u "$uid" -g "$gid" -M -d /home/axs_root -s /bin/sh "$uname"
fi
uname=$(getent passwd "$uid" | cut -d: -f1)

# Our own home, owned by us, regardless of what existed before:
mkdir -p /home/axs_root && chown "$uid:$gid" /home/axs_root

# Root powers via sudo, keyed by uid (works even if the uid's first name is e.g. 'ubuntu'):
if [ -d /etc/sudoers.d ]; then
    echo "#$uid ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/axs_root && chmod 440 /etc/sudoers.d/axs_root
fi

export HOME=/home/axs_root USER="$uname" LOGNAME="$uname"
exec setpriv --reuid="$uid" --regid="$gid" --clear-groups -- "$@"
