asar 1.90
; Lufia II: Rise of the Sinistrals (US) — "Restored & Extended" mod
; Assemble with asar onto a clean, headerless US ROM
; (SHA1 A89931C1F29B161B8BE717DFAB4A4ADB54B42B84):
;   asar l2mod.asm lufia2.sfc
;
; 1. Map-name decoder: $0A back-references resolve within the current 4KB page
;    (fixes "'3y" Gratze names, Narvick, Capsule Monsters' Cave).
; 2. Gratze overworld region 17 gets a real encounter list.
; 3. Ancient Cave: rare encounters with Kraken, King Hidora and the unused Gades.
; 4. Monster-move IP skills on four new jewels + restored drops (Uni jewel, Repeat attack).
; 5. Capsule monster fixes.
; 6. Cave Gades: story sprite, only after the Gordovan win, speech before the battle.
;
; Free space used: $81:FD10-$81:FFFE (unused $AA filler, now full), $84:FD50-$84:FDFF
; (unused $AA filler; $84:FE00+ is the Iris patch's), $80:FFA0-FFA3, $97:B0A1-$97:B125
; (zero padding after the action text), $97:C493-$97:C53C (old region table, see section 2).

lorom

; ---------------------------------------------------------------- constants
!RandomScale     = $808299      ; A = n (8-bit) -> random 0..n-1
!IpNamePointer   = $81F46B      ; original IP effect-record lookup (bank $95)

!FORM_KHIDORA    = $C0          ; virtual formation ids (>= $C0)
!FORM_GADES      = $C1
!FORM_KRAKEN     = 165          ; original, unused "Kraken" formation

!SPR_HIDORA      = 191          ; field sprites (from $94:DDF6)
!SPR_GADES       = $7A          ; Gades' story sprite (cutscenes)

!WON_FLAG        = $DD          ; unused event flags: Gades beaten at Gordovan West Tower,
!TALK_FLAG       = $DE          ; and "this cave Gades has spoken"
!WON_BYTE        = $7E077E+(!WON_FLAG>>3)
!WON_BIT         = 1<<(!WON_FLAG&7)
!TALK_BYTE       = $077E+(!TALK_FLAG>>3)
!TALK_BIT        = 1<<(!TALK_FLAG&7)

; ================================================================ 1. map names
org $80C9EB                     ; PHX / REP / LDA $54 / AND #$0FFF / TAX / SEP
    phx
    jsl NameBackref
    nop #6

; The arrival banner (TextUpdateSceneLabel) printed the raw ROM name through the text
; engine, which resolves back-references the old way. Point it at the copy the routine
; has just decoded into $7E:E300 instead, so the banner uses the fixed decoder above.
org $80C89D                     ; CLC / ADC #$8000  (A = name pointer, 16-bit)
    lda.w #$E300
    nop
org $80C8AD                     ; LDA #$87 -> bank of the decoded copy
    lda.b #$7E

; ================================================================ 2. region 17
org $869D22 : lda.l RegionTable+1,x
org $869D3E : lda.l RegionTable+1,x
org $869D59 : lda.l RegionTable,x

; ================================================================ 3. cave + formations
org $8183A9                     ; formation read in BattleGenerateEncounterRecord
    jsl FormationRead
    nop #25

org $839A42                     ; CavePlaceRandomObject: pool pick
    jsl CavePick
org $839A4A                     ; field sprite for the picked formation
    jsl FormationSprite
org $80AB86                     ; same lookup when a cave floor is (re)loaded
    jsl FormationSprite

; ================================================================ 4. IP skills + drops
org $81AB50                     ; BattleIpAction: effect record -> $0A42/$0A44
    jsl IpEffectPointer
    nop #10

org $81FB1A                     ; BattleRollEnemyItemDrop entry
    jmp DropHook
    nop #2

; ---------------------------------------------------------------- new code, bank $81
org $81FD10
NameBackref:                    ; in: X = offset after the 3-byte code, $54 = code word
    rep #$20
    txa
    sec : sbc #$0003            ; offset of the $0A byte
    pha
    and #$F000
    pha                         ; [page][pos]
    lda $54
    and #$0FFF
    ora 1,s                     ; same 4KB page
    cmp 3,s
    bcc .ok
    beq .ok
    sec : sbc #$1000            ; reference lies in the previous page
.ok:
    tax
    pla : pla
    sep #$20
    rtl

FormationRead:                  ; in: A = formation id, M8/X8, DB = $97
    rep #$30
    and #$00FF
    cmp #$00C0
    bcs .virtual
    asl : asl : asl
    tay
    lda $BE93,y : sta $22
    lda $BE95,y : sta $24
    lda $BE97,y : sta $26
    lda $BE99,y : sta $28
    rtl
.virtual:
    sec : sbc #$00C0
    asl : asl : asl
    tax
    lda.l VirtualFormations,x   : sta $22
    lda.l VirtualFormations+2,x : sta $24
    lda.l VirtualFormations+4,x : sta $26
    lda.l VirtualFormations+6,x : sta $28
    txy
    rtl

FormationSprite:                ; in: X = formation id, M8; out: A = field sprite
    txa
    cmp.b #!FORM_KHIDORA : bne +
    lda.b #!SPR_HIDORA : rtl
+   cmp.b #!FORM_GADES : bne +
    lda.b #!SPR_GADES : rtl
+   lda.l $94DDF6,x
    rtl

CavePick:                       ; in: X = pool index, M8/X8, DB = $7F
    lda.l $94D95C,x             ; original pick
    pha
    phx
    ldx.b #$00
.loop:
    lda.l CaveBosses,x
    beq .done
    lda.l $7FE696               ; floor being generated
    cmp.l CaveBosses,x   : bcc .next
    cmp.l CaveBosses+1,x : beq + : bcs .next
+   lda.l CaveBosses+3,x
    cmp.b #!FORM_GADES : bne +
    lda.l !WON_BYTE : and.b #!WON_BIT
    beq .next                   ; Gades only appears once you have beaten him at Gordovan
+   lda.l CaveBosses+2,x
    jsl !RandomScale
    cmp.b #$00                  ; RandomScale's flags come from PLX/PLY, not A
    bne .next
    lda.l CaveBosses+3,x
    sta 2,s                     ; replace the formation on the stack
    cmp.b #!FORM_GADES : bne .done
    lda.l !TALK_BYTE : and.b #!TALK_BIT^$FF : sta.l !TALK_BYTE   ; a new Gades speaks again
    bra .done
.next:
    inx #4
    bra .loop
.done:
    plx
    pla
    rtl

IpEffectPointer:                ; in: A (16-bit) = effect record id
    cmp #$00F0
    bcs .new
    jsl !IpNamePointer
    sta $0A42
    sep #$20
    lda.b #$95
    sta $0A44
    rtl
.new:
    sec : sbc #$00F0
    asl
    tax
    lda.l NewIpEffects,x
    sta $0A42
    sep #$20
    lda.b #NewIpEffects>>16
    sta $0A44
    rtl

DropHook:                       ; replaces REP #$20 / STZ $09FE
    rep #$20
    stz $09FE
    lda $09FA
    and #$00FF
    sta $09FC                   ; enemy id (scratch; the original loop reuses it)
    ldx #$0000
.loop:
    lda.l ExtraDrops,x
    cmp #$FFFF
    beq .done
    cmp $09FC
    beq .found
    inx #4
    bra .loop
.found:
    lda.l ExtraDrops+2,x        ; item | listed% << 9, as in the enemy record
    pha
    sep #$20
    xba
    lsr
    sta $09FB
    lda.b #100
    jsl !RandomScale
    cmp $09FB
    bcs .fail
    lda.b #4
    jsl !RandomScale
    cmp.b #1
    bne .fail
    rep #$20
    pla
    and #$01FF
    ora #$0200
    sta $09FE
    bra .done
.fail:
    rep #$20
    pla
.done:
    rep #$20
    jmp $FB1F                   ; continue with the enemy's own drop tags

; ---------------------------------------------------------------- data, bank $81
VirtualFormations:              ; $FF,$01 = fixed list, enemies follow
    db $FF,$01,$99,$FF,$FF,$FF,$FF,$FF   ; $C0 King Hidora
    db $FF,$01,$DE,$FF,$FF,$FF,$FF,$FF   ; $C1 Gades (10,000 HP)

CaveBosses:                     ; first floor, last floor, 1-in-N per monster, formation
    db 55, 66, 24, !FORM_KHIDORA
    db 60, 75, 24, !FORM_KRAKEN
    db 85, 98, 32, !FORM_GADES
    db 0

ExtraDrops:                     ; enemy id, drop word (item | listed% << 9; real = listed/4)
    dw $0059, $0170|(20<<9)     ; Unicorn      -> Uni jewel (Dash), 5%
    dw $0083, $01C6|(12<<9)     ; Deadly Sword -> Sword jewel (Repeat attack), 3%
    dw $0075, $01C7|(12<<9)     ; Dark Spirit  -> Spirit jewel (Black thunder), 3%
    dw $0079, $01C7|(20<<9)     ; Leech        -> Spirit jewel, 5%
    dw $009C, $01C8|(4<<9)      ; White Dragon -> White eye (Cold stream), 1%
    dw $0095, $01C9|(12<<9)     ; Gold Gorem   -> Golden rock (Golden mist), 3%
    dw $FFFF

RegionTable:                    ; copy of $97:C493 (17 regions) + a real region 17
    incbin "region_0_16.bin"
    db 147,100, 163,100, 138,80, 156,60, 157,40   ; Gratze: Moray Vine, Warm Eye, Basilisk, Sphinx, Gold Gorem

; ---------------------------------------------------------------- section 6 code (cave Gades)
CaveContact:                    ; from $83:B96F (FieldProbeActorContact); X16 = touched actor slot
    lda.w $05B6 : lsr : bcs .cave   ; (low RAM is mirrored in every bank this runs with)
    jml $83B976                 ; not a cave floor: look for a contact script (original path)
.cave:
    lda.w $05FA,x : sec : sbc.b #$50
    sta.l $7FF8A4               ; cave object index (the battle path stores the same)
    phx
    rep #$20 : and.w #$00FF : tax : sep #$20
    lda.l $7FF966,x             ; its formation
    plx
    cmp.b #!FORM_GADES : bne .battle
    lda.w !TALK_BYTE : bit.b #!TALK_BIT : bne .battle
    ora.b #!TALK_BIT : sta.w !TALK_BYTE
    ; start the speech the way FieldTryActorInteraction starts a talk script; the next
    ; contact check (one frame after it ends) starts the battle as usual
    lda.w $06E2,x : cmp.w $06E2 : beq +   ; Gades turns to face the leader (as in a talk)
    lda.b #$04 : bcs ++
    lda.b #$00 : bra ++
+   lda.w $06BA,x : cmp.w $06BA
    lda.b #$02 : bcs ++
    lda.b #$06
++  sta.w $066A,x : sta.w $0692,x
    lda.w $05FA,x : sta.w $09AB : sta.w $09AC
    lda.w $0622,x : ora.b #$01 : sta.w $0622,x
    lda.w $0622   : ora.b #$01 : sta.w $0622
    lda.b #$80 : sta.w $099B    ; text_state: script running (FieldPrepareEventControl)
    stz.w $1259 : stz.w $1255 : stz.w $1256
    lda.b #$00 : sta.l $7FD0FF
    dec : sta.l $7FD0C1
    lda.b #$8E : sta.w $1254    ; on "end", return to an "end" byte in the cave's own
    lda.b #GadesSpeech>>16      ; script bank ($8E), so the bank is restored
    sta.w $09B9
    rep #$20
    lda.w #$A1E2 : sta.w $1252
    lda.w #GadesSpeech : sta.w $09B7
    sep #$20
    jml $83B987                 ; SEC : RTS (contact handled)
.battle:
    jml $83B989

assert pc() <= $820000

; ---------------------------------------------------------------- bank $84: IP records + effects
; IP record: effect id (word), animation, type, target mode, IP cost, name, 0
org $84FD50
IpBlackThunder:
    dw $00F0 : db $89, $02, $00, 164 : db "Black thunder", 0
IpColdStream:
    dw $00F1 : db $1B, $02, $00, 164 : db "Cold stream", 0
IpGoldenMist:
    dw $00F2 : db $87, $02, $00, 164 : db "Golden mist", 0

NewIpEffects:
    dw EffBlackThunder, EffColdStream, EffGoldenMist

; Effect record = $FF + battle script (see docs: 32 select, 15 read stat, 0D add,
; 22 magic attack, 21 special attack). Variable L0 = $80 / value $8080.
EffBlackThunder:                ; all enemies, thunder magic, INT + 200 (+INT again in 22)
    db $FF, $32,$01, $32,$05, $15,$80,$08, $0D,$80 : dw 200 : db $22 : dw $0800, $8080 : db $00, $00
EffColdStream:                  ; all enemies, ice special, STR + 450
    db $FF, $32,$01, $32,$05, $15,$80,$06, $0D,$80 : dw 450 : db $21 : dw $0400, $8080 : db $00, $00
EffGoldenMist:                  ; all enemies, light special, STR + 540
    db $FF, $32,$01, $32,$05, $15,$80,$06, $0D,$80 : dw 540 : db $21 : dw $0010, $8080 : db $00, $00

; section 6: script op $11 (stays below $84:FE00, which the Iris patch uses)
ScriptOp11:                     ; new script op 11 xx: open a window at actor xx.
    lda.w $0000,y : iny         ; xx = $FF: the cave monster being met; otherwise a character
    cmp.b #$FF : beq .monster   ; id, or another party member if that one isn't on screen
    phy
.try:
    pha
    jsl $80BF92                 ; FieldSelectActorById: CLC = found
    bcs .no
    ldx.b $A7
    lda.w $0622,x : bit.b #$04  ; hidden?
    beq .yes
.no:
    pla
    inc : cmp.b #$07 : bcc .try
    lda.b #$00                  ; fall back to the leader
    bra .got
.yes:
    pla
.got:
    ply
    bra .open
.monster:
    lda.l $7FF8A4 : clc : adc.b #$50
.open:
    jml $80BC33                 ; window_ex's tail: $09AB, window position, open

assert pc() <= $84FE00
assert pc() <= $850000

org $848F10+2*(5-1)   : dw IpBlackThunder   ; IP  5 was "Test"
org $848F10+2*(167-1) : dw IpColdStream     ; IP 167 was "Double slash" (duplicate of Scissor slash)
org $848F10+2*(13-1)  : dw IpGoldenMist     ; IP 13 was "Dragon fury" (never on any item)

; ---------------------------------------------------------------- bank $97: IP descriptions
org $97B0A1                     ; $97:B0A0 is the last original string's terminator
DescBlackThunder:
    db "Strike all enemies", $0A, "with black thunder.", 0
DescColdStream:
    db "A freezing stream", $0A, "hits all enemies.", 0
DescGoldenMist:
    db "Golden mist burns", $0A, "all enemies with", $0A, "holy light.", 0
assert pc() <= $97B126

!DESC = $978000+2*($0230)
org !DESC+2*5   : dw DescBlackThunder-$978000
org !DESC+2*167 : dw DescColdStream-$978000
org !DESC+2*13  : dw DescGoldenMist-$978000

; ---------------------------------------------------------------- bank $96/$9E: new jewels
; Key26-Key29 records ($96:CF69+$2A10, 65 bytes) become four jewels; Key30 shares PURIFIA's
; dummy key record. Record: 9 fixed bytes, 32-bit word mask, words in bit order.
!ITEMS = $96CF69
org !ITEMS+$2A10
ItemSwordJewel:                 ; $1C6: Repeat attack (IP 1)
    db $02,$00,$00,$EC,$0D : dw 5000 : db $20,$7F : dd $00008000 : dw 1
ItemSpiritJewel:                ; $1C7: Black thunder (IP 5), INT +20
    db $02,$60,$00,$EC,$0D : dw 20000 : db $20,$7F : dd $00008100 : dw 20, 5
ItemWhiteEye:                   ; $1C8: Cold stream (IP 167), AGL +20
    db $02,$60,$00,$EC,$0D : dw 60000 : db $20,$7F : dd $00008080 : dw 20, 167
ItemGoldenRock:                 ; $1C9: Golden mist (IP 13)
    db $02,$60,$00,$EC,$0D : dw 40000 : db $20,$7F : dd $00008000 : dw 13
assert pc() <= !ITEMS+$2A51             ; Crown's record starts here

org !ITEMS+2*$1C6
    dw ItemSwordJewel-!ITEMS, ItemSpiritJewel-!ITEMS, ItemWhiteEye-!ITEMS, ItemGoldenRock-!ITEMS
    dw $2A6B                    ; Key30 -> PURIFIA's dummy key record

org $9EC7E8+12*$1C6
    db "Sword jewel "
    db "Spirit jewel"
    db "White eye   "
    db "Golden rock "

; ================================================================ 5. capsule monsters
; Winged Horse (Gusto form 3, record $97:E2D7): the menu listed Finale + Electro bolt as innate
; and Air attack as learnable, but its battle AI uses Air attack from the start and Electro bolt
; only once learned (slot 3). Make the record match the AI.
org $97E2D7+$0F : db 26         ; innate: Air attack   (was 30 Electro bolt)
org $97E2D7+$14 : db 30         ; learnable slot 3: Electro bolt (was 26 Air attack)

; Darbi: its GUT is about a third of the other capsules', so its courage check (flee once
; % HP lost >= GUT*25/K) fired after a few points of damage. Lower K in its four turn scripts
; ("set L2, K" word) so it is about twice as brave, still the most skittish capsule.
org $97E73B+2 : dw 9            ; Myconido   (was 17)
org $97E7BE+2 : dw 20           ; Wolfman    (was 35)
org $97E845+2 : dw 30           ; Mini Imp   (was 50)
org $97E8D9+2 : dw 36           ; Big Imp    (was 60)

; Wind and earth: Gusto's wind ($0001) and Sully's earth ($0008) attacks had no enemy weak to
; them. Shared reaction routines 27-32 are unused anywhere in the ROM (78 bytes at $96:FD4A);
; two new routines go there (battle VM bytecode, jumps relative to the routine start).
!SHARED = $96FADD               ; shared routine table (offsets from $FADD)
org $96FD4A
WeakFlyerWind:                  ; replaces routine 4 for all its users (flying enemies)
    db $0C,$80,$27,$80          ; set L0, G39 (attack attribute)
    db $06,$80,$80,$00,$1B,$00  ; if L0 == anti-flyer  -> double
    db $06,$80,$00,$10,$20,$00  ; if L0 == ground      -> no damage
    db $16,$80,$01,$00          ; and L0, wind
    db $07,$80,$00,$00,$1B,$00  ; if L0 != 0           -> double
    db $43                      ; return
    db $0F,$2A,$02,$00,$43      ; +$1B: G42 (damage) x 2, return
    db $0C,$2A,$00,$00,$43      ; +$20: G42 = 0, return
assert pc() == WeakFlyerWind+$25
ResistThunderWeakEarth:         ; routine 27: thunder-resistant regular monsters
    db $0C,$80,$27,$80          ; set L0, G39
    db $16,$80,$00,$08          ; and L0, thunder
    db $07,$80,$00,$00,$1D,$00  ; if L0 != 0 -> half
    db $0C,$80,$27,$80          ; set L0, G39
    db $16,$80,$08,$00          ; and L0, earth
    db $07,$80,$00,$00,$22,$00  ; if L0 != 0 -> double
    db $43
    db $10,$2A,$02,$00,$43      ; +$1D: G42 / 2, return
    db $0F,$2A,$02,$00,$43      ; +$22: G42 x 2, return
assert pc() <= $96FD98
org !SHARED+2*4  : dw WeakFlyerWind-!SHARED
org !SHARED+2*27 : dw ResistThunderWeakEarth-!SHARED

; regular monsters that resist thunder now also take double earth damage (bosses keep routine 7)
macro earth(adr)
    assert read2(<adr>) == 7
    org <adr> : dw 27
endmacro
%earth($968BCE)                 ; Wind Genie
%earth($969039)                 ; Salamander
%earth($969FB2)                 ; Bolt Fish
%earth($96A845)                 ; Specter
%earth($96B605)                 ; High Hidora
%earth($96BA16)                 ; Silver Dragon
%earth($96C061)                 ; Tengu

; ================================================================ 6. cave Gades
; The 10,000 HP Gades (formation $C1) now uses his story sprite, only appears once he has been
; beaten at Gordovan West Tower, and speaks before the fight. Touching him runs a short scene
; script (bank $97, plain ASCII); the battle starts on the next contact check, after it ends.
assert read2($89EC05) == $0A37
org $89EC05 : db $1A, !WON_FLAG ; Gordovan win branch: wait_frames 10 -> set_flag $DD

assert read1($83B96F) == $AD && read2($83B970) == $05B6
org $83B96F                     ; FieldProbeActorContact: LDA $05B6 / BIT #$01 / BNE
    jml CaveContact
    nop #3

assert read1($8EA1E2) == $00    ; map $F0's "end" byte used as the speech's return address
org $80CA14+2*$11 : dw Op11Stub ; script op $11 was an invalid opcode (BRK)
org $80FFA0
Op11Stub:
    jml ScriptOp11
assert pc() <= $80FFB0

; The old region table ($97:C493, 170 bytes) moved to bank $81 (section 2) and is free.
org $97C493
GadesSpeech:
    db $11,$00, "Gades!", $01
    db $11,$FF, "Surprised to see me,", $03, "worm?", $01
    db $11,$01, "How are you here?!", $01
    db $11,$FF, "The others might have", $03, "followed HIS orders but", $03
    db "I have to pay you back", $03, "for before!", $01
    db $00
assert pc() <= $97C53D
