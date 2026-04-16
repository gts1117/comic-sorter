import injector
import traceback
try:
    injector.convert_cbr_to_cbz_and_inject("/Users/grahamschwartz/Documents/Comics/Comics/Studio 407/Fictionauts/Unknown Storyline/Fictionauts (2025) (digital) (Son of Ultron-Empire).cbr", "Studio 407", "Fictionauts", "Unknown Storyline")
    print("Success!")
except Exception as e:
    traceback.print_exc()
