"""What each month of the year changes in the scene. The place is the San Francisco Bay Area; the sun's times are
the Bay Area's (37.77 north, 122.42 west).

scene_build.py reads the tables here and calls tint for every computed colour of every month. The dog's, the props'
and the text's colours are not computed: they are the same in every month.

The year there, as the scene shows it:
- The trees are evergreen (cypress, pine, coast live oak): they keep their leaves and their green in every month.
- The grass is the season's sign. The first rains come in November and the grass turns green; it is deep green from
  January to April, dries through May, and is gold from June to October.
- Rain falls from November to March, hardly ever from June to September. In summer low cloud comes in off the sea
  in the morning and clears before noon (weather.gloom).
- The sun is low in winter (29 degrees at noon in December) and high in summer (76 in June): the days are 9 h 34 min
  to 14 h 46 min long, and the dog's shadow by day is longer in winter.

Sun times: minutes after midnight in standard time (UTC-8) on the 15th of each month, from the NOAA sunrise equation
for 37.77 north, 122.42 west, the sun's upper edge on the horizon with refraction (zenith 90.833 degrees). scene.py
changes them evenly from one 15th to the next and adds an hour while summer time is on.
Twilight: by the same equation the sun is 6 degrees under the horizon (the end of civil twilight) 26 to 31 minutes
after sunset there. Night begins TWILIGHT minutes after sunset and ends as long before sunrise: dusk used to
end 40 minutes after sunset, but it is completely dark well before that (33 minutes after a sunset at 17:03 in
November).
"""

SUNRISE = [441, 418, 380, 334, 299, 287, 299, 324, 349, 375, 408, 435]
SUNSET = [1033, 1067, 1095, 1122, 1149, 1170, 1169, 1142, 1097, 1052, 1019, 1012]
TWILIGHT = 27                # minutes from sunset to night, and from night to sunrise
SUMMER_TIME = 'us'           # second Sunday of March to first Sunday of November (scene.us_summer_time)

# The day's weather: the first of clear, cloudy, rain whose number is above the day's roll of 0..99. So January has 42
# clear days in 100, 24 cloudy and 34 with rain (a rain day rains during one shower and is cloudy for the rest).
WEATHER_ODDS = [[42, 66, 100], [44, 68, 100], [48, 72, 100], [62, 82, 100], [72, 90, 100], [84, 96, 100],
                [88, 99, 100], [88, 98, 100], [86, 95, 100], [78, 89, 100], [56, 75, 100], [44, 67, 100]]
# Morning cloud on a clear day: in how many of 100 clear days of the month, and when it clears (a minute of the day
# from `until` to `until + until_range - 1`, picked by the date).
GLOOM = dict(odds=[5, 5, 8, 15, 30, 50, 55, 50, 30, 12, 5, 5], question=6, until=600, until_question=7, until_range=150)

# The dog's shadow by day, [ax, bx, ay, by] as scene.json dog.shadow: it reaches h * ax // bx to the side and
# h * ay // by down for a pixel h rows above the ground. Longer while the sun is low.
SHADOW_DAY = [[1, 4, 1, 7], [1, 4, 1, 7], [1, 6, 1, 10], [1, 6, 1, 10], [1, 8, 1, 12], [1, 8, 1, 12],
              [1, 8, 1, 12], [1, 8, 1, 12], [1, 6, 1, 10], [1, 6, 1, 10], [1, 4, 1, 7], [1, 4, 1, 7]]

FADE_DAYS = 10               # a month's palette is mixed with the next month's over its last ten days

# Clouds in clear weather: how many of the ten drift by. The winter's clear days come between storms; the summer's
# and the early autumn's are bare blue (the summer's cloud is the fog on the horizon and the morning's low cloud).
CLOUDS_CLEAR = [4, 4, 3, 3, 2, 1, 1, 1, 1, 2, 3, 4]

# ---------------------------------------------------------------------------------------------- the twelve designs
# The base design (month 0, art/palettes/<state>.json) is the scene with green grass and no flowers. Each month
# changes the day colours below; the lighting state's grading comes after (scene_build.lit).

# The grass: its three tones (dark, middle, light) in each month. Green with the rains, gold in the dry months.
GRASS = [
    (0x4A7426, 0x5E8F2E, 0x7CAA3C),      # January: deep green
    (0x487A24, 0x5A9629, 0x7AB23A),      # February: the greenest
    (0x4A7C22, 0x5E9A26, 0x80B636),      # March
    (0x5A7C24, 0x749B2A, 0x94B43A),      # April: green, a little yellow in it
    (0x7C8231, 0x9C9E38, 0xB9B648),      # May: turning
    (0xB3973F, 0xD1B24C, 0xE6CB63),      # June: pale gold
    (0xBA9540, 0xD6B04D, 0xEAC864),      # July: gold
    (0xBC9240, 0xD7AC4C, 0xEAC563),      # August
    (0xB48A3D, 0xCEA449, 0xE2BD5E),      # September
    (0xA98239, 0xC39A46, 0xD8B45A),      # October: tawny gold
    (0x7F7C30, 0x989538, 0xB2AC48),      # November: the first green comes through the gold
    (0x5C7A2B, 0x75952F, 0x92AE3E),      # December: green again
]
GRASS_BASE = (0x65732B, 0x778E2F, 0x8FA03C)      # scene_land's GRASS_0..2, which the table above replaces

