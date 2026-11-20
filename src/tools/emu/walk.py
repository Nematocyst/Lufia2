from emu_iris import *
def walk_to(emu, tx, ty, ghost=True):
    r=emu.ram
    if ghost: r[0x057C]=0xFF
    for axis,target,neg,pos in ((1,ty,'UP','DOWN'),(0,tx,'LEFT','RIGHT')):
        for _ in range(400):
            cur=(r[0x6BA],r[0x6E2])[axis]
            if cur==target: break
            emu.held={'B', pos if target>cur else neg} if ghost else {pos if target>cur else neg}
            emu.run(2)
        emu.held=set(); emu.run(20)
    r[0x057C]=0
    return (r[0x6BA],r[0x6E2])
def talk(emu, face):
    emu.press(face,hold=2,gap=10); emu.press('A',hold=3,gap=30)
