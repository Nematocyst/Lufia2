asar 1.90
; Lufia II (US) — MSU-1 music (proof of concept, 2026-11-12)
;
; Each game song id 0-62 can be replaced by an MSU-1 track "<rom>-<n>.pcm" (44.1 kHz 16-bit
; stereo, "MSU1" header + loop point). Missing tracks fall back to the original music.
; While an MSU track plays, the original song still runs on the sound chip at music volume 0
; (driver command $0B, as in music-off), so sound effects, the sound driver's song-position reads
; used by cutscenes (script op $4D) and every other music command keep working.
;
; Hooks (bank $80 entry points; 4-5 bytes each):
;   PlaySong            $80:93FE  start the song's MSU track (or fall back)
;   PrepareSongResource $80:969F  same, used to bring a song back after a jingle (inn, item get)
;   FadeOutMusic        $80:9692  fade the MSU track too (one volume step per frame)
;   NMI INIDISP write   $80:8664  per-frame MSU fade
;   script op $72 and $83:83CE    stop music -> stop the MSU track too
;   music.asm ApplyMusic $83:FFBA (only if present): MUSIC OFF / STEREO also mutes/unmutes MSU
; Track numbers = song ids, as in Conn's patch (Zeldix t1833), so the existing PCM packs
; (luf2_msu1-<n>.pcm) work: rename the ROM to luf2_msu1.sfc.
; Code + tables at $D0:8000 (empty bank of the 4 MB ROM; backgrounds build 3: $DB:FC00). RAM $7F:FF80-FF83.
lorom

!MsuStatus  = $002000
!MsuTrack   = $002004
!MsuVolume  = $002006
!MsuControl = $002007

!Playing    = $7FFF80               ; 1 = an MSU track is playing
!Volume     = $7FFF81               ; current MSU volume
!Fading     = $7FFF82               ; 1 = fading out
!SpcMuted   = $7FFF83               ; 1 = original music muted by us
!Setting    = $7E0B54               ; MUSIC setting (0 stereo, 1 mono, 2 off with music.asm)

!SetMusicVolume     = $809601
!SoundDriverWrite0D = $809623
!SoundDriverRequest03 = $809528

; ---------------------------------------------------------------- hooks
assert read4($8093FE) == $085ADA48 && read1($809402) == $8B
org $8093FE
    jml MsuPlaySong
    nop
assert read4($80969F) == $085ADA48 && read1($8096A3) == $8B
org $80969F
    jml MsuPrepareSong
    nop
assert read4($809692) == $A920E208 && read1($809696) == $06
org $809692
    jml MsuFadeOut
    nop
assert read3($808664) == $0583AD && read3($808667) == $21008D
org $808664
    jsl MsuNmi
    nop #2
assert read1($80B8B1) == $22 && read3($80B8B2) == !SoundDriverRequest03
org $80B8B1 : jsl MsuStop          ; script op $72 (stop music)
assert read1($8383CE) == $22 && read3($8383CF) == !SoundDriverRequest03
org $8383CE : jsl MsuStop

if read4($83FFBA) == $AD20E208     ; music.asm's ApplyMusic (PHP / SEP #$20 / LDA $0B54)
org $83FFBA
    jml MsuApplyMusic
endif

; ---------------------------------------------------------------- code
!MSUBASE ?= $D08000                 ; -D MSUBASE=$DBFC00 for backgrounds build 3 ($D0 is used there)
org !MSUBASE

MsuPlaySong:                        ; replaces PHA PHX PHY PHP PHB
    pha : phx : phy : php : phb
    sep #$20 : rep #$10
    jsr MsuStart                    ; A = song id (kept)
    jml $809407                     ; JSR LoadSong ... (original)

MsuPrepareSong:
    pha : phx : phy : php : phb
    sep #$20
    jsr MsuStart
    jml $8096A6                     ; JSR LoadSong ... (original)

MsuFadeOut:                         ; replaces PHP / SEP #$20 / LDA #$06
    php : sep #$20
    lda.l !Playing : beq +
    lda.b #$01 : sta.l !Fading
+   lda.b #$06
    jml $809697

MsuStop:                            ; JSL from script op $72 / $83:83CE
    php : sep #$20
    lda.l !Playing : beq +
    lda.b #$00 : sta.l !MsuControl : sta.l !Playing : sta.l !Fading
+   plp
    jml !SoundDriverRequest03       ; original stop (returns to the caller)

MsuNmi:                             ; replaces LDA $0583 / STA $2100 (A8 in the NMI)
    lda.l $7E0583 : sta.l $002100
    lda.l !Fading : beq .out
    lda.l !Volume : sec : sbc.b #$04 : bcs +
    lda.b #$00
