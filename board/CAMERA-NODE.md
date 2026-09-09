# Camera node — the board, before its schematic

**Status: circuit specification, drawn from [CAMERA-MESH.md](../CAMERA-MESH.md).
No part here is final until it has been picked from the library with its
datasheet open.** This is what the schematic is drawn *from*: the blocks,
the rails, the pin budget, the roles, and the decisions that are deliberately
left to draw time. It exists so the schematic answers a written question
instead of inventing one page by page, the same order the controller took
(CONTROLLER-V1 → LAYOUT-REQUIREMENTS → copper).

**The processor is the ESP32-P4, and that was the second choice.** The first
draft was an ESP32-S3 with an OV5640 on a parallel bus, which is the
ESP32-CAM class of picture: fine by day, poor by night. The S3 has no MIPI
receiver and no image processor, so the sensor's own tiny ISP is all the
picture gets. The market's night pictures come from a camera SoC with a
real ISP behind a 4–5 MP sensor; the P4 is that on a microcontroller's
sleep budget: MIPI CSI-2, a hardware ISP, JPEG and H.264 encoders, and a
12 µA deep sleep. It costs an external flash, a fine-pitch QFN on a
four-layer board, and a Wi-Fi companion for the base, because the P4 has
no radio. Those are written below, each with its reason.

---

## One board, three roles