# Flowers and pumpkins: specks on the grass (scene_land places them). Each has a colour and, for each month, how far
# it stands out from the grass, 0 (it is the grass's middle tone: not to be seen) .. 100.
BLOOM = {
    'FLOWER_YELLOW': (0xF2D24A, [20, 80, 100, 60, 0, 0, 0, 0, 0, 0, 0, 0]),       # mustard and sourgrass
    'FLOWER_ORANGE': (0xF08A2C, [0, 0, 70, 100, 80, 15, 0, 0, 0, 0, 0, 0]),       # California poppies
    'FLOWER_VIOLET': (0x8E6FD0, [0, 0, 20, 90, 100, 40, 0, 0, 0, 0, 0, 0]),       # lupine
    'PUMPKIN':       (0xE8792A, [0, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0, 0]),          # by the blue house, in October
}

# Hue (degrees, + toward green and blue), saturation and brightness (percent) of a kind of thing in each month.
SHIFT = {
    # the trees keep their leaves: deep green in the wet months, fresh in spring, a little dusty by autumn
    'leaf': [(4, 100, 97), (4, 102, 98), (2, 106, 103), (0, 108, 105), (-2, 105, 104), (-3, 100, 102),
             (-4, 95, 100), (-5, 92, 98), (-5, 90, 97), (-4, 90, 96), (0, 95, 96), (3, 100, 96)],
    # the sky: crisp and deep in winter, hazy and pale in the foggy summer, deep and clear in autumn
    'sky': [(3, 104, 93), (3, 104, 92), (0, 102, 98), (0, 100, 100), (0, 96, 101), (-2, 86, 103),
            (-2, 82, 103), (-2, 84, 103), (0, 100, 100), (2, 106, 98), (3, 100, 93), (3, 104, 94)],
    # the sea: greener and darker under winter storms, greyer in the summer fog, its bluest in autumn. The month
    # proposals' winter seas are far darker (January at 37 to 49
    # percent of brightness against 64 to 76 here). Half the way there (January 78 percent, November 86) the shallows
    # lost their turquoise in the day frame, and the picture shows five months of winter: so about a quarter.
    'sea': [(-9, 96, 87), (-9, 96, 90), (-6, 98, 95), (0, 100, 100), (-1, 98, 100), (-3, 92, 101),
            (-4, 90, 101), (-3, 92, 101), (2, 104, 100), (3, 106, 99), (0, 96, 93), (-2, 95, 90)],
    # the sand: damp and a little darker in the wet months, bright in summer
    'sand': [(0, 94, 96), (0, 94, 96), (0, 97, 98), (0, 100, 100), (0, 100, 101), (0, 100, 102),
             (0, 100, 102), (0, 100, 102), (0, 102, 101), (0, 102, 100), (0, 96, 97), (0, 94, 96)],
    'rock': [(0, 96, 93), (0, 96, 93), (0, 98, 96), (0, 100, 100), (0, 100, 101), (0, 100, 103),
             (0, 100, 103), (0, 100, 103), (0, 102, 102), (0, 102, 100), (0, 98, 95), (0, 96, 93)],
}
# The light: each channel of every computed colour in percent. Cool and clear in winter, golden in autumn.
LIGHT = [(98, 99, 102), (98, 99, 102), (100, 100, 100), (100, 100, 100), (101, 100, 99), (101, 100, 99),
         (101, 100, 98), (102, 100, 97), (104, 100, 95), (104, 100, 94), (102, 100, 97), (99, 99, 101)]


def mix(a, b, percent):
    """a to b by percent, per channel, rounded."""
    return sum((((a >> s) & 255) * (100 - percent) + ((b >> s) & 255) * percent + 50) // 100 << s for s in (16, 8, 0))


def shift(colour, hue, sat, val):
    """The colour with its hue turned by hue degrees and its saturation and brightness scaled (percent)."""
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(((colour >> 16) & 255) / 255, ((colour >> 8) & 255) / 255, (colour & 255) / 255)
    r, g, b = colorsys.hsv_to_rgb((h + hue / 360) % 1, min(1.0, s * sat / 100), min(1.0, v * val / 100))
    return (int(r * 255 + 0.5) << 16) | (int(g * 255 + 0.5) << 8) | int(b * 255 + 0.5)


def tint(colour, month, what, state):
    """A day colour of the base design as month 1..12 shows it. what: 'grass' (colour is one of GRASS_BASE), a key of
    BLOOM, a key of SHIFT, or anything else ('land': only the month's light changes it)."""
    if what == 'grass':
        colour = GRASS[month - 1][GRASS_BASE.index(colour)]
    elif what in BLOOM:
        flower, strength = BLOOM[what]
        colour = mix(GRASS[month - 1][1], flower, strength[month - 1])
    elif what in SHIFT:
        colour = shift(colour, *SHIFT[what][month - 1])
    r, g, b = LIGHT[month - 1]
    return (min(255, ((colour >> 16) & 255) * r // 100) << 16) | (min(255, ((colour >> 8) & 255) * g // 100) << 8) \
        | min(255, (colour & 255) * b // 100)


def base(colour, what):
    """The base design (month 0): the colour itself; a flower or a pumpkin is the grass's middle tone (not seen)."""
    return GRASS_BASE[1] if what in BLOOM else colour
