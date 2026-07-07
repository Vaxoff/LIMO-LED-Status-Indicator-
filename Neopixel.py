from rpi_ws281x import PixelStrip, Color
 
# -----------------------
# Config - adjust to match your strip and wiring
# -----------------------
LED_COUNT = 8          # number of pixels on your strip
LED_PIN = 37            # BCM GPIO number backing physical pin 37
LED_FREQ_HZ = 800000    # signal frequency (800khz is standard for WS281x)
LED_DMA = 10            # DMA channel
LED_BRIGHTNESS = 100    # 0-255
LED_INVERT = False
LED_CHANNEL = 0         # set to 1 if using GPIO13/PWM1 instead
 
RED = Color(255, 0, 0)
 
 
def set_all(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()
 
 
def main():
    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL,
    )
    strip.begin()
 
    set_all(strip, RED)
    print("NeoPixel strip set to red.")
 
 
if __name__ == "__main__":
    main()
 