The camera, the relay and the base are **one PCB, populated three ways**.
The P4 has no radio of its own, so the base's 2.4 GHz uplink to the
cabin's router is an **ESP32-C6 module on SDIO**, fitted only in the base
role (Espressif's own pairing, driven by their `esp_hosted` component). A
base is therefore a camera board with the sensor and flash left off and
the C6 and a microSD fitted. A relay is the same board with nothing but
the HaLow radio. One layout, one enclosure family, one firmware with a
role byte.

| Role | Populated | Not populated | Power |
|---|---|---|---|
| Camera | everything but the C6 | C6 | 1S cell, optional 2 W solar |
| Relay | MCU, radio, power, microSD | sensor, IR-cut, flash, pyro, C6 | 1S cell + 5 W solar |
| Base | MCU, radio, power, microSD, **C6** | sensor, IR-cut, flash, pyro | 12 V in through the same charger input, cell as hold-up |

---

## Rails

Everything about this board's battery life is decided here, so the rails
come before the blocks.

| Rail | Source | Who | Why it is its own rail |
|---|---|---|---|
| `VCELL` | 1S cell (LiFePO₄ 3.2 V or Li-ion 3.6 V nominal), through the charger's power path (`SYS`) | charger, boosts, ADC divider | The cell is the only thing that is always there |
| `3V3` | Ultra-low-quiescent buck from `SYS` (TPS62840: ~60 nA quiescent, 750 mA); its enable is the slide switch's OFF position | P4 (its own domains, listed below), flash, pyro, the C6 in the base role | This rail is on for years. Its quiescent current *is* the sleep budget. OFF kills it and everything downstream, and leaves the charger alive so a camera in a drawer by a window still charges |
| `VDD_HP` | 1.1 V buck the **P4 controls itself** (`EN_DCDC`, `FB_DCDC` into a TLV62569) | P4 core | The chip turns it off in deep sleep and trims it under load; an external buck is what Espressif's reference does, and the internal core LDO exists only as a fallback |
| `1V8_PSRAM`, `2V5_MIPI`, `VDD_FLASH` | The P4's own output LDOs (`VDDO_PSRAM`, `VDDO_3`, `VDDO_FLASH`), each with its capacitors | in-package PSRAM, MIPI D-PHY, the flash | Rails we decouple rather than make. All three die in deep sleep with the HP domain, which is why the flash needs no switch |
| `3V3_HP` | **Buck-boost** from `SYS` (TPS63021, fixed 3.3 V, 2 A), enabled by a GPIO | the three switched rails below | A cold cell under a one-amp burst sags below a buck's dropout; a buck-boost holds 3.3 V down to a 2.5 V cell. Off in sleep, ~1 µA |
| `3V3_CAM` | Load switch from `3V3_HP` (TPS22917) | camera module, IR-cut driver, ambient-light sensor | The sensor leaks hundreds of µA in "standby". Cutting the rail is the only real off |
| `3V3_RF` | Load switch from `3V3_HP` | HaLow module (up to ~400 mA in transmit) | Same reason. A radio module's sleep current is a datasheet number; a load switch is a measurement |
| `3V3_SD` | Load switch from `3V3_HP` | microSD | An idle card draws 100–200 µA. It is used by both the camera and the radio, so it gets its own switch |
| `VLED` | Boost from `SYS` (TPS61165 class, EN/PWM from the MCU) | 8–12 × 850 nm LEDs in strings, current-sense shunt | Enabled only during exposure, tens of milliseconds per picture. Never idles |
| `VUSB` | USB-C, 5 V | charger input, programming | The lesson of board A: a first image needs a wire the board actually exposes |

**Why two bucks and not one.** The always-on `3V3` buck is chosen for
its quiescent current and gives 750 mA. Awake, the board can ask for more
than that at once: the P4 (~100 mA from 3.3 V), a camera module (150–200
mA), a microSD writing (up to 200 mA) and a HaLow module transmitting
(300–400 mA). A rail that only stays inside its budget because the
firmware promises never to write a card during a transmit is a rail that
browns out the day the promise is broken. So the awake loads hang off
their own converter, and the sleep converter never sees them.

**Sleep target: under 30 µA** total with the cell at nominal: P4 deep
sleep 12 µA by the datasheet, `3V3` buck quiescent, pyro standby, the
buck-boost and three load switches disabled, the core buck disabled by
the chip, the divider switched off. This is a measurement before it is a
claim; the first board carries a jumper in the cell lead for exactly that
meter.

**Charger.** 1S, solar-tolerant input (5–6 V panel or 12 V through a
pre-regulator in the base role), **programmable termination** so one board
serves LiFePO₄ (3.6 V) and Li-ion (4.2 V) by a resistor, **power path** so a
flat cell in sunlight still boots the node, and an **NTC input that stops
charging below 0 °C**. The controller's frost rule, in a chip. Lithium
primary AA cells (the −40 °C option) are a later variant with a different
input, not this board.

---

## Blocks

Grouped by completed function, which is also how the schematic pages split.

### MCU

**ESP32-P4NRW32**: dual-core RISC-V at 400 MHz, **32 MB PSRAM in the
package** (a 5 MP frame and its JPEG both fit, with room for the ISP's
buffers), MIPI CSI-2, hardware ISP, JPEG and H.264. It needs an
**external 16 MB QSPI flash** on its dedicated flash pins, a **40 MHz
crystal**, a **32.768 kHz crystal** on GPIO0/GPIO1 (the wake schedule in
[CAMERA-MESH.md](../CAMERA-MESH.md) assumes ±20 ppm; the internal RC is
±5 %), and its core buck. USB Serial/JTAG on GPIO24/25 through a USB-C
with ESD is the programmer and the console; the high-speed USB pins stay
unused. Boot and reset buttons, one status LED, test points on every rail,
on UART0 and on the four JTAG pins.

The pin map below is copied from Espressif's ESP32-P4-Function-EV-Board
wherever the choice was free, so the dev kit's firmware runs on this board
without a pin table edit. Where it departs, the row says why.

### Camera

**MIPI CSI-2 camera on the Raspberry Pi 15-pin 1.0 mm FPC**, the connector
Espressif's own board uses and the one every Pi camera and its clones fit.
The module carries its own regulators and its own 24 MHz oscillator (the
15-pin standard has no XCLK), so the connector supplies only 3.3 V, I²C,
and two GPIO. Changing the sensor is changing the module, not the board.

**What may go on the end of that flex is decided by Espressif's driver
list, not by the sensor market.** `esp_cam_sensor` carries OV5647, SC2336,
OV5640, OV02C10 and a handful of others; there is no IMX219, IMX477 or
IMX708 driver, so a Pi Camera v2 or v3 will not enumerate whatever its
datasheet promises. That leaves **OV5647** as the only sensor sold on
15-pin boards, and its driver's **1280×960 binning mode** is the one to
use at night: summing the 1.4 µm pixels four at a time is worth more in
the dark than the 5 MP the part number advertises. SC2336 would be the
better sensor (2.7 µm, built for security cameras), but nobody sells it
on a 15-pin board, only on Espressif's 24-pin. The bench comparison the
gates ask for is therefore OV5647 binned against OV5647 unbinned, not one
sensor against another.

**Why not the sensor on the board, the way the mass-market cameras do it.**
Theirs is a bare die on the main board under a lens holder that a jig
focuses on the line, by the thousand. A five-board run has no jig: a lens
holder glued and focused by hand is a soft picture, and it is the picture
a hunter judges. A module arrives with its lens focused at the factory,
its filter glued flat, and its own regulators, and JLC stocks none of the
bare sensors anyway. The connector costs a dollar and a ZIF latch; what
it buys is a sharp first picture and a sensor swap without a board spin.
Sensor-on-board is the cost-down for the day a run is large enough to
own a focus jig. The CSI wiring to the P4 does not change.

**Mechanical IR-cut filter**, and the board drives it two ways because
modules split two ways. A bare actuator gets the H-bridge (two GPIO, one
pulse each way; DRV8837) out to its own two-pin connector. A Pi-style
module (Arducam's and Waveshare's IR-CUT boards) has the driver on it
already and switches on a level held on the connector's **pin 12**, the
line the Pi calls the camera LED; that pin is `CAM_IO1`, wired to the P4,
so those modules need no board change and leave the H-bridge unused.
**Ambient-light sensor** (phototransistor on an ADC pin) decides day/night
for the filter and the flash without waking the sensor.

### Trigger

**Digital pyroelectric sensor** (Excelitas PYD 1598: serial interface,
on-chip threshold, ~3 µA) behind a Fresnel lens in the housing tuned to
the field of view. Its direct-link line lands on a **low-power-domain
GPIO** (GPIO0–15 on the P4) so the MCU sleeps through everything but a
real crossing; its serial-in line takes one more pin. LCSC does not
stock it, but JLCPCB's own catalogue lists it as **C3678555**, a
pre-order part, wave-soldered like any through-hole part, held in the
account's parts library for the assemblies that follow. So it is
assembled like everything else, after one pre-order. The analog
alternative (a D203S element and a BISS0001, both at LCSC) is a
different sleep budget, not a fallback: the element's bias and the
BISS0001 together draw 40–60 µA, twice the whole node's target. If the
digital part ever becomes unobtainable, that is a page revision, not a
resistor swap.

### Flash

One string of ten 850 nm LEDs on a boost driver, a **current-sense
shunt**, which the teardown found, read on an ADC pin so the firmware
knows a black night picture came from a dead string and not from the
sensor, one control line from the MCU that is both enable and PWM,
exposure-synchronous. The first board's string is ten small 3528 parts
at 150 mA (about 2 W), enough to prove the pipeline and not enough to
light a moose at 20 m. The class's answer to that is a **second board in
the lid**: the LED array, and often the pyro and the light sensor with
it, sit on a front board behind the window with a flex to the main board
in the body, because those three parts must face the scene and the main
board must sit against the battery. This node will do the same the day
the housing is drawn: the flash driver stays on the main board, the
string and the pyro move to the front board, and the two connectors
appear on these pages. The nets do not change.

### Radio

**HaLow module — decided: Quectel FGH100M (FGH100MABMD)**, a Morse
Micro MM6108 in a 13 × 13 mm LGA. The range test was going to pick
between the MM6108 and Newracom's NRC7394; the decision came earlier and
on other grounds: LCSC and JLC assemble no Newracom module at all, the
MM6108 is the silicon every serious HaLow product ships, and Morse
Micro's **official ESP-IDF component lists the ESP32-P4 as a tested
host** with AP mode available for the base. Of Quectel's two variants
the plain FGH100M is the one certified for **Canada (IC), FCC and CE**
today at 21 dBm; the `-H` variant reaches 27 dBm through a 5 V front-end
but is preliminary, FCC "planned" only, and on a different footprint, so
it is not a drop-in later. The receiver is the number that matters at
the ranges the mesh uses: −109 dBm at MCS10 in a 1 MHz channel.

The driver wants eight lines, and the schematic gives it eight on the
P4's IO-MUX SPI pins: `SPI_SCK`, `SPI_MOSI`, `SPI_MISO`, `HALOW_CS`,
`HALOW_IRQ` (out-of-band data-ready), `HALOW_BUSY` (rising-edge
interrupt, needed for power save), `HALOW_WAKE` (the module's
`WAKEUP_IN`) and `HALOW_RST` (`RESET_N`, held low by 10 k so the module
sleeps at ~0 µA until the P4 releases it). The pad assignment comes from
Seeed's published schematic of the same module (their XIAO HaLow hat,
FGH100M-H): `SDIO_CLK` is the SPI clock, `SDIO_CMD` MOSI, `SDIO_DATA0`
MISO, `SDIO_DATA3` chip select with 47 k up, `SDIO_DATA1` the interrupt,
`GPIO0` BUSY, 22 Ω in series with clock and data, and 10 k to ground on
`GPIO1`–`GPIO9` and the four JTAG inputs. The module runs from `3V3_RF`
through its switch; `VDD_FEM` reaches that rail through a 0 Ω link,
because the `-H` brief gives that pin its own 3–5.25 V supply and the
plain brief says nothing. Antenna pad through 0 Ω to the U.FL, with two
unpopulated shunt pads for a matching network the bench may never need.

