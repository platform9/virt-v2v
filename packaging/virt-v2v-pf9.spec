Name:           virt-v2v
Version:        2.11.8
Release:        1.pf9%{?dist}
Summary:        Convert a virtual machine to run on KVM (Platform9 build)
License:        GPLv2+
BuildArch:      x86_64
AutoReq:        no
AutoProv:       no

# --- Runtime dependencies ---
# xfsprogs: required for XFS guest migrations (libguestfs supermin appliance
#   calls xfs_repair to fix filesystem UUIDs on RHEL/CentOS 7+ VMs).
Requires:       xfsprogs

# mingw-srvany-redistributable: provides rhsrvany.exe, required by virt-v2v to
#   install Windows firstboot scripts. Without it every Windows migration aborts.
Requires:       mingw-srvany-redistributable

# reiserfs-utils: for ReiserFS guest filesystems (old SUSE/RHEL 3-4).
# jfsutils: for JFS guest filesystems (old IBM enterprise Linux).
# f2fs-tools: for F2FS guest filesystems.
# These are Recommends so install does not fail if absent from the repo.
Recommends:     reiserfs-utils
Recommends:     jfsutils
Recommends:     f2fs-tools

%description
virt-v2v converts virtual machines from foreign hypervisors to run on KVM.

This is a Platform9 patched build based on upstream 2.11.8 with the following
fixes backported:

  1. convert_linux.ml: sanitize the GRUB_DISTRIBUTOR backtick command
     substitution in /etc/default/grub before Augeas loads the file.
     Prevents a fatal aug_get: no matching node error on every Ubuntu migration.

  2. convert_linux.ml: fix crypttab aug_get failure on comment lines.
     Ubuntu 22.04 default /etc/crypttab is a header comment only; aug_match
     returned the #comment node and aug_get "#comment/target" then aborted.
     Fix: use the Augeas predicate *[target] to match real entries only.
     Backport of upstream commit 673f2d04.

This build also bundles all required runtime helpers so the RPM is
self-sufficient: rhsrvany.exe and pnp_wait.exe for Windows firstboot, and
a %post scriptlet to register filesystem tools with the libguestfs supermin
appliance.

%install
# Stage the virt-v2v install tree built by the CI workflow.
cp -a %{BUILD_STAGING}/. %{buildroot}/

# Bundle Windows firstboot helpers into /usr/share/virt-tools/.
# rhsrvany.exe  — from mingw-srvany-redistributable (installed in CI).
# pnp_wait.exe  — from the system virt-v2v package (installed in CI).
# virt-v2v looks for these at runtime in virt_tools_data_dir(); without
# rhsrvany.exe every Windows migration aborts with a fatal error.
mkdir -p %{buildroot}%{_datadir}/virt-tools
cp /usr/share/virt-tools/rhsrvany.exe %{buildroot}%{_datadir}/virt-tools/
cp /usr/share/virt-tools/pnp_wait.exe %{buildroot}%{_datadir}/virt-tools/

%files
%{_bindir}/virt-v2v
%{_bindir}/virt-v2v-in-place
%{_bindir}/virt-v2v-inspector
%{_bindir}/virt-v2v-open
%{_mandir}/man1/virt-v2v*
%{_datadir}/bash-completion/completions/virt-v2v
%{_datadir}/locale/*/LC_MESSAGES/virt-v2v.mo
%{_mandir}/ja/man1/*
%{_mandir}/uk/man1/*
%{_datadir}/virt-tools/rhsrvany.exe
%{_datadir}/virt-tools/pnp_wait.exe

%post
# Register filesystem tools with the libguestfs supermin appliance.
#
# The supermin appliance builds itself at runtime by copying files from
# packages listed in its packages file. We add filesystem tools here so
# that libguestfs can repair/inspect the corresponding guest filesystems.
# Each package is only added if it is actually installed on the host
# (Requires/Recommends above ensure this under normal dnf installs).
PKGS=/usr/lib64/guestfs/supermin.d/packages
if [ -f "$PKGS" ]; then
    for pkg in xfsprogs reiserfs-utils jfsutils f2fs-tools; do
        if rpm -q "$pkg" &>/dev/null; then
            grep -q "^${pkg}$" "$PKGS" || echo "$pkg" >> "$PKGS"
        fi
    done
fi

%changelog
* Wed Jun 18 2026 Platform9 <eng@platform9.com> - 2.11.8-1.pf9
- Bundle rhsrvany.exe and pnp_wait.exe for Windows firstboot support
- Add Requires: xfsprogs, mingw-srvany-redistributable
- Add Recommends: reiserfs-utils, jfsutils, f2fs-tools
- Add %post scriptlet to register filesystem tools with supermin appliance
- Backport: fix crypttab aug_get failure on comment lines (use *[target] predicate)
- Backport: sanitize GRUB_DISTRIBUTOR backtick in /etc/default/grub
- Backport: add /usr/sbin/grub-mkconfig to grub binary search list