+   sta.l !Volume : sta.l !MsuVolume
    bne .out
    sta.l !Fading : sta.l !Playing : sta.l !MsuControl   ; faded out: stop
.out:
    rtl

; C clear = MSU-1 present (A8)
MsuPresent:
    lda.l $002002 : cmp.b #'S' : bne .no
    lda.l $002003 : cmp.b #'-' : bne .no
    lda.l $002004 : cmp.b #'M' : bne .no
    lda.l $002005 : cmp.b #'S' : bne .no
    lda.l $002006 : cmp.b #'U' : bne .no
    lda.l $002007 : cmp.b #'1' : bne .no
    clc : rts
.no:
    sec : rts

; A8 = song id; X/Y/A preserved. Starts the MSU track or falls back to the original music.
MsuStart:
    php : rep #$10
    pha : phx
    rep #$20 : and.w #$00FF : tax : sep #$20
    jsr MsuPresent : bcs .fallback
    cpx.w #64 : bcs .fallback
    lda.l TrackTable,x : cmp.b #$FF : beq .fallback
    sta.l !MsuTrack : lda.b #$00 : sta.l !MsuTrack+1
-   lda.l !MsuStatus : bit.b #$40 : bne -            ; wait while the track is being opened
    bit.b #$08 : bne .fallback                        ; track missing -> original music
    lda.b #$00 : sta.l !Fading
    lda.l !Setting : cmp.b #$02 : lda.b #$FF : bcc +  ; MUSIC OFF: play silently
    lda.b #$00
+   sta.l !Volume : sta.l !MsuVolume
    lda.l LoopTable,x : sta.l !MsuControl             ; 3 = play + repeat, 1 = play once
    lda.b #$01 : sta.l !Playing
    lda.l !SpcMuted : bne +
    lda.b #$01 : sta.l !SpcMuted
    lda.b #$00 : jsl !SetMusicVolume                  ; original music silent
+   plx : pla : plp : rts
.fallback:
    lda.l !Playing : beq +
    lda.b #$00 : sta.l !MsuControl : sta.l !Playing : sta.l !Fading
+   lda.l !SpcMuted : beq +
    lda.b #$00 : sta.l !SpcMuted
    lda.l !Setting : cmp.b #$02 : bcs +               ; MUSIC OFF keeps the original muted
    lda.b #$FF : jsl !SetMusicVolume
+   plx : pla : plp : rts

; music.asm's ApplyMusic, MSU-aware (only assembled in when music.asm is present)
MsuApplyMusic:
    php : sep #$20
    lda.l !Setting
    cmp.b #$02 : bcc .on
    lda.b #$00 : jsl !SoundDriverWrite0D
    lda.b #$00 : jsl !SetMusicVolume
    lda.l !Playing : beq .out
    lda.b #$00 : sta.l !Volume : sta.l !MsuVolume
    bra .out
.on:
    jsl !SoundDriverWrite0D
    lda.l !Playing : beq .spc
    lda.b #$FF : sta.l !Volume : sta.l !MsuVolume
    lda.b #$00 : jsl !SetMusicVolume                  ; keep the original muted
    bra .out
.spc:
    lda.b #$FF : jsl !SetMusicVolume
.out:
    plp
    rtl

; song id -> MSU track number ($FF = always the original music). Default: track = song id.
TrackTable:
    !i = 0
    while !i < 64
        db !i
        !i #= !i+1
    endwhile
    org TrackTable+$0C : db $FF     ; DAMY (empty) slots
    org TrackTable+$0E : db $FF
    org TrackTable+$30 : db $FF, $FF
    org TrackTable+$3F
    db $FF
    org TrackTable+64

; 3 = loop, 1 = play once. Copied from Conn's patch (luf2_msu.asm, $81:FF00) so the existing
; track packs (made for it) behave the same: once = 04 inn, 06 opening 2, 0C/0E dummies, 0F wedding,
; 25 slots start, 26 "gaaan", 2D ending, 30/31 dummies, 33-36 item get, 3C, 3E.
LoopTable:
    db $03,$03,$03,$03,$01,$03,$01,$03,$03,$03,$03,$03,$01,$03,$01,$01
    db $03,$03,$03,$03,$03,$03,$03,$03,$03,$03,$03,$03,$03,$03,$03,$03
    db $03,$03,$03,$03,$03,$01,$01,$03,$03,$03,$03,$03,$03,$01,$03,$03
    db $01,$01,$03,$01,$01,$01,$01,$03,$03,$03,$03,$03,$01,$03,$01,$03
assert pc() <= (!MSUBASE&$FF0000)+$10000