**ESP32-C6-MINI-1, base role only**, on the P4's second SDIO slot with
the six 51 k pull-ups Espressif specifies, its enable and boot pin on P4
GPIOs, and its UART0 crossed to the P4's UART1 so the P4 can put it in
download mode and flash it. No second cable for the second chip.

### Storage

microSD on **4-bit SDMMC** (the P4's slot 1, on its IO-MUX pins). The
camera's own copy of every full frame; the base's ring buffer. Its rail is
switched, its card-detect is read, its six lines carry the 51 k pull-ups
the SD specification asks for and a TVS each, because the card is the one
thing a gloved hand touches in January. **microSD, not full-size SD, by
decision:** the mass-market cameras fit a full-size slot because the hunter
comes to read the card; here the card is the archive the base empties over
the radio, and the smaller socket saves 20 mm of board.

---

## Pin map

The S3 draft did not close its pin budget and closed it with an I²C
expander. The P4 has 55 GPIO and needs none, which also removes a trap:
that expander powers up with every output **high**, so the rail enables
on it would have switched every rail on at each boot. On the P4 every
enable is a chip pin that is high-impedance at reset, held low by its own
pull-down.

| GPIO (pin) | Signal | Why this pin |
|---|---|---|
| GPIO0 (104), GPIO1 (1) | `XTAL_32K_N`, `XTAL_32K_P` | the only 32 kHz crystal pins on the P4 |
| GPIO2 (2) | `MTCK` | the last JTAG pin, on a test point. The other three went to the setup switch, the pyro and the radio; USB Serial/JTAG is the debugger, and it needs none of them |
| GPIO3 (3) | `HALOW_BUSY` | the HaLow module's BUSY line, a rising-edge interrupt the driver needs for power-save mode; without it the radio never sleeps |
| GPIO5 (5) | `PIR_SI` | the pyro's serial-in configuration line. It was `MTDO`, a chip output under JTAG, so an attached debugger would write nonsense into the pyro's registers (while debugging, and only then) |
| GPIO4 (4) | `SETUP_SW` | the slide switch's SETUP position, on a low-power-domain pin so moving the switch wakes the node. It was `MTMS`; a debugger drives that pin push-pull and wins over the 100 k pull-up, so JTAG still works. Only in SETUP position would the reading be nonsense, which nobody debugging cares about |
| GPIO6 (6) | `PIR_WAKE` | low-power domain: wakes the chip from deep sleep |
| GPIO7 (7), GPIO8 (8) | `I2C_SDA`, `I2C_SCL` | the dev kit's I²C; the camera module's SCCB rides it |
| GPIO9 (10) | `C6_WAKEUP` | base only |
| GPIO10 (11), GPIO11 (12) | `C6_U0RXD`, `C6_U0TXD` | UART1 on its IO-MUX pins, crossed to the C6's UART0 for flashing it. Base only |
| GPIO12 (13), GPIO13 (14) | `C6_EN`, `C6_IO9` | the C6's enable and boot strap, driven by the P4. Base only |
| GPIO14–17 (15–18) | `SD2_D0`–`SD2_D3` | SDIO slot 2 to the C6, as the dev kit wires it. Base only |
| GPIO18 (19), GPIO19 (20) | `SD2_CLK`, `SD2_CMD` | |
| GPIO20 (22) | `ADC_LIGHT` | ADC1 channel 4 |
| GPIO21 (23) | `ADC_VCELL` | ADC1 channel 5 |
| GPIO22 (24) | `ADC_FLASH_I` | ADC1 channel 6: the flash shunt |
| GPIO23 (25) | `VCELL_SENSE_EN` | |
| GPIO24 (52), GPIO25 (53) | `USB_DN`, `USB_DP` | USB Serial/JTAG, through 33 Ω as the dev kit does |
| GPIO26 (55) | `LED_STATUS` | |
| GPIO27 (56) | `EN_3V3_HP` | the buck-boost's enable |
| GPIO28–31 (57, 58, 60, 61) | `HALOW_CS`, `SPI_MOSI`, `SPI_SCK`, `SPI_MISO` | SPI2 on its IO-MUX pins: no GPIO-matrix latency on the radio's bus |
| GPIO32 (63), GPIO33 (64) | `HALOW_IRQ`, `HALOW_RST` | |
| GPIO34 (65) | `STRAP_JTAG` | strapping pin the datasheet forbids leaving floating: 10 k to ground, test point, nothing else |
| GPIO35 (66) | `BOOT` | strapping: 10 k up, button to ground |
| GPIO36 (68) | `HALOW_WAKE` | the module's `WAKEUP_IN`; a strapping pin that only selects ROM printing, and only when an eFuse is burnt; 100 k down gives it a level at reset |
| GPIO37 (69), GPIO38 (70) | `TXD0`, `RXD0` | UART0 on test points |
| GPIO39–42 (80–83) | `SD1_D0`–`SD1_D3` | SDMMC slot 1 on its IO-MUX pins, the microSD |
| GPIO43 (84), GPIO44 (86) | `SD1_CLK`, `SD1_CMD` | |
| GPIO45 (87) | `EN_3V3_SD` | |
| GPIO46 (88) | `SD_DET` | |
| GPIO47 (89), GPIO48 (90) | `EN_3V3_CAM`, `EN_3V3_RF` | |
| GPIO49 (92), GPIO50 (93) | `CAM_IO0`, `CAM_IO1` | the Pi connector's two GPIO: enable/reset, and a strobe most modules leave unconnected |
| GPIO51 (94), GPIO52 (95) | `ICR_A`, `ICR_B` | the IR-cut H-bridge |
| GPIO53 (97) | `CHG_STAT1` | the charger's "charging" line; its second status line stays on a pull-up, and `CE#` stays tied low because the charger's own NTC rule is the only gate the cell needs |
| GPIO54 (98) | `FLASH_CTRL` | one pin: the boost driver's enable *is* its PWM input (TPS61165 class) |

Dedicated pins: the flash on 27–33, CSI on 42–48 with its 4.02 k
reference resistor, DSI 34–40 left open, high-speed USB 49–50 left open
with its PHY still powered as the datasheet requires.

Every microcontroller pin is now assigned once. Nothing is shared by
wishful thinking, and nothing is on an expander.

## Schematic pages

| Page | Holds |
|---|---|
| 1 MCU | P4 and its decoupling, core buck, both crystals, flash, USB-C + ESD, boot/reset, strapping, status LED, JTAG/UART test points |
| 2 Power | cell, charger, solar/USB input, `3V3` buck and the OFF/SETUP/ON switch on its enable, `3V3_HP` buck-boost, the three load switches, NTC, cell divider, the sleep-current jumper |
| 3 Camera | 15-pin CSI FPC, IR-cut H-bridge, ambient-light sensor |
| 4 Trigger | pyro, its wake line, footprint reserve for the analog fallback |
| 5 Flash | boost driver, LED strings, shunt |
| 6 Radio | the FGH100M HaLow module with its series resistors, straps and decoupling, the U.FL, the C6 companion and its SDIO |
| 7 Storage | microSD on SDMMC, its pull-ups, its TVS, card detect |

There is no role header: the role byte lives in flash and is set over
the same USB-C that flashes the firmware.

---

## What the hand gets

Three things a person touches in the field, and one they see. All three
sit behind **one gasketed door**, the way the class does it, so the sealed
part of the housing is never opened outdoors:

- **The slide switch, OFF / SETUP / ON.** On the `3V3` buck's enable,
  where it switches microamps, rather than in the cell lead, where a
  contact carrying one-amp bursts ages. OFF: the buck and everything
  below it are dead, ~0.15 µA, and the charger still charges. SETUP:
  pulls `SETUP_SW` low, which wakes the P4 and puts it in pairing and
  set-up mode. ON: nothing pulled, the node runs its schedule.
- **The microSD**, push-push, with its TVS array.
- **The USB-C**, which is the **service port**. The P4's USB Serial/JTAG
  is behind it with no other part: `esptool` puts the chip in download
  mode by itself over that port, so **flashing needs no BOOT button**.
  The button is for the bench. The same port is the console and the
  configuration channel. The base's C6 is flashed *through* the P4 (its
  boot pin, enable and UART0 are on P4 pins, the way Espressif's
  `esp_hosted` expects), and the HaLow module carries no firmware of its
  own: the P4 loads it over SPI at every boot. One cable, every chip.
  Field updates over HaLow come later and change nothing here.

