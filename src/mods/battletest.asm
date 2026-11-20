asar 1.90
; TEST ROM ONLY: start a battle on demand from the emulator.
; Write a monster group id to $7F:FFF1 and $01 to $7F:FFF0 while on a field map;
; the next field frame starts a scripted battle (like script op $53) with that group.
; Uses $83:FFBA-$83:FFFF (unused filler in the original ROM).
lorom

FieldBattleTransition = $8383EB

assert read3($83900C) == $C540A5            ; FieldWaitForNextFrame: LDA $40 / CMP $40 / BEQ / RTS
org $83900C
    jmp BattleTestWait

org $83FFBA
BattleTestWait:
    php
    sep #$20
    lda.b $40
-   cmp.b $40
    beq -
    lda.l $7FFFF0
    beq .done
    lda.b #$00
    sta.l $7FFFF0
    lda.l $7FFFF1
    sta.l $7FF8A4
    lda.b #$FF
    sta.l $7FF8A3
    rep #$10
    jsl FieldBattleTransition
.done:
    plp
    rts
assert pc() <= $840000
