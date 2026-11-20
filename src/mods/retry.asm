asar 1.90
; Lufia II (US) — RETRY from the start (optional patch)
; The title's file menu offers START, plus RETRY once the game has been cleared, plus GIFT
; once a RETRY game has been cleared. The count comes from SRAM $70:0000 bits 2-3, read by
; TitleLoadSaveSelectionBits ($82:E998). This patch treats "never cleared" as "cleared once",
; so RETRY is always offered. GIFT is unchanged. Nothing is written to SRAM.
;
; Free space: $86:FFF0-FFFA (filler at the end of bank $86). The Iris patch ends at $86:FF78
; and the Restored & Extended mod doesn't use bank $86's tail, so all three combine.
lorom

assert read4($82E998) == $700000AF       ; LDA $700000
org $82E998
    jsl RetryHeader                     ; replaces LDA $700000 (4 bytes)

org $86FFF0
RetryHeader:
    lda.l $700000
    bit.b #$0C : bne +                  ; already cleared at least once: as is
    ora.b #$04                          ; else behave as "cleared once" (RETRY)
+   rtl
assert pc() <= $86FFFB
