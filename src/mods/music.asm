asar 1.90
; Lufia II (US) — CONFIG: MUSIC  STEREO / MONO / OFF  (optional patch)
; Adds a third MUSIC setting. OFF silences the music but keeps every sound effect.
; The setting is saved with the game like the others ($0B54: 0 stereo, 1 mono, 2 off).
;
; How: the sound driver has a music volume command (driver mode $0B, routine SetMusicVolume
; $80:9601) that the game never uses. Volume 0 silences music only; it stays in force across
; song changes, so it is sent whenever the setting is applied: new game, loading a save, and
; changing the option. Volume $FF is the driver's default (checked by audio comparison).
; LEFT and RIGHT both cycle the option (LEFT on MUSIC was broken in the original: it read
; past the end of a 3-entry jump table).
;
; Free space: $82:FFB7-$82:FFFF and $83:FFBA-$83:FFFF (unused filler; not used by
; Restored & Extended, Iris Treasures, RETRY or the battle backgrounds patch).
lorom

!SetMusicVolume     = $809601
!SoundDriverWrite0D = $809623       ; stereo (0) / mono (1)
!Dispatch           = $8028         ; InlinePointerDispatch (bank $82)
!Redraw             = $BFBB         ; redraw options, back to the input loop (bank $82)
MenuRedraw          = $82BFBB

; ---------------------------------------------------------------- apply on new game / load
assert read1($829AD4) == $22 && read3($829AD5) == !SoundDriverWrite0D
org $829AD4 : jsl ApplyMusic        ; new game (A = $0B54 from the driver: 0/1)
assert read1($82EAEE) == $22 && read3($82EAEF) == !SoundDriverWrite0D
org $82EAEE : jsl ApplyMusic        ; after loading a save (A = $0B54)

; ---------------------------------------------------------------- CONFIG menu
assert read3($82BFAD) == $0B54AD    ; sub_82BFAD: LDA $0B54 / EOR #$01 / STA / JSL / BRA
org $82BFAD                         ; RIGHT on MUSIC
    jsr MusicNext
    bra MenuRedraw                  ; (a label: asar takes a number after bra as the raw offset)
    nop #9

assert read3($82BF4C) == $14B3AD    ; LDA $14B3 / JSR InlinePointerDispatch / 3-entry table
org $82BF4C                         ; LEFT on any option
    jmp LeftHook

assert read2($82A0BB) == $8EA9 && read1($82A0BF) == $A0 && read2($82A0C0) == $C975
org $82A0BB : lda.b #MusicOptions>>16
org $82A0BF : ldy.w #MusicOptions

; ---------------------------------------------------------------- bank $82 (A8 X16, DB low RAM)
org $82FFB7
LeftHook:
    lda.w $14B3                     ; option row
    cmp.b #$03 : beq +
    jmp $BF4F                       ; others: original dispatch (A = row)
+   jsr MusicPrev
    jmp !Redraw

MusicNext:
    lda.w $0B54 : inc
    cmp.b #$03 : bcc +
    lda.b #$00
+   bra MusicSet
MusicPrev:
    lda.w $0B54 : dec
    bpl MusicSet
    lda.b #$02
MusicSet:
    sta.w $0B54
    jsl ApplyMusic
    rts
assert pc() <= $830000, "bank $82 free space overflow"

; ---------------------------------------------------------------- bank $83
org $83FFBA
; Send the MUSIC setting to the sound driver (any width, DB with low RAM mapped).
ApplyMusic:
    php
    sep #$20
    lda.w $0B54
    cmp.b #$02 : bcc .on
    lda.b #$00 : jsl !SoundDriverWrite0D
    lda.b #$00 : bra .vol           ; OFF: music volume 0
.on:
    jsl !SoundDriverWrite0D
    lda.b #$FF                      ; STEREO/MONO: full volume (driver default)
.vol:
    jsl !SetMusicVolume
    plp
    rtl

; same layout as the original string at $8E:C975, plus OFF ($00/$01/$02 = highlight)
MusicOptions:
    db $0E,$00,$00, $0B,$DC,$33, "STEREO"
    db $0E,$01,$00, $0B,$EA,$33, "MONO"
    db $0E,$02,$00, $0B,$F6,$33, "OFF"
    db $00
assert pc() <= $840000, "bank $83 free space overflow"