The thing they see is the **antenna**: a U.FL on the board to a 900 MHz
whip on an IP67 RP-SMA bulkhead through the housing. A whip on top of a
plastic box beats a PCB antenna inside it by 3–6 dB and can be pointed;
on the base it goes up a mast. The pigtail is a housing part, kept short.
The base's C6 keeps its module antenna: it talks to a router ten metres
away, indoors.

---

## What the weather gets

The teardown showed a bare board with hand-soldered flying leads
and no coating, in a gasketed box. A sealed box that cycles between −30
and +25 °C breathes through its gasket and condenses inside; that is how
trail cameras die: corrosion at the battery contacts and the microphone
port. Three rules, none expensive:

- **Conformal coating** on every populated board (acrylic, sprayed after
  assembly with the connectors masked; JLC does not offer it, the bench
  does). The controller's board A is uncoated because it lives indoors; a
  board on a tree is not allowed that argument.
- **A pressure-equalising vent membrane** in the housing, so the air
  inside follows the outside without carrying water. A desiccant sachet
  is the consumer answer and lasts one season.
- **No flying leads.** Everything leaves the board on a connector or an
  FFC, the same KF2EDG/JST family as the controller.

## Decided at draw time, with the datasheet open

Named here so nobody mistakes a placeholder for a choice. Decided ones
carry their numbers and the LCSC stock seen on the day, because a part
with 183 units is a prototype part, not a production one.

