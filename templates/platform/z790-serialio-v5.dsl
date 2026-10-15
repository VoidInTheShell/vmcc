DefinitionBlock ("", "SSDT", 2, "ALASKA", "MS7E07  ", 1) {
 External (\_SB.PCI0, DeviceObj)
 Scope (\_SB.PCI0) {
Device (SRAM) { Name (_ADR, 0x00140002) Method (_STA, 0) { Return (0x0F) } }
Device (I2C0) { Name (_ADR, 0x00150000) Method (_STA, 0) { Return (0x0F) } }
Device (MEI0) { Name (_ADR, 0x00160000) Method (_STA, 0) { Return (0x0F) } }
Device (UAR0) { Name (_ADR, 0x001E0000) Method (_STA, 0) { Return (0x0F) } }
Device (SPI0) { Name (_ADR, 0x001E0002) Method (_STA, 0) { Return (0x0F) } }
}}
