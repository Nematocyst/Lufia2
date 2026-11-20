asar 1.90
; Lufia II (US) — random battle-background variants, v2 (2026-11-06). Replaces variants_patch.py.
; Needs a bbg_build layout-v2 ROM (record table at $DF:8000, 1024 records x 4 bytes).
;
; Each background id ($00-$3F, as set by scripts / overworld / Ancient Cave) can have a list of
; up to 255 alternate RECORDS (16-bit record numbers, so pictures beyond id $3F are reachable).
; Every battle picks one of (the id's own record + the alternates) at random: game RNG + play-time
; frames and seconds, scaled with the hardware multiplier (same as v1).
;
; Hooks in BattleBackgroundPrepare:
;   $81:B9C8  LDA $11E1 / CMP #$18      -> JSL VariantPick2 / NOP   (returns A = id, B = 0, flags of
;                                                                     CMP #$18, Y = 4 x record)
;   $81:B9D2  ASL / ASL / TAX            -> TYX / NOP / NOP           (X = 4 x record for the 4 record
;                                                                     reads; X is reloaded right after)
; $11E1 keeps the original id (the desert-slot check in bgext.asm uses it).
;
; Table at $DF:F600 (written by build_bg3.py, not here): 64 words = offset of each id's list from
; $DF:F600 (0 = no alternates); list = count byte, then count x 16-bit record numbers.
lorom

!VT = $DFF600
!RandomByte = $8082C7

assert read3($81B9C8) == $11E1AD && read2($81B9CB) == $18C9
org $81B9C8
    jsl VariantPick2
    nop
assert read3($81B9D2) == $AA0A0A
org $81B9D2
    tyx
    nop #2

org $E0F300
VariantPick2:
    php
    rep #$30
    phx
    lda.l $7E11E1 : and.w #$003F : asl : tax
    lda.l !VT,x                     ; offset of this id's list
    beq .own
    tax
    sep #$20
    lda.l !VT,x                     ; number of alternates
    beq .own
    inc                             ; n = own + alternates (<= 256 -> 0 means 256; lists stay < 255)
    pha
    phx
    jsl !RandomByte
    plx
    clc
    adc.l $7E0B50                   ; play-time frames
    adc.l $7E0B4F                   ; play-time seconds
    sta.l $004202                   ; WRMPYA = v
    pla
    sta.l $004203                   ; WRMPYB = n -> v * n
    nop #4
    lda.l $004217                   ; r = v * n / 256 = 0 .. n-1
    beq .own                        ; 0 = the id's own picture
    rep #$20
    and.w #$00FF
    dec : asl                       ; 2 x (r - 1)
    pha
    txa : clc : adc 1,s : tax
    pla
    lda.l !VT+1,x                   ; alternate record number
    bra .rec
.own:
    rep #$20
    lda.l $7E11E1 : and.w #$00FF    ; record = id
.rec:
    asl : asl
    tay                             ; Y = 4 x record
    plx
    lda.l $7E11E1 : and.w #$00FF    ; A = id, B = 0
    plp
    cmp.b #$18                      ; flags as the original code
    rtl
assert pc() <= $E0F400