1. **Charger — decided: BQ25185DLHR** (LCSC C19725033, WSON-10, **183 in
   stock on 2026-09-02; fine for prototypes, re-check before any run**).
   3.6–18 V in, 25 V tolerant, so the panel and a 12 V base feed IN
   directly through a Schottky each. `ILIM/VSET` = **18 kΩ → 4.2 V /
   500 mA input limit** (Li-ion); **3.6 kΩ → 3.6 V** for LiFePO₄. One
   resistor, the only change between chemistries. `ISET` = **1 kΩ → 300 mA**
   (I = 300 AΩ / R). `TS/MR`: a bare **10 kΩ NTC to ground**. The pin's
   38 µA bias puts the cold trip at 1.0 V ≈ 0 °C and hot at 0.115 V ≈
   60 °C by itself (the datasheet's curve is β 3435; the NCP18XH103 is
   3380, close enough for a charge cutoff). Power path regulates SYS at
   4.5 V; both bucks run from SYS. `CE#` pulled down (charging on);
   `STAT1/2` open-drain with 10 k pull-ups. IN and SYS capacitors 25 V
   rated as TI asks: 1 µF 0603 (CL10B105KA8NNNC, C29936, 1.8 M in stock;
   the first pick, CL10A105KB8NNNC, showed **zero stock** and was dropped)
   and 10 µF 0805 (CL21A106KAYNNNE, C15850).
