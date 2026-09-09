// Remove every track, via and zone the router laid, and keep the
// hand-routed nets (csi_tracks.py): the MIPI lanes, the D-PHY reference,
// both crystals. For a re-route after a placement change around the P4.
stack({
  boardThicknessMm: 1.6,
  fallbackCopperThicknessOz: 1,
  layers: [
    { kind: "copper", name: "TOP", thicknessOz: 1 },
    { kind: "dielectric", name: "PP7628", thicknessMm: 0.2104, relativePermittivity: 4.4, material: "FR-4 7628" },
    { kind: "copper", name: "INNER_1", thicknessOz: 0.5 },
    { kind: "dielectric", name: "core", thicknessMm: 1.065, relativePermittivity: 4.6, material: "FR-4 core" },
    { kind: "copper", name: "INNER_2", thicknessOz: 0.5 },
    { kind: "dielectric", name: "PP7628b", thicknessMm: 0.2104, relativePermittivity: 4.4, material: "FR-4 7628" },
    { kind: "copper", name: "BOTTOM", thicknessOz: 1 },
  ],
});
clearRouting({ nets: ["1V8_PSRAM", "2V5_MIPI", "3V3", "3V3_CAM", "3V3_HP", "3V3_RF", "3V3_SD", "ADC_FLASH_I", "ADC_LIGHT", "ADC_VCELL", "ANT_MOD", "BB_L1", "BB_L2", "BOOT", "BUCK_EN", "BUCK_HP_SW", "BUCK_SW", "BUCK_VSET", "C6_EN", "C6_IO8", "C6_IO9", "C6_U0RXD", "C6_U0TXD", "C6_WAKEUP", "CAM_IO0", "CAM_IO1", "CHG_CE_N", "CHG_ISET", "CHG_STAT1", "CHG_STAT2", "CHG_TS", "CHG_VSET", "EN", "EN_3V3_CAM", "EN_3V3_HP", "EN_3V3_RF", "EN_3V3_SD", "EN_DCDC", "FB_DCDC", "FLASH_CK", "FLASH_COMP", "FLASH_CS", "FLASH_CTRL", "FLASH_D", "FLASH_FB", "FLASH_HOLD", "FLASH_Q", "FLASH_SW", "FLASH_WP", "GND", "HALOW_ANT", "HALOW_BUSY", "HALOW_CS", "HALOW_IRQ", "HALOW_RST", "HALOW_WAKE", "I2C_SCL", "I2C_SDA", "ICR_A", "ICR_B", "ICR_OUT1", "ICR_OUT2", "LED_1", "LED_2", "LED_3", "LED_4", "LED_5", "LED_6", "LED_7", "LED_8", "LED_9", "LED_A", "LED_STATUS", "MM_GPIO1", "MM_GPIO2", "MM_GPIO3", "MM_GPIO4", "MM_GPIO5", "MM_GPIO6", "MM_GPIO7", "MM_GPIO8", "MM_GPIO9", "MM_MISO", "MM_MOSI", "MM_SCK", "MM_TCK", "MM_TDI", "MM_TMS", "MM_TRST", "MTCK", "PIR_SI", "PIR_WAKE", "PYRO_VDD", "RXD0", "SD1_CLK", "SD1_CMD", "SD1_D0", "SD1_D1", "SD1_D2", "SD1_D3", "SD2_CLK", "SD2_CMD", "SD2_D0", "SD2_D1", "SD2_D2", "SD2_D3", "SD_DET", "SETUP_SW", "SPI_MISO", "SPI_MOSI", "SPI_SCK", "STRAP_JTAG", "TXD0", "USB_CC1", "USB_CC2", "USB_DN", "USB_DN_C", "USB_DN_J", "USB_DP", "USB_DP_C", "USB_DP_J", "VCELL", "VCELL_J", "VCELL_SENSE_EN", "VDDO_4", "VDD_FEM", "VDD_FLASH", "VDD_HP", "VDIV_G", "VDIV_TOP", "VIN_CHG", "VLED", "VSOLAR", "VSYS", "VUSB"], items: ["tracks", "vias", "zones"] });
runCopper();
