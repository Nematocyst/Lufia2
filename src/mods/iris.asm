asar 1.90
; Lufia II: Rise of the Sinistrals (US) — "Iris Treasures" patch
; Assemble onto a clean, headerless US ROM (SHA1 A89931C1F29B161B8BE717DFAB4A4ADB54B42B84)
; or onto a ROM already patched with "Restored & Extended" v0.2 (no overlapping bytes).
;
;  1. The eight wearable Iris Treasures become equipment for Selan and Tia only
;     (sword/staff, shield, helmet/tiara, armor, ring, jewel). The Iris pot stays a key item.
;  2. Each piece grows with the wearer's level (bonus = rate x level / 16 on top of the base stats).
;  3. Full set (6 Iris pieces worn + Iris pot in the bag): +20 STR/AGL/INT/GUT/MGR,
;     +10% max HP and MP, and HP regeneration in battle every round = level/2 (max 50).
;  4. Ancient Cave: Iris items are carried in and out like blue-chest items, worn or not.
;  5. New Game+ (RETRY): the Iris items of the last used save come along.
;  6. Gruberik: the collector displays the treasures without taking them, and he and the
;     treasure hunter get new dialogue about them.
;
; Free space used: $80:FC20-$80:FF9F, $86:FC10-$86:FFFF, $84:FE00-$84:FFFF, $85:FEC0-$85:FFFF ($AA filler);
; $96:F841-$96:F92A (records of 18 identical key items, which now share Door key's record).

lorom

; ---------------------------------------------------------------- game routines
!ReadGameFile          = $80914B
!SaveTestFileHighFlags = $80905F
!TestEventFlag         = $80BE1A        ; A = flag -> X = byte, $57 = bit
!TitleStateDispatch    = $82E746        ; $30 = 4: add item $09CF/$09D0, qty $09CD
!SavePackState         = $85C954
!CopyMessageName       = $8594E7
!DisplayMessage        = $8595FE
!ClearMessage          = $859671
!FrameInput            = $85EC81
!EffectRecord          = $85D9C9
!Popups                = $81C35F
!PlayEffect            = $81895E
!TargetRecord          = $81B2B5
!TargetSlot            = $81B2DB

!IRIS     = $019C                       ; Iris sword; k = id - !IRIS (0..8)
!POT      = $01A3
!FEMALE   = $12                         ; equip mask: Selan $02 + Tia $10

!REGEN_MAX = 50                         ; regen cap per round
!MAGIC    = $5A
!WORN_FLAG = $DC                        ; unused event flag
!WORN_BYTE = $7E077E+(!WORN_FLAG>>3)
!WORN_BIT  = 1<<(!WORN_FLAG&7)                         ; NG+ mask stored in the save at $7F:F17C..F17F

; ================================================================ 1. item records
; Shrine key .. Truth key (18 identical 13-byte records) now share Door key's record,
; freeing $96:F841-$96:F92A for the new Iris records.
org $96CF69+2*$01AE
    fillword $F834-$CF69 : fill 2*18

macro ptr(id, label)
    org $96CF69+2*<id> : dw <label>-$CF69
endmacro
%ptr($019C, RecSword)
%ptr($019D, RecShield)
%ptr($019E, RecHelmet)
%ptr($019F, RecArmor)
%ptr($01A0, RecRing)
%ptr($01A1, RecJewel)
%ptr($01A2, RecStaff)
%ptr($01A4, RecTiara)

; b0 $22 = equippable + important (can't be sold or dropped), b2 $82 weapon,
; b3 class (E0 sword, E9 rod, E1 armor, E2 shield, E3 helmet, E5 ring, EC jewel),
; b4 icon (kept), b5-6 price, b7 slot, b8 equip mask; then word mask + words.
org $96F841
RecSword:   db $22,$00,$82,$E0,$01 : dw $0000 : db $01,!FEMALE
            dd $00002014 : dw 19, 60, 1         ; w2 script, w4 ATP 60, w13 sword swing
            db $37,$1F,$10,$00,$00              ; light attribute (like the Dual blade)
RecStaff:   db $22,$00,$82,$E9,$0A : dw $0000 : db $01,!FEMALE
            dd $00002114 : dw 21, 30, 20, 3     ; w2 script, ATP 30, INT 20, w13 rod swing
            db $37,$1F,$40,$00,$00              ; blunt attribute (like every rod/staff)
RecArmor:   db $22,$00,$00,$E1,$02 : dw $0000 : db $02,!FEMALE
            dd $00000020 : dw 30                ; DFP 30
RecShield:  db $22,$00,$00,$E2,$03 : dw $0000 : db $04,!FEMALE
            dd $00000020 : dw 15
RecHelmet:  db $22,$00,$00,$E3,$04 : dw $0000 : db $08,!FEMALE
            dd $00000020 : dw 15
RecTiara:   db $22,$00,$00,$E3,$21 : dw $0000 : db $08,!FEMALE
            dd $00000020 : dw 15
RecRing:    db $22,$00,$00,$E5,$06 : dw $0000 : db $10,!FEMALE
            dd $00000000
RecJewel:   db $22,$00,$00,$EC,$0D : dw $0000 : db $20,!FEMALE
            dd $00000000
assert pc() <= $96F92B, "Iris records overflow"

; ================================================================ 2. stat totals
org $81F4ED                     ; PartyStatTotals: LDX $C1 / REP #$20 ...
    jsl IrisStatTotals
    rts

; ================================================================ 3. battle regen
org $81C621                     ; BattleStatusTick: LDA $02 / BEQ done
    jsl IrisStatusTick          ; never returns here (resumes at $81:C650)

; ================================================================ 4. Ancient Cave
org $848876 : dl BlueTable      ; AncientCaveTestBlueItem (entry)
org $848880 : dw BlueTableEnd-BlueTable
org $848B00 : dl BlueTable      ; AncientCaveCarryBlueItem (exit)
org $848B08 : dw BlueTableEnd-BlueTable
org $848964                     ; exit: Iris-only inventory loop -> flags for worn pieces too
    jsl IrisExitFlags
    jmp $89AC

; Script op $02 (an invalid opcode in the original): "far text" 02 lo hi bank prints a plain
; ASCII string from anywhere in ROM, like a dictionary word, then continues after the op.
org $80CA14+2*$02 : dw ScriptOp02_FarText
org $80C68B                     ; TextMeasure: CMP #$0A / BEQ -> also measure far text
    jmp MeasureHook
    nop

; Gruberik: new dialogue for the treasure hunter and the collector (display only, no
; more taking the items); generated by gruberik_dialogue.py
incsrc "collector.asm"

; ================================================================ 5. New Game+
org $8090D7                     ; SaveGameFile: JSL SavePackState
    jsl IrisSavePack
org $83AD80                     ; new game: LDA $0B51 / BIT #$02
    jsl IrisNewGame
    nop

; ================================================================ bank $80 ($80:FC20-, $AA filler)
!ReadOperand = $C0B7            ; SceneScriptReadOperand (JSR, bank $80)
org $80FC20
ScriptOp02_FarText:             ; A8 X16, Y -> operands, DB = script bank
    jsr !ReadOperand : pha      ; lo
    jsr !ReadOperand : pha      ; hi
    jsr !ReadOperand : pha      ; bank
    sty.w $1252                 ; return point, as for dictionary words (op $00 comes back)
    lda.w $09B9 : sta.w $1254
    pla : sta.w $09B9
    pla : xba : pla             ; A = lo, B = hi
    pha : lda.w $09B9 : pha : plb : pla
    rep #$20 : tay : sty.w $09B7 : sep #$20
    jmp $9D00                   ; text loop

MeasureHook:                    ; A = control byte < $80
    cmp.b #$0A : bne +
    jmp $C6C6
+   cmp.b #$02 : beq .far
    jmp $C68F                   ; original: CMP #$10 ...
.far:
    jsr !ReadOperand : pha
    jsr !ReadOperand : pha
    jsr !ReadOperand : pha      ; stack: 1 bank, 2 hi, 3 lo
    phy : phb                   ; stack: 1 DB, 2-3 Y, 4 bank, 5 hi, 6 lo
    lda 4,s : pha : plb
    lda 5,s : xba : lda 6,s
    rep #$20 : tax : sep #$20
.loop:
    lda.w $0000,x : inx
    cmp.b #$00 : beq .done
    cmp.b #$03 : beq .nl
    cmp.b #$10 : bcs .ch
    cmp.b #$0C : bcc .loop      ; nothing else is used in far text
    inc.b $56                   ; ? ! , . then a new line
.nl:
    inc.b $55
    lda.b $56 : stz.b $56
    cmp.b $54 : bcc .loop
    sta.b $54 : bra .loop
.ch:
    inc.b $56 : bra .loop
.done:
    plb : ply
    pla : pla : pla
    jmp $C660                   ; continue measuring the script

incsrc "collector_far.asm"      ; far-text strings (generated)
assert pc() <= $80FFA0, "bank $80 free space overflow"

; ================================================================ bank $85 ($85:FEC0-, $AA filler)
org $85FEC0
RegenMsg:   db "Iris Treasures glow.", $00
            fill 37-21                   ; CopyMessageName copies 37 bytes

; ---------------------------------------------------------------- battle regen
; Replaces "LDA $02 / BEQ" in BattleStatusTick (DB $81, A8 X16). Shows the poison
; results first (original code), then heals full-set wearers and shows those.
IrisStatusTick:
    lda.b $02 : beq +
    ldx.w #$F2CC : jsr IrisShowTick         ; "Poisoning."
    jsr IrisEndTick
+   stz.b $02
    stz.b $00
    lda.b #$10 : sta.b $01
-   jsr IrisRegenOne
    lsr.b $01 : bcc -
    lda.b $02 : beq +
    ldx.w #RegenMsg : jsr IrisShowTick
    jsr IrisEndTick
+   pla : pla : pla                         ; drop the JSL return address
    jml $81C650                             ; PLB / RTS of BattleStatusTick

IrisShowTick:
    jsl !CopyMessageName
    ldx.w #$0001 : stx.w $1266
    ldx.w #$FFFF : stx.w $1264
    jsl !DisplayMessage
    lda.b #$00 : jsl !Popups
    lda.b #$DC : jsl !PlayEffect            ; number pop-ups
    rts
IrisEndTick:
    jsl !ClearMessage
    jsl !FrameInput
    rts

; one party target ($00 | $01): mirrors the start of BattleApplyTargetStatusTick
IrisRegenOne:
    lda.b $00 : ora.b $01 : sta.b $03
    jsl !EffectRecord
    stx.w $2181 : lda.b #$01 : sta.w $2183
    ldx.w #$001E
-   stz.w $2180 : dex : bne -
    lda.b $03 : jsl !TargetRecord
    cpx.w #$0BAD : bcc .out                 ; none, or not a character record
    cpx.w #$10DF : bcs .out
    lda.w $000F,x : bit.b #$04 : bne .out   ; down
    rep #$20
    jsl IrisHasSetL : bcc .out16
    lda.w $000E,x : and.w #$00FF : lsr
    cmp.w #!REGEN_MAX : bcc + : lda.w #!REGEN_MAX
+   sta.b $54
    lda.w $0025,x : sec : sbc.w $0011,x
    beq .out16 : bcc .out16
    cmp.b $54 : bcs + : sta.b $54
+   lda.b $54 : beq .out16
    clc : adc.w $0011,x : sta.w $0011,x
    sep #$20
    txy : lda.b $03 : jsl !TargetSlot : tyx
    lda.b $03 : jsl !EffectRecord
    lda.b #$80 : sta.l $7F0000,x
    lda.b #$04 : sta.l $7F0002,x
    rep #$20
    lda.b $54 : sta.l $7F0004,x             ; positive = HP gained
    sep #$20
    inc.b $02
    rts
.out16:
    sep #$20
.out:
    rts

assert pc() <= $860000, "bank $85 overflow"

; ================================================================ code (bank $86)
org $86FC10

; Per-level rates (1/16 point per level) for HP MP ATP DFP STR AGL INT GUT MGR.
IrisRates:
    db  0, 0,48, 0, 0, 0, 0, 0, 0       ; 0 sword   ATP +3/level
    db  0, 0, 0,10, 0, 0, 0, 0, 0       ; 1 shield  DFP +0.6
    db  0, 0, 0,10, 0, 0, 0, 0, 0       ; 2 helmet  DFP +0.6
    db 64, 0, 0,16, 0, 0, 0, 0, 0       ; 3 armor   HP +4, DFP +1
    db  0, 0, 0, 0, 0, 8, 0, 0, 8       ; 4 ring    AGL +0.5, MGR +0.5
    db  0, 0, 0, 0, 8, 0, 0, 8, 0       ; 5 jewel   STR +0.5, GUT +0.5
    db  0,32,16, 0, 0, 0,32, 0, 0       ; 6 staff   MP +2, ATP +1, INT +2
    db  0, 0, 0, 0, 0, 0, 0, 0, 0       ; 7 pot     (not wearable)
    db  0, 0, 0,10, 0, 0, 0, 0, 0       ; 8 tiara   DFP +0.6
IrisRow:   dw 0,9,18,27,36,45,54,63,72
IrisBit:   dw $0001,$0002,$0004,$0008,$0010,$0020,$0040,$0080,$0100

!SET_STATS = 20                         ; full-set bonus to STR AGL INT GUT MGR

; ---------------------------------------------------------------- stat totals
; Replaces PartyStatTotals (A8 X16 in, record at $C1, A8 out). Same sums as the
; original, plus the Iris bonuses held in a stack frame:
;   1,s HP  3 MP  5 ATP  7 DFP  9 STR  11 AGL  13 INT  15 GUT  17 MGR
;   19 pieces worn / set flag  21 level  23 record+$66  25 record
IrisStatTotals:
    phy                                     ; the original left Y alone
    ldx.b $C1
    rep #$20
    tsc : sec : sbc.w #26 : tcs
    lda.w #0
    sta 1,s : sta 3,s : sta 5,s : sta 7,s : sta 9,s
    sta 11,s : sta 13,s : sta 15,s : sta 17,s : sta 19,s
    lda.w $000E,x : and.w #$00FF : sta 21,s
    txa : sta 25,s
    clc : adc.w #$0066 : sta 23,s
    ldy.w #0
.slot:
    lda (23,s),y : and.w #$01FF
    sec : sbc.w #!IRIS
    cmp.w #9 : bcs .next
    cmp.w #7 : beq .next
    asl : tax : lda.l IrisRow,x : tax
    lda 19,s : inc : sta 19,s
    macro addrate(n)
        lda.l IrisRates+<n>,x : and.w #$00FF : clc : adc 1+2*<n>,s : sta 1+2*<n>,s
    endmacro
    %addrate(0) : %addrate(1) : %addrate(2) : %addrate(3) : %addrate(4)
    %addrate(5) : %addrate(6) : %addrate(7) : %addrate(8)
.next:
    iny : iny
    cpy.w #12 : bcs +
    jmp .slot
+

    lda 21,s : tay                          ; rates -> points
    macro scale(n)
        lda 1+2*<n>,s : beq ?z : jsr IrisMulLevel : sta 1+2*<n>,s
    ?z:
    endmacro
    %scale(0) : %scale(1) : %scale(2) : %scale(3) : %scale(4)
    %scale(5) : %scale(6) : %scale(7) : %scale(8)

    lda 19,s : cmp.w #6 : bne .noset
    jsr IrisPotInBag : bcc .noset
    macro setb(n)
        lda 1+2*<n>,s : clc : adc.w #!SET_STATS : sta 1+2*<n>,s
    endmacro
    %setb(4) : %setb(5) : %setb(6) : %setb(7) : %setb(8)
    lda.w #1 : bra .flag
.noset:
    lda.w #0
.flag:
    sta 19,s

    lda 25,s : tax
    lda.w $0051,x : clc : adc.w $0074,x : adc 1,s : sta.w $0025,x       ; max HP
    lda.w $0053,x : clc : adc.w $0076,x : adc 3,s : sta.w $0027,x       ; max MP
    lda.w $005D,x : clc : adc.w $0084,x : adc.w $0092,x : adc 17,s : sta.w $0035,x  ; MGR
    lda.w $005B,x : clc : adc.w $0082,x : adc.w $0090,x : adc 15,s      ; GUT (max 199)
    cmp.w #$00C8 : bcc + : lda.w #$00C7
+   sta.w $0033,x
    lda.w $0059,x : clc : adc.w $0080,x : adc.w $008E,x : adc 13,s : sta.w $0031,x  ; INT
    lda.w $0057,x : clc : adc.w $007E,x : adc.w $008C,x : adc 11,s : sta.w $002F,x  ; AGL
    lda.w $0055,x : clc : adc.w $007C,x : adc.w $008A,x : adc 9,s : sta.w $002D,x   ; STR
    clc : adc.w $0086,x : adc 5,s : sta.w $0029,x                       ; ATP
    lda.w $0078,x : beq + : sta.w $0029,x
+   lda.w $002F,x : clc : adc.w $002D,x : lsr
    clc : adc.w $0088,x : adc 7,s : sta.w $002B,x                       ; DFP
    lda.w $007A,x : beq + : sta.w $002B,x
+
    lda 19,s : beq +                                                    ; +10% HP/MP
    lda.w $0025,x : jsr IrisTenth : clc : adc.w $0025,x : sta.w $0025,x
    lda.w $0027,x : jsr IrisTenth : clc : adc.w $0027,x : sta.w $0027,x
+
    lda.w #999                                                          ; caps
    cmp.w $0025,x : bcs + : sta.w $0025,x
+   cmp.w $0027,x : bcs + : sta.w $0027,x
+   lda.w $0025,x : cmp.w $0011,x : bcs + : sta.w $0011,x               ; HP <= max
+   lda.w $0027,x : cmp.w $0013,x : bcs + : sta.w $0013,x
+
    tsc : clc : adc.w #26 : tcs
    jsr IrisUpdateWornFlag
    sep #$20
    ply
    rtl

; event flag !WORN_FLAG = some party member wears the full set (read by the collector)
IrisUpdateWornFlag:
    phx
    ldy.w #0
-   lda.w $0A80,y : beq +                  ; party record offsets (DB maps low RAM here)
    tax : phy : jsr IrisHasSet : ply : bcs .worn
+   iny : iny : cpy.w #8 : bcc -
    sep #$20
    lda.l !WORN_BYTE : and.b #!WORN_BIT^$FF : bra .st
.worn:
    sep #$20
    lda.l !WORN_BYTE : ora.b #!WORN_BIT
.st:
    sta.l !WORN_BYTE
    rep #$20
    plx
    rts

; A16 = rate sum (<= 255), Y = level -> A = rate * level / 16
IrisMulLevel:
    sep #$20
    sta.l $004202
    tya : sta.l $004203
    rep #$20
    nop #4
    lda.l $004216
    lsr #4
    rts

; A16 -> A / 10
IrisTenth:
    sta.l $004204
    sep #$20
    lda.b #10 : sta.l $004206
    rep #$20
    nop #8
    lda.l $004214
    rts

; C = Iris pot in the bag (A16 X16; clobbers A, X)
IrisPotInBag:
    ldx.w #0
-   lda.l $7E0A8D,x : and.w #$01FF : cmp.w #!POT : beq +
    inx : inx : cpx.w #$00C0 : bcc -
    clc : rts
+   sec : rts

; C = full set (record in X; A16 X16; X preserved)
IrisHasSet:
    phx
    ldy.w #6
-   lda.l $7E0066,x : and.w #$01FF
    sec : sbc.w #!IRIS
    cmp.w #9 : bcs .no
    cmp.w #7 : beq .no
    inx : inx : dey : bne -
    jsr IrisPotInBag
    plx : rts
.no:
    plx : clc : rts

IrisHasSetL:
    jsr IrisHasSet
    rtl

assert pc() <= $870000, "bank $86 overflow"

; ---------------------------------------------------------------- Ancient Cave
; (bank $84; $84:FD50-$84:FDC7 belong to Restored & Extended, $FDC8-$FDFF left spare)
org $84FE00
; Blue-chest items (kept on entry, carried out on exit) + the nine Iris items.
BlueTable:
    incbin "blue_table.bin"
    dw $019C,$019D,$019E,$019F,$01A0,$01A1,$01A2,$01A3,$01A4
BlueTableEnd:

; AncientCaveExit, replacing the Iris inventory loop: the blue-item loop now carries
; the Iris items (worn or not); here only the "brought back" flags $C8+k are set.
IrisExitFlags:
    php
    rep #$30
    jsr IrisOwnedMask
    jsr IrisSetFlags
    stz.b $58
    plp
    rtl

; A16 mask -> event flags $C8+k (A16 X16 in, clobbers A X Y)
IrisSetFlags:
    ldy.w #0
-   lsr : bcc +
    pha : phy
    sep #$20
    tya : clc : adc.b #$C8
    jsl !TestEventFlag
    lda.l $00077E,x : ora.b $57 : sta.l $00077E,x
    rep #$30
    ply : pla
+   iny : cpy.w #9 : bcc -
    rts

; A16 = bit k for every Iris item in the bag or worn by any of the 7 characters
IrisOwnedMask:
    lda.w #0 : pha
    ldx.w #0
-   lda.l $7E0A8D,x : jsr .mark
    inx : inx : cpx.w #$00C0 : bcc -
    ldx.w #0
.rec:
    ldy.w #6
-   lda.l $7E0C13,x : jsr .mark
    inx : inx : dey : bne -
    txa : clc : adc.w #$00BE-12 : tax
    cpx.w #$00BE*7 : bcc .rec
    pla
    rts
.mark:                                  ; stack: 1 ret, 3 mask
    and.w #$01FF : sec : sbc.w #!IRIS
    cmp.w #9 : bcs +
    phx : asl : tax : lda.l IrisBit,x : plx
    ora 3,s : sta 3,s
+   rts

; ---------------------------------------------------------------- New Game+
; SaveGameFile: store the owned mask in spare bytes of the item-storage block
; ($7F:F080+$FC.., beyond the last item id), which is part of every save.
IrisSavePack:
    php
    rep #$30
    phx : phy
    jsr IrisOwnedMask
    sep #$20
    sta.l $7FF17D : eor.b #$A5 : sta.l $7FF17F
    xba : sta.l $7FF17E
    lda.b #!MAGIC : sta.l $7FF17C
    rep #$30
    ply : plx
    plp
    jml !SavePackState

; New game (field start, A8): on RETRY, read the last used save file into the save
; buffer (no other state is touched) and give back the Iris items it held.
IrisNewGame:
    php
    rep #$30
    pha : phx : phy
    sep #$20
    lda.l $000B51 : and.b #$83 : cmp.b #$01 : beq +
    jmp .done
+   lda.l $700000 : and.b #$03
    jsl !SaveTestFileHighFlags : bcc +
    jmp .done                                   ; empty slot
+
    lda.l $700000 : and.b #$03
    jsl !ReadGameFile
    rep #$30
    lda.w #0 : pha                              ; mask at 1,s
    sep #$20
    lda.l $7E3CBF : cmp.b #!MAGIC : bne .scan   ; buffer holds $7F:F17F..F080 reversed
    lda.l $7E3CBE : eor.b #$A5 : cmp.l $7E3CBC : bne .scan
    lda.l $7E3CBE : sta 1,s
    lda.l $7E3CBD : sta 2,s
.scan:                                          ; also the bag (saves made before the patch)
    rep #$30
    ldx.w #$3CB7
-   lda.l $7E0000,x : xba                       ; inventory $0A8D+2j: bytes reversed
    and.w #$01FF : sec : sbc.w #!IRIS
    cmp.w #9 : bcs +
    phx : asl : tax : lda.l IrisBit,x : plx
    ora 1,s : sta 1,s
+   dex : dex : cpx.w #$3CB7-2*96 : bne -
    pla
    pha
    jsr IrisSetFlags                            ; the cave won't hand out duplicates
    pla
    ldy.w #0
-   lsr : bcc +
    pha : phy
    sep #$20
    tya : clc : adc.b #$9C : sta.l $7E09CF
    lda.b #$01 : sta.l $7E09D0 : sta.l $7E09CD
    lda.b #$00 : sta.l $7E09CE
    stz.b $31
    lda.b #$04 : sta.b $30
    jsl !TitleStateDispatch
    rep #$30
    ply : pla
+   iny : cpy.w #9 : bcc -
.done:
    rep #$30
    ply : plx : pla
    plp
    lda.w $0B51 : bit.b #$02
    rtl

assert pc() <= $850000, "bank $84 overflow"