2. **`3V3` buck — decided: TPS62840DLCR** (C2071859, VSON-8, 6 440 in
   stock). 1.8–6.5 V in, 750 mA, 60 nA quiescent. `VSET` = **267 kΩ →
   3.3 V** (E96, Table 1 of the datasheet), `MODE` and `STOP` to ground,
   `EN` to SYS. Inductor the one TI characterises: **DFE201612E-2R2M**
   2.2 µH 0806 (C337893, 13 k in stock); 10 µF in and out.
3. **Load switches — decided: TPS22917DBVR** (C2681320, SOT-23-6, 19 840
   in stock) instead of the TPS22916 first named: that one only comes in
   a 0.7 mm DSBGA, which is a yield problem on a first board. 2 A, `QOD`
   tied to `VOUT` so each rail is actively discharged when off, `CT` left
   open, `ON` held low by 100 k so a rail is off until the firmware says
   otherwise. Three of them: camera, radio, card.
4. **Cell sense:** 100 k/100 k divider on `ADC_VCELL`, its top switched by a
   P-MOSFET (SI2301, C10487) whose gate a 2N7002 (C8545) pulls down from
   `VCELL_SENSE_EN`; 100 k pull-down keeps it off at reset. Off, the
   divider draws nothing.
5. **Processor — decided: ESP32-P4NRW32** (C22387510, QFN-104 10 × 10 mm,
   0.35 mm pitch, **zero stock at LCSC on 2026-09-02, $5.92**; ordered
   through JLC's sourcing before the board, or bought and consigned; the
   first bench unit is an ESP32-P4-Function-EV-Board, not this PCB). The
   board becomes **four layers**: the D-PHY pairs and the 0.35 mm QFN
   need it, and the controller's two-layer rules do not carry.
