#!/bin/sh
# Build the standalone Iris Treasures patch (and a combined ROM with Restored & Extended).
set -e
cd "$(dirname "$0")"
ROOT=..
ASAR=$ROOT/ext/asar/build/asar/bin/asar
python3 -c "
d=open('$ROOT/rom/orig.smc','rb').read(); o=(0x94&0x7F)*0x8000+(0xEEA0-0x8000)
open('blue_table.bin','wb').write(d[o:o+0x52])"
python3 gruberik_dialogue.py
mkdir -p out
cp $ROOT/rom/orig.smc out/lufia2_iris.sfc
$ASAR --fix-checksum=on --symbols=wla iris.asm out/lufia2_iris.sfc
python3 mkpatch.py $ROOT/rom/orig.smc out/lufia2_iris.sfc out/lufia2_iris
cp out/lufia2_mod.sfc out/lufia2_mod_iris.sfc
$ASAR --fix-checksum=on iris.asm out/lufia2_mod_iris.sfc
python3 mkpatch.py $ROOT/rom/orig.smc out/lufia2_mod_iris.sfc out/lufia2_restored_iris
python3 test_iris.py out/lufia2_iris.sfc
python3 test_iris.py out/lufia2_mod_iris.sfc out/lufia2_mod.sfc | tail -1
