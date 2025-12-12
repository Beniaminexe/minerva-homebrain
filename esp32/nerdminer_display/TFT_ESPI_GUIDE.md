# TFT_eSPI Quick Guide for NerdMiner/ESP32

## Where to configure
`TFT_eSPI` uses `User_Setup.h` inside the library folder (`Arduino/libraries/TFT_eSPI/User_Setup.h`) or a custom `User_Setup_Select.h` pointing to your setup file. Edit this to match your display.

## Pick the right driver
- Common drivers: `ILI9341`, `ST7789`, `ST7735`, `ILI9488`.
- In `User_Setup.h`, uncomment the one that matches your TFT:
  - `#define ILI9341_DRIVER`
  - `#define ST7789_DRIVER`
  - etc.
- If unsure, search your TFT module markings or vendor page.

## SPI pin mappings (typical ESP32)
- SCK: `GPIO18`
- MOSI: `GPIO23`
- MISO: `GPIO19` (often unused by write-only TFTs)
- CS  : choose a free GPIO (e.g., `GPIO5`)
- DC  : choose a free GPIO (e.g., `GPIO2`)
- RST : choose a free GPIO (e.g., `GPIO4`) or tie to ESP32 reset
- BL  : backlight; tie to 3.3V or control via a GPIO (configure as OUTPUT HIGH)

Set these in `User_Setup.h`:
```
#define TFT_MISO 19
#define TFT_MOSI 23
#define TFT_SCLK 18
#define TFT_CS   5
#define TFT_DC   2
#define TFT_RST  4
```
Adjust pins to your wiring.

## Backlight notes
- Some modules need BL tied high; others expose a pin you must drive HIGH.
- If the screen stays dark but wiring is correct, check BL/LED pin.

## Test the display
1) Select your board (ESP32) in Arduino IDE.
2) Open `File -> Examples -> TFT_eSPI -> 320 x 240 -> TFT_graphicstest`.
3) Build and upload. If you see graphics, driver/pins are correct.

## If you don't know your driver
- Try `ILI9341` first (common on 2.8" SPI modules).
- If colors are inverted or nothing shows, try `ST7789` or `ST7735` with the correct resolution.
- Check the vendor page or silkscreen for hints; sometimes the chip is labeled on the PCB.