6. **Core buck — decided: TLV62569DBVR** (C141836, SOT-23-5, 122 k in
   stock), the part on Espressif's own board, wired exactly as they do:
   `EN` from the P4's `EN_DCDC`, `FB` from its `FB_DCDC`, 2.2 µH
   (DFE201612E-2R2M again), 4.7 µF in, 22 µF out (CL21A226MQQNNNE, C5674).
   The chip owns the feedback; there is no divider to get wrong.
7. **`3V3_HP` buck-boost — decided: TPS63021DSJR** (C202140, VSON-14,
   2 297 in stock, $3.29; the one expensive part, and the one that keeps
   a −20 °C cell from browning out the radio). Fixed 3.3 V, 2 A, `EN` from
   `EN_3V3_HP` with 100 k down, `PS/SYNC` low for power-save mode. Inductor
   1.5 µH rated 3 A; picked with its saturation curve, below.
8. **Flash — decided: W25Q128JVSIQ** (C97521, SOIC-8, **Basic part**,
   34 k in stock) on the P4's dedicated flash pins, powered by the chip's
   own `VDDO_FLASH`, `/CS` pulled up 10 k as the reference does.
9. **Camera connector — decided: TE 1-1734248-5** (C2922285, 15-pin
   1.0 mm bottom-contact FPC, 948 in stock), the exact part on the
   Function-EV board so the flex orientation is not a guess. Pinout is the
   Raspberry Pi's: GND / D0− / D0+ / GND / D1− / D1+ / GND / CLK− / CLK+ /
   GND / IO0 / IO1 / SCL / SDA / 3V3. `IO0` pulled up 10 k, I²C pulled up
   2.2 k on the camera side of the 0 Ω links, 4.02 k `CSI_REXT` to ground,
   and **100 Ω in series with each of the six lane wires** because the
   reference board has them and a MIPI lane is the one interface on this
   board nobody can probe on a bench.
10. **Wi-Fi companion, base only — decided: ESP32-C6-MINI-1-N4**
    (C5736265, 559 in stock). SDIO slot 2 with 51 k pull-ups on the six
    lines, `EN` 10 k up with 1 µF, `IO8` 10 k up (its strap), `IO9` and
    UART0 to the P4.
11. **IR-cut driver — decided: DRV8837DSGR** (C39159, WSON-8), on
    `3V3_CAM`, `nSLEEP` tied to that rail; 2-pin JST PH to the filter.
    **Ambient light — decided: ALS-PT19-315C** (C146233, 575 in stock),
    collector on `3V3_CAM`, 100 k emitter load, so it draws nothing in
    sleep and cannot read while the camera rail is off, which is the
    order the firmware wants anyway.
12. **Slide switch — decided: SS13D07VG4** (C2681578, 1P3T through-hole,
    17 k in stock), through-hole on purpose so a gloved thumb cannot
    lift it off the board. Its four terminals sit in a row and the
    slider bridges two neighbours per position, so pin 2 is ground, pin 1
    is the buck enable (OFF), pin 3 is `SETUP_SW` (SETUP) and pin 4 is
    open (ON); `BUCK_EN` has 100 k to `SYS`, `SETUP_SW` 100 k to `3V3`
    and 100 nF for the bounce. **Confirm the bridging order on the
    datasheet before the board**. A single-common variant with the
    common on pin 1 would tie the enable to the setup line.
13. **microSD — decided: TF-01A** (C91145, push-push, 81 k in stock),
    51 k pull-ups on D0–D3 and CMD to `3V3_SD`, `SD_DET` 100 k to `3V3`,
    and a **BSDFN2C031U** TVS (C600818, DFN1006, 9.8 k in stock) on each
    of the six lines, the part on Espressif's board, one per line
    because six singles route next to a socket where a four-channel
    array does not.
