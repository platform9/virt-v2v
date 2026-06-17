Name:           virt-v2v
Version:        2.11.8
Release:        1.pf9%{?dist}
Summary:        Convert a virtual machine to run on KVM (Platform9 build)
License:        GPLv2+
BuildArch:      x86_64
AutoReq:        no
AutoProv:       no

%description
virt-v2v converts virtual machines from foreign hypervisors to run on KVM.

This is a Platform9 patched build based on upstream 2.11.8 with two
Ubuntu 22.04 migration fixes backported:

  1. linux_bootloaders.ml: add /usr/sbin/grub-mkconfig to the grub binary
     search list. Ubuntu 22.04 ships the binary at that path (no '2' suffix).

  2. convert_linux.ml: sanitize the GRUB_DISTRIBUTOR backtick command
     substitution in /etc/default/grub before Augeas loads the file.
     This prevents a fatal aug_get: no matching node error that aborted
     every Ubuntu VM migration.

%install
# The build script runs make install DESTDIR=... --prefix=/usr
cp -a %{BUILD_STAGING}/. %{buildroot}/

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

%changelog
* Thu Jun 01 2026 Platform9 <eng@platform9.com> - 2.11.8-1.pf9
- Backport: add /usr/sbin/grub-mkconfig to grub binary search list
- Backport: sanitize GRUB_DISTRIBUTOR backtick in /etc/default/grub
