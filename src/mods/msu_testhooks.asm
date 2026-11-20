asar 1.90
; TEST ROM ONLY. $7F:FFF0=1 + $7F:FFF1=group: start a battle (from battletest.asm, moved to bank $D0).
; $7F:FFF2=1: inn stay like script op $17 (PlaySong 4, then 150 frames later PrepareSongResource($099D)).
lorom
assert read3($83900C) == $C540A5
org $83900C
    jml TestWait
org $D09000
TestWait:
    php
    sep #$20
    lda.b $40
-   cmp.b $40
    beq -
    lda.l $7FFFF2 : beq .battle
    cmp.b #$01 : bne .count
    lda.b #$02 : sta.l $7FFFF2
    lda.b #150 : sta.l $7FFFF3
    lda.b #$04 : jsl $8093FE              ; PlaySong(inn)
    bra .battle
.count:
    lda.l $7FFFF3 : dec : sta.l $7FFFF3 : bne .battle
    lda.b #$00 : sta.l $7FFFF2
    lda.w $099D : jsl $80969F             ; PrepareSongResource(background song)
.battle:
    lda.l $7FFFF0
    beq .done
    lda.b #$00
    sta.l $7FFFF0
    lda.l $7FFFF1
    sta.l $7FF8A4
    lda.b #$FF
    sta.l $7FF8A3
    rep #$10
    jsl $8383EB
.done:
    plp
    jml $839012                           ; RTS of FieldWaitForNextFrame (bank $83)