14. **Antenna — decided: U.FL-R-SMT-1(80)** (C88374, Hirose, 58 k in
    stock) to an RP-SMA bulkhead with an O-ring; the bulkhead and the
    pigtail are housing parts. The HaLow module is drawn as a **1×10
    2.54 mm header** (PZ254V-11-10P, C492409) carrying `3V3_RF`, ground,
    the SPI, `HALOW_CS`, `HALOW_IRQ`, `HALOW_RST` and `HALOW_EN`. That is the
    footprint a dev module plugs into for the range test, replaced by the
    module's own once it is chosen.
15. **LED driver — decided: TPS61165DBVR** (C58756, SOT-23-6, 24 k in
    stock), with its datasheet open: 3–18 V in, 38 V open-LED
    protection, 200 mV feedback, `CTRL` is enable, PWM and one-wire
    dimming on one pin with an internal 800 k pull-down (off at reset,
    1 µA shut down), `COMP` wants 220 nF, 10 µH in, 1–10 µF out. Fed from
    `SYS`. Shunt **1.33 Ω → 150 mA** (RTT051R33FTP, C158243, 44 k in
    stock), which is what the chip's 1.2 A switch delivers into a 15 V
    string from a 3.3 V cell (Figure 1 of the datasheet), and read on
    `ADC_FLASH_I` through 1 k / 10 nF. Output capacitor 4.7 µF **50 V**
    1206 (12065C475K4Z2A, C779997) because the open-LED clamp is 38 V.
    Inductor CY54-10UH (C2929431, 5.8 × 5.2 mm, 31 k in stock). Confirm
    its saturation current is above 1.2 A on the datasheet. LEDs
    JNJ-L-3528CW-85020D (C22447917, 850 nm, 20°, 2 000 in stock): the
    3535 one-watt parts LCSC lists had 1 to 170 units each, which is not
    a production part; the front board picks its own.
16. **Pyro — decided: Excelitas PYD 1598 / 7655** (JLCPCB C3678555,
    TO-5 4-lead, **zero in stock, pre-order at ~$5.72 in quantity, two
    minimum**, wave-soldered, kept in the account's parts library), drawn
    with its own symbol: Direct Link → `PIR_WAKE`, Serial In → `PIR_SI`,
    supply through 100 Ω / 10 µF from `3V3`. See the Trigger block for
    why the LCSC analog path is not a fallback.
17. **HaLow module — decided: Quectel FGH100MABMD** (C23509203, LGA
    13 × 13 mm, **44 in stock, $13.15**; the `-H` is C53961956, 6 in
    stock, preliminary, different footprint). Rails: `VBAT` 3.0–3.6 V and
    `VDDIO` from `3V3_RF`; `VDD_FEM` tied to the same rail pending the
    hardware design guide (the `-H` brief gives it 3.0–5.25 V, the plain
    brief does not list it). Host lines as in the Radio block. **The
    SPI-mode pad assignment (which SDIO pads are SCK/MOSI/MISO/CS, which
    pad is the SPI IRQ, which GPIO is BUSY) is confirmed against
    Quectel's FGH100M Hardware Design before layout**. It is the one
    document this page was drawn without, and it is behind Quectel's
    registration wall, not LCSC's.
18. The 40 MHz crystal and the buck-boost inductor: picked from stock at
    draw time; the crystal must be −40 °C rated with a load capacitance
    the two 22 pF (or the pair the part's own CL asks for) match.
19. **The P4's pin capacitors are 0402, decided at layout**: 100 nF
    C1525, 1 µF C52923, 10 nF C15195, 22 pF C1555. Samsung and FH,
    all JLC basic parts, millions in stock. A side of the 0.35 mm QFN is
    10 mm and holds six 0603 parts; its left side has eight supply pins
    on six nets, and with 0603 parts two of them had no capacitor within
    7 mm. The 10 µF, 4.7 µF and 22 µF bulk parts stay 0603/0805: a 10 µF
    0402 is a 6.3 V part that keeps half its capacitance at 3.3 V.
    [CAMERA-LAYOUT.md](CAMERA-LAYOUT.md) C-35 holds the distances.

## Measured before the board is believed

Sleep current through the jumper, at room temperature and in a freezer.
Trigger-to-first-frame from deep sleep. Flash exposure energy per picture.
**And now a fourth, first:** a night picture at 15 m with an 850 nm flash,
from the Function-EV board with an OV5647 NoIR, next to the same scene
from an ESP32-S3 with an OV5640. That is the picture that justified this
page's second draft, taken before the PCB exists. All four sit in
[CAMERA-MESH.md](../CAMERA-MESH.md)'s list of conditions; this board is where
the numbers come from.
