asar 1.90
; Lufia II (US) — battle background extensions: extra tiles + third palette + backdrop gradients.
; Apply AFTER bbg_build.py (needs the 4 MB layout: records at $E0:F100, palettes $E0:9000, third
; palettes $E0:A000, gradient pointers $E0:F600 (colour 0) and $E0:F6C0 (fixed colour), tables in
; bank $F2).
;
; EXTRA TILES: backgrounds may use up to 426 tiles. Tiles beyond the first 256 use tile numbers
; 86-255 (VRAM words $2560-$2FFF; BG1/BG2 tile base $2000). In battle nothing displays or writes
; that range (traced and tested): the only upload near it is BattleQueueTilesAt2000 ($85:9D61,
; action-message text, $2000-$255F). The extra tiles are stored uncompressed (table $E0:B000,
; 5 bytes per graphics index: long pointer, byte count) and copied by DMA channel 6 (the battle's
; general-purpose DMA channel; the NMI reprograms it for every use) in 512-byte pieces, each
; started at the beginning of vertical blank, when the background loads.
;
; SCROLLING BANDS (prototype): a background may have a top band that drifts sideways (clouds over a
; gradient sky). Table $E0:B500, 2 bytes per graphics index: band end line (0 = none), speed
; (frames per pixel = 1 << speed). The battle NMI ($85:8E6C) sets BG1HOFS = $0594 + drift for the
; top of the frame and arms an H+V IRQ at the band's last line; the IRQ handler (vector $00:FFEE ->
; $80:FFA4) puts BG1HOFS back to $0594 for the rest of the screen. Battle never used IRQs (the
; original vector pointed at a bare RTI at $80:86C0). Frame counter: $7F:FFF4 (PROTOTYPE: free-RAM
; check still to do). Shakes keep working: both values follow $0594. Skipped for the desert.
;
; THIRD PALETTE: every background load also copies 32 bytes from $E0:A000 + 32 x (palette index)
; into CGRAM row 4 (buffer $0320 and master $7F:F1DB, so effects that restore from the master keep
; it). Row 4 is unused in battle (traced and tested: nothing reads or writes it; rows 5-7 hold the
; party colours for actors drawn on BG2, refreshed every turn). Original backgrounds have zeros
; there, which is what row 4 held before. Tiles with palette bits 4 use it.
;
; A background whose record effect byte (4th byte) is $10+n gets gradient n:
;   HDMA channel 0 rewrites CGRAM colour 0 (the backdrop) per scanline, so see-through pixels of the
;   background show a smooth vertical gradient (the sky costs no tiles and none of the 30 colours);
;   HDMA channel 6 writes the same gradient to COLDATA (the fixed colour). The subscreen shows the
;   fixed colour where it is see-through, and translucent windows (results, messages) blend with the
;   subscreen: without this the sky inside them would turn black.
; Background $00 (desert) keeps its heat ripple, which also uses channel 0.
;
; Battle HDMA: config buffer $1AEF (5 bytes per channel: DMAP, BBAD, A1TL, A1TH, A1B), $DA = channels
; to (re)enable at the next NMI, $D9 = enabled mask (BattleNmiUploads sub_858ED2). Channel use:
; 0 = ripple (switched off whenever a background loads), 1/3/4/5/7 = window translucency and layers,
; 2 = window colour math during turns / results, 6 = VRAM transfers (GP-DMA in the NMI; the NMI
; re-applies channel 6's HDMA settings every frame, so it can also run HDMA) and the circle-window
; spell effect. COLDATA is never written in battle by the original code.
lorom

!BattleInitializeRipple = $85A701
!GradPtr = $DFF000          ; layout v2: tables in bank $DF (240 skies, 256 palettes)
!FixPtr = $DFF300
!Cfg = $7E1AEF
!Pal3 = $DFD000
!XTab = $E0B000
!BandTab = $E0B500
!BandCount = $7FFFF4

; BattleBackgroundPrepare tail: LDA #$01 / TRB $D9 / TDC / STA $1B17 / LDA $11E1 / BNE / JSL ripple / RTL
assert read4($81BAB9) == $D91401A9
org $81BAB9
    jml GradientTail

; End of the circle-window effect: LDA #$40 / TRB $D9 switches channel 6 off. Restore the fixed-colour
; gradient afterwards.
assert read4($819A9A) == $D91440A9
org $819A9A
    jsl GradientCircleEnd

; BattleBeginPrimaryWave: the per-line BG3 scroll for lines 0-7 points at a blank line (0, -1 ... -7);
; lines 8-11 got $94, which shows the bottom edge of the window frame (map row 19, low priority).
; The opaque sky always covered it; a see-through sky reveals it as dark dashes on lines 9-11.
; Extend the blank range to lines 0-11 (effects that rebuild this table write their own values).
assert read3($85A818) == $0010E0            ; CPX.w #$0010
org $85A818
    cpx.w #$0018

; battle NMI: LDA $0583 / STA $2100 (6 bytes) -> JSL BandNmi / NOP / NOP
assert read2($858E6C) == $83AD && read3($858E6F) == $21008D
org $858E6C
    jsl BandNmi
    nop #2

; The game sets the interrupt-disable flag at reset (SEI $80:8000) and never clears it, so the band
; IRQ could never be taken. NMI exit (PLY/PLX/PLA/PLB/PLP/RTI at $80:86BA) -> NmiExit: same, but
; clears I in the flags RTI restores. Harmless elsewhere: nothing else ever enables an IRQ source.
assert read4($8086BA) == $AB68FA7A
org $8086BA
    jml NmiExit

; native IRQ vector -> trampoline in free filler before the header ($80:FFA4-FFA7)
assert read2($00FFEE) == $86C0
org $00FFEE
    dw $FFA4
assert read4($80FFA4) == $AAAAAAAA
org $80FFA4
    jml BandIrq

org $E0F780
GradientTail:
    php
    sep #$20
    lda.b #$01 : trb.b $D9          ; as the original: channel 0 off
    lda.b #$00 : sta.l $7E1B17
    lda.l $7E11E1                   ; background id
    cmp.b #$18 : beq +              ; black screen: no record was loaded
    jsr LoadRow4
    jsr LoadExtraTiles
+   lda.l $7E11E1
    bne .notdesert
    lda.l $7E11E5                   ; desert slot: a picture with a gradient (effect $10+, e.g. a
    cmp.b #$10 : bcs .notdesert     ; random variant of the desert) uses the gradient instead
    jsl !BattleInitializeRipple     ; desert: heat ripple (original behaviour)
    plp
    rtl
.notdesert:
    lda.b #$41                      ; channels 0 and 6
    jsr GradientSetup
    plp
    rtl

GradientCircleEnd:                  ; A8 here
    lda.b #$40 : trb.b $D9          ; the replaced instructions
    php
    lda.b #$40                      ; channel 6 only
    jsr GradientSetup
    plp
    rtl

; Copy the background's third palette into CGRAM row 4 (buffer and master).
LoadRow4:
    php
    rep #$30
    lda.l $7E11E4                   ; palette index (record byte 2)
    and.w #$00FF
    asl : asl : asl : asl : asl     ; x32
    tax
    ldy.w #$0000
-   lda.l !Pal3,x
    phx
    tyx
    sta.l $7E0320+$80,x             ; row 4 in the CGRAM buffer
    sta.l $7FF1DB+$80,x             ; and in the master copy
    plx
    inx : inx : iny : iny
    cpy.w #$0020
    bne -
    sep #$20
    lda.b #$80 : tsb.b $73          ; upload CGRAM at the next NMI
    plp
    rts

; Copy the background's extra tiles (if any) to VRAM $2560+.
LoadExtraTiles:
    php
    rep #$30
    lda.l $7E11E3                   ; graphics index (record byte 1)
    and.w #$00FF
    pha : asl : asl : clc : adc 1,s : tax : pla     ; 5 x index
    lda.l !XTab+3,x                 ; byte count
    beq .none
    pha                             ; 5,s = bytes left
    lda.l !XTab,x : pha             ; 3,s = source address
    lda.l !XTab+2,x : and.w #$00FF : pha   ; 1,s = source bank
    ldy.w #$2560                    ; VRAM word address
.loop:
    sep #$20
-   lda.w $4212 : bmi -             ; wait for the end of the current vertical blank,
-   lda.w $4212 : bpl -             ; then for the start of the next one
    lda.b #$80 : sta.w $2115        ; VMAIN: increment after the high byte
    sty.w $2116
    lda.b #$01 : sta.w $4360        ; two registers, write once ($2118/$2119)
    lda.b #$18 : sta.w $4361
    lda 1,s : sta.w $4364
    rep #$20
    lda 3,s : sta.w $4362
    lda 5,s
    cmp.w #$0200 : bcc +
    lda.w #$0200
+   sta.w $4365
    tax                             ; X = piece size
    sep #$20
    lda.b #$40 : sta.w $420B        ; DMA channel 6
    rep #$20
    txa : clc : adc 3,s : sta 3,s   ; source += piece
    txa : eor.w #$FFFF : inc : clc : adc 5,s : sta 5,s   ; bytes left -= piece
    txa : lsr
    phy : clc : adc 1,s : tay : pla ; VRAM address += piece / 2
    lda 5,s
    bne .loop
    pla : pla : pla
.none:
    plp
    rts

; ---------------------------------------------------------------- scrolling band
BandNmi:                            ; A8 X16, in the battle NMI
    lda.w $0583 : sta.w $2100       ; the replaced instructions
    php
    rep #$30
    phx
    lda.l $7E11E1 : and.w #$00FF
    beq .off                        ; desert: the ripple owns BG1HOFS
    cmp.w #$0018 : beq .off
    lda.l $7E11E3 : and.w #$00FF : asl : tax
    lda.l !BandTab,x : and.w #$00FF
    beq .off
    sep #$20
    sta.w $4209 : stz.w $420A       ; VTIME = band end line
    lda.b #220 : sta.w $4207 : stz.w $4208   ; HTIME: late in the line -> write lands in hblank
    lda.l !BandTab+1,x : tax        ; speed (shift)
    rep #$20
    lda.l !BandCount : inc : sta.l !BandCount
-   cpx.w #$0000 : beq +
    lsr : dex : bra -
+   clc : adc.l $7E0594             ; drift + game scroll (shakes)
    sep #$20
    sta.w $210D : xba : sta.w $210D
    lda.b #$B1 : sta.w $4200        ; NMI + H/V IRQ + auto joypad
    rep #$30
.off:
    plx
    plp
    rtl

NmiExit:
    ply : plx : pla : plb : plp     ; as the original
    php
    rep #$20 : pha
    sep #$20
    lda 4,s : and.b #$FB : sta 4,s  ; interrupted code's flags (pushed by the NMI): clear I
    rep #$20 : pla
    plp
    rti

BandIrq:                            ; any width; DB unknown
    rep #$20 : pha
    sep #$20
    lda.l $004211                   ; acknowledge
    lda.l $7E0594 : sta.l $00210D
    lda.l $7E0595 : sta.l $00210D
    rep #$20 : pla
    rti

; A = channels to enable (bit 0 colour 0, bit 6 fixed colour), if the current background has a gradient.
GradientSetup:
    php
    sep #$20
    rep #$10
    pha
    lda.l $7E11E1
    cmp.b #$18 : beq .none          ; black screen: no record was loaded
    ; (desert slot: only pictures with a gradient get here; the others keep the ripple on ch0)
    lda.l $7E11E5                   ; record effect byte
    sec : sbc.b #$10
    bcc .none
    cmp.b #$F0 : bcs .none
    rep #$20
    and.w #$00FF
    pha                             ; n
    asl : clc : adc 1,s             ; 3n
    tax
    pla
    sep #$20
    lda 1,s : and.b #$01 : beq +
    rep #$20
    lda.l !GradPtr,x : sta.l !Cfg+2         ; channel 0: A1T
    sep #$20
    lda.l !GradPtr+2,x : sta.l !Cfg+4       ; A1B
    lda.b #$03 : sta.l !Cfg                 ; direct, mode 3 (B, B, B+1, B+1)
    lda.b #$21 : sta.l !Cfg+1               ; $2121 CGADD / $2122 CGDATA
+   lda 1,s : and.b #$40 : beq +
    rep #$20
    lda.l !FixPtr,x : sta.l !Cfg+30+2       ; channel 6: A1T
    sep #$20
    lda.l !FixPtr+2,x : sta.l !Cfg+30+4     ; A1B
    lda.b #$00 : sta.l !Cfg+30              ; direct, mode 0 (one byte)
    lda.b #$32 : sta.l !Cfg+30+1            ; $2132 COLDATA
+   pla
    tsb.b $DA                       ; enable at the next NMI
    plp
    rts
.none:
    pla
    plp
    rts
assert pc() <= $E0FB00
