#!/bin/bash
set -euo pipefail

SRC=/build/virt-v2v
LIBGUESTFS=/opt/libguestfs
STAGING=/staging
SPEC=/build/virt-v2v/packaging/virt-v2v-pf9.spec
JOBS=$(nproc)

echo "==> Building libguestfs..."
git clone --depth=1 https://github.com/libguestfs/libguestfs "$LIBGUESTFS"
cd "$LIBGUESTFS"
git submodule update --init
autoreconf -fiv
./configure CFLAGS="-fPIC -g -O2"
make -j"$JOBS"

echo "==> Initialising virt-v2v submodule..."
cd "$SRC"
git config --global --add safe.directory "$SRC"
# Submodule may already be present from the COPY; init only if needed
if [ ! -f common/mldrivers/linux_bootloaders.ml ]; then
    git submodule update --init
fi

echo "==> Building virt-v2v..."
autoreconf -fiv
"$LIBGUESTFS/run" ./configure CFLAGS="-fPIC -g -O2"
"$LIBGUESTFS/run" make -j"$JOBS"

echo "==> Staging install..."
mkdir -p "$STAGING"
"$LIBGUESTFS/run" make install DESTDIR="$STAGING"

echo "==> Building RPM..."
rpmdev-setuptree
rpmbuild -bb \
    --define "_topdir /root/rpmbuild" \
    --define "BUILD_STAGING $STAGING" \
    --buildroot /root/rpmbuild/BUILDROOT \
    "$SPEC"

echo "==> RPMs produced:"
find /root/rpmbuild/RPMS -name '*.rpm' | tee /rpms-list.txt
