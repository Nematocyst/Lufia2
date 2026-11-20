asar 1.90
; TEST ONLY: when a battle background loads, fill CGRAM rows 4-7 (buffer $0320 and master $7F:F1DB)
; with loud test colours, to see whether anything else displays them and whether they survive.
; Hooks the same place as gradient.asm ($81:BAB9); do not combine with it.
lorom

assert read4($81BAB9) == $D91401A9
org $81BAB9
    jml PalTest

org $E0FA00
PalTest:
    php
    rep #$30
    ldx.w #$0000
-   lda.l Colours,x
    sta.l $7E0320+$80,x             ; rows 4-7 in the CGRAM buffer
    sta.l $7FF1DB+$80,x             ; and in the master copy
    inx : inx
    cpx.w #$0080
    bne -
    sep #$20
    lda.b #$80 : tsb.b $73          ; upload CGRAM at the next NMI
    plp
    ; the original tail
    lda.b #$01 : trb.b $D9
    lda.b #$00 : sta.l $7E1B17
    lda.l $7E11E1
    bne +
    jsl $85A701
+   rtl

Colours:                            ; row 4 red ramp, 5 green, 6 blue, 7 yellow
    !r = 0
    while !r < 4
        !i = 0
        while !i < 16
            if !r == 0
                dw (!i*2)
            elseif !r == 1
                dw (!i*2)<<5
            elseif !r == 2
                dw (!i*2)<<10
            else
                dw (!i*2)|((!i*2)<<5)
            endif
            !i #= !i+1
        endwhile
        !r #= !r+1
    endwhile
