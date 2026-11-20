#!/bin/sh
# Build the mod ROM and patches from the clean US ROM.
set -e
cd "$(dirname "$0")"
ROOT=..
ASAR=$ROOT/ext/asar/build/asar/bin/asar
python3 -c "
import sys; d=open('$ROOT/rom/orig.smc','rb').read(); o=(0x97&0x7F)*0x8000+(0xC493-0x8000)
open('region_0_16.bin','wb').write(d[o:o+170])"
mkdir -p out
cp $ROOT/rom/orig.smc out/lufia2_mod.sfc
$ASAR --fix-checksum=on --symbols=wla --symbols-path=out/l2mod.sym l2mod.asm out/lufia2_mod.sfc
python3 mkpatch.py $ROOT/rom/orig.smc out/lufia2_mod.sfc out/lufia2_restored
# optional: RETRY from the start
cp $ROOT/rom/orig.smc out/lufia2_retry.sfc
$ASAR --fix-checksum=on retry.asm out/lufia2_retry.sfc
python3 mkpatch.py $ROOT/rom/orig.smc out/lufia2_retry.sfc out/lufia2_retry
# RETRY combined and add-on patches (needs out/lufia2_iris.sfc and out/lufia2_mod_iris.sfc from build_iris.sh)
if [ -f out/lufia2_mod_iris.sfc ]; then
  for base in mod iris mod_iris; do cp out/lufia2_$base.sfc out/${base}_retry.sfc; $ASAR --fix-checksum=on retry.asm out/${base}_retry.sfc; done
  python3 mkpatch.py $ROOT/rom/orig.smc out/mod_iris_retry.sfc out/lufia2_restored_iris_retry
  python3 mkpatch.py out/lufia2_mod_iris.sfc out/mod_iris_retry.sfc out/addon_retry_for_restored_iris
  python3 mkpatch.py out/lufia2_mod.sfc out/mod_retry.sfc out/addon_retry_for_restored
  python3 mkpatch.py out/lufia2_iris.sfc out/iris_retry.sfc out/addon_retry_for_iris
fi
