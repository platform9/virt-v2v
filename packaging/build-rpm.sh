#!/bin/bash
set -euo pipefail

SRC=/build/virt-v2v
LIBGUESTFS=/opt/libguestfs
STAGING=/staging
SPEC=/build/virt-v2v/packaging/virt-v2v-pf9.spec
JOBS=$(nproc)

echo "==> Building pinned libnbd..."
# Pin to the libnbd version vJailbreak ships at runtime (1.25.5).  The
# distro libnbd/ocaml-libnbd is newer, and a virt-v2v built against it needs
# symbols (e.g. nbd_connect_read_memory) the runtime libnbd lacks.
dnf remove -y 'ocaml-libnbd*' || true
ocamlfind remove nbd 2>/dev/null || true
curl -fsSL -o /tmp/libnbd.tar.gz \
    https://download.libguestfs.org/libnbd/1.25-development/libnbd-1.25.5.tar.gz
mkdir -p /tmp/libnbd-src
tar -xzf /tmp/libnbd.tar.gz -C /tmp/libnbd-src --strip-components=1
(
    cd /tmp/libnbd-src
    ./configure --prefix=/usr --libdir=/usr/lib64 \
        --disable-golang --disable-rust --disable-python --disable-fuse
    make -j"$JOBS"
    make install
    ldconfig
)
test "$(pkg-config --modversion libnbd)" = "1.25.5"

echo "==> Building libguestfs..."
# Pin to the libguestfs version vJailbreak ships at runtime (1.59.8).
# Building against master produces a virt-v2v that needs newer symbols
# (e.g. guestfs_kill_procs) than the runtime library has.
git clone --depth=1 --branch v1.59.8 https://github.com/libguestfs/libguestfs "$LIBGUESTFS"
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
"$LIBGUESTFS/run" ./configure CFLAGS="-fPIC -g -O2" --prefix=/usr
"$LIBGUESTFS/run" make -j"$JOBS"

echo "==> Staging install..."
mkdir -p "$STAGING"
"$LIBGUESTFS/run" make install DESTDIR="$STAGING"

echo "==> Verifying symbols resolve against pinned libraries..."
nbdlib=$(find /usr/lib64 -maxdepth 1 -name 'libnbd.so.0*' -type f | head -1)
gflib=$(find "$LIBGUESTFS/lib/.libs" -name 'libguestfs.so.0*' -type f | head -1)
have=$( { nm -D --defined-only "$nbdlib"; nm -D --defined-only "$gflib"; } \
        | awk '{print $3}' | sed 's/@.*//' | sort -u )
status=0
for b in "$STAGING"/usr/bin/virt-v2v*; do
    [ -f "$b" ] && [ -x "$b" ] || continue
    need=$(nm -D --undefined-only "$b" | awk '{print $2}' | sed 's/@.*//' \
           | grep -E '^(nbd_|guestfs_)' | sort -u || true)
    missing=$(comm -23 <(echo "$need") <(echo "$have") || true)
    if [ -n "$missing" ]; then
        echo "ERROR: $b needs symbols missing from the pinned libraries:"
        echo "$missing"
        status=1
    fi
done
[ "$status" -eq 0 ] || exit 1

echo "==> Building RPM..."
rpmdev-setuptree
rpmbuild -bb \
    --define "_topdir /root/rpmbuild" \
    --define "BUILD_STAGING $STAGING" \
    --buildroot /root/rpmbuild/BUILDROOT \
    "$SPEC"

echo "==> RPMs produced:"
find /root/rpmbuild/RPMS -name '*.rpm' | tee /rpms-list.txt
