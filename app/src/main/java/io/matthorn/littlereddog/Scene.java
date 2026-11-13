package io.matthorn.littlereddog;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * The beach, drawn from the files in the art folder: a port of tools/scene.py, which is the reference. Every pixel is
 * a palette index read from a layer; a frame stacks the layers in the order scene.json gives, looks the indexes up in
 * the lighting state's palette, and, across a change of pose, state or weather, blends two finished frames in whole
 * steps. The dog shows one of the poses of scene.json (dog.poses); poseAt picks it from the tick.
 * All arithmetic is integer and follows Python's: floorDiv and floorMod wherever a value can be negative, long for the
 * tick and anything multiplied by it, and the hash on the low 32 bits of its inputs.
 *
 * Everything is read and decoded in the constructor. A frame reuses the same buffers; the only things it may allocate
 * are the date line and the wrapped quote, which are kept per date and hour (same result, made once an hour), a
 * LocalDate at the first minute of a day, to find the minute before, and, with a pose in the doghouse's doorway, the
 * LocalDateTime of each minute inHouse looks at (a few for each frame).
 */
public final class Scene {

    public static final int W = 480, H = 270;
    public static final int CLEAR = 0, CLOUDY = 1, RAIN = 2;
    static final String[] STATES = {"dawn", "day", "dusk", "night", "cloudy", "rain"};
    static final int DAWN = 0, DAY = 1, DUSK = 2, NIGHT = 3, OVERCAST = 4, WET = 5;
    static final String[] WEATHERS = {"clear", "cloudy", "rain"};
    private static final String[] DAYS = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};
    private static final String[] MONTHS = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"};

    /** Opens a file of the art folder by its path relative to it: "scene.json", "layers/sky.png", "palettes/day.json", "dog.png", "quotes.txt". */
    public interface Files {
        java.io.InputStream open(String path) throws java.io.IOException;
    }

    // ------------------------------------------------------------------------------------------- what the files say

    private final String[] order;
    private final Map<String, Integer> roleIndex = new HashMap<>();
    private final Files files;                            // kept: a month's palettes are read when the month first shows
    private final int[][][] monthRgb = new int[12][][];   // [month - 1][state][index]
    private final boolean[][][] monthShown = new boolean[12][][];
    private final int[][] mixRgb = new int[6][256];       // the palette of the date mixKey names, for each state
    private final boolean[][] mixShown = new boolean[6][256];
    private int mixKey = -1;                              // year * 10000 + month * 100 + day
    private final int monthFadeDays;
    private final Map<String, Png> layers = new HashMap<>();
    private final Map<String, Png> fullLayers = new HashMap<>();
    private final boolean[] clearNightOnly;               // by position in order
    private final boolean moonClearNightOnly;             // the moon is one of those layers
    private final Png[] stateSky = new Png[6], stateSea = new Png[6], stateSand = new Png[6];
    private final int[][] stateSun = new int[6][];
    private final int[] sunrise, sunset;                  // standard time on the 15th of each month
    private final boolean summerTime;                     // the US rule adds an hour
    private final int[] dawn = new int[2], dusk = new int[2];
    private final Png sun;
    private final int sunCx, sunCy;
    private final Png moon;
    private final int moonSize, moonCx, moonCy, moonX, moonY;
    private final boolean[] moonStates = new boolean[6];
    private final long moonEpoch, moonMonth;
    private final int[] glintRoles;
    private final int glintStep, glintShown;
    private final int[] pathRoles;
    private final String[] pathDigits;
    private final int pathStep, pathFrames;
    private final int[] twinkleRoles;
    private final int twinkleSlot, twinkleOneIn, twinkleSalt, twinkleDimTo;
    private final Png beam;
    private final int beamX, beamY, beamW, beamTicks, beamFrames;
    private final Png foam, ripples;
    private final int foamTop, foamH, foamFrames, foamTicks, ripplesTop, ripplesH, ripplesFrames, ripplesTicks, ripplesWeather;
    private final int rainWeather, rainTileW, rainTileH, rainLean;
    private final Png rainFar, rainNear;
    private final int rainFarSpeed, rainNearSpeed;
    private final int fadeSteps, fadeTicks, lightMinutes, lightSteps;
    private final int[] light = new int[3];               // stateFade's answer: the state before, the state after, the step
    private final Png clouds;
    private final int[] cloudsShown = new int[3];
    private final int[] cloudsShownClear;                 // in clear weather the month says how many
    private final boolean[] cloudsGrown = new boolean[3];
    private final int cloudSpan, cloudLeft;
    private final int[][] cloudTracks;                    // row, start x, ticks per px, then normal and grown: sx, sy, w, h, dx, dy
    private final Png specials;                           // the sheet of what shows only on some dates
    private final Special[] specialItems;
    private final boolean[] specialToday;                 // by item: its date rule holds on the date specialKey names
    private final int[] slotOfOrder;                      // by position in order: which of SLOTS it is, or -1
    private final Special[] tints;                        // roles in another colour on some days: their gates
    private final int[][] tintRoles, tintRgb;
    private final int meteorSlot, meteorOneIn, meteorLife, meteorFade, meteorTail, meteorSalt;
    private final int[] meteorBox, meteorSpeed, meteorSlope, meteorLevels;
    private final int[][] meteorShowers;                  // month, day, month, day, one in
    private final boolean[] skyRole = new boolean[256];   // the roles a shooting star may be drawn over
    /** The most pixels a shooting star can have: its head and a tail of up to METEOR_PIXELS - 1. */
    static final int METEOR_PIXELS = 21;
    private final int[] meteorPx = new int[3 * METEOR_PIXELS];
    private int lastYear, lastMonth, lastDay, lastState = -1, lastWeather;   // of the last frame drawn
    /** For looking at one surprise without waiting: its name (null: none), and the tick it was asked for. */
    private String demo;
    private long demoTick;
    private int specialKey = -1;                          // year * 10000 + month * 100 + day
    private final int dogX, dogY;
    private final String[] poseNames;
    private final Part[][] poses;                         // each pose's parts, in the order scene.json gives
    private final int poseHold, poseJitter, poseFadeTicks, poseSalt, poseOrderSalt;
    private static final int NO_MOON = 6;                 // after the six states: a night state while no moon is drawn
    private final int[][] shadowLean = new int[7][];
    private final int[][] shadowDay = new int[12][];      // by day the lean is the month's
    private final int[] shadowThick = new int[7];
    /** scene.py's shadow_target as a lookup: DOG_SHADOW for a sand role, the value of shadow_onto for one of its keys, 0 for no change. */
    private final byte[] shadowTarget = new byte[256];
    private final int textRole, edgeRole;
    private final int[] textOpacity = new int[6];         // by state, percent: how solid the clock and the words are
    private final byte[] textUnder = new byte[W * H];     // the frame as it was before the clock and the words were stamped
    private final Png font, digits;
    private final String fontChars;
    private final int cellW, advance, line, marginX, marginY, quoteChars, quoteLines, quoteEpoch;
    private final int[][] digitCells = new int[11][];    // '0'..'9', then ':'
    private final List<String> quotes = new ArrayList<>();
    private final int quoteSalt;
    private final int[] quotePass, quotePassBefore;      // the order of one pass of the quotes, and of the pass before it
    private long quotePassNumber = Long.MIN_VALUE;       // the pass quotePass holds
    /** The hour whose quote shows, for the fast mode: -1 for the clock's hour. */
    private int fixedQuoteHour = -1;
    // scene.json, evening: the brightness of the hour (percent), when the night's begins (minute of the day), the
    // ramps, the hold and the fade after the screensaver starts (minutes), and the warmth
    private final int brightDay, brightEvening, brightNight, nightFrom, nightRamp, holdMinutes, fadeMinutes;
    private final int eveningDawn, eveningWarmAfter, eveningGreen, eveningBlue;
    private final int[][] weatherOdds = new int[12][];
    private final int[] gloomOdds;
    private final int gloomQuestion, gloomUntil, gloomUntilQuestion, gloomUntilRange;
    private final int rollQuestion, rollBound, showerStart, showerStartQuestion, showerStartRange, showerLength,
            showerLengthQuestion, showerLengthRange;
    /** Ticks a second (scene.json): the tick is epoch milliseconds * ticksPerSecond div 1000. */
    final int ticksPerSecond;

    // ------------------------------------------------------------------------------------------- buffers for a frame

    private final byte[] idx = new byte[W * H];
    private final int[] frameRgb = new int[256];
    private final boolean[] frameShown = new boolean[256];
    private final byte[] moveScratch;                     // as large as the largest part
    private final byte[] shadowBase = new byte[W * H];    // the frame as it was before any shadow was laid
    private final int[] fadeOld = new int[W * H], fadeNew = new int[W * H], statePrev = new int[W * H], poseOld = new int[W * H];
    /** The poses of this render: old (-1 unless a change fades), new (-1: no dog), step. */
    private final int[] chosen = new int[3];
    private final int[] orderNow, orderBefore;            // poseOfSlot's two shuffles
    private final int[] glyphSheet = new int[256], glyphSx = new int[256], glyphW = new int[256], glyphX = new int[256], glyphY = new int[256];
    private int glyphs;
    private long textKey = -1;
    private String textDate;
    private List<String> textQuote;
    /** The minute before the one asked about: year, month, day, hour, minute. */
    private int py, pm, pd, ph, pmi;

    private static final class Move {
        boolean regular;
        int period, length, slot, spread, a, b, salt, ticksPerFrame;
        int[][] frames;                                   // each frame: ops flattened, see apply()
    }

    /** One part of a pose: an image of the art folder placed at (dogX + atX, dogY + atY). */
    private static final class Part {
        byte[] still, frame;                              // the image as loaded, and as moved at this tick
        int w, h, atX, atY;
        boolean flat;
        int[] ground;                                     // a row for each column, -1 for none; null when flat
        Move[] moves;
    }

    private static final Part[] NO_PARTS = {};
    private final Part house;                             // the doghouse's shape that casts its shadow (scene.py's house_cast)
    private Part[] doorParts;                             // the dog in the doghouse's doorway (house.pose); null: he never goes in
    private String doorName;
    private int[] stayLook;                               // house.stay: see inHouse
    private int stayOutOneIn, staySalt;

    /** One item of scene.json's specials: a sprite of the sheet shown at (x, y) on the dates of its rules. */
    private static final class Special {
        String name;
        int slot;                                         // which of SLOTS draws it
        boolean anyDate, clear, once;                     // no date rule; only in clear weather; frames play once
        int[] days, every, move, jitter;                  // tools/scene_surprises.py describes them; null: none
        int fade;
        int x, y, sx, sy, w, h, frames, ticks, ahead, hourFrom = -1, hourTo;
        boolean[] states;                                 // null: every state
        int[][] when;                                     // each rule: RULE_RANGE, RULE_NTH or RULE_EASTER, then its numbers
    }

    private static final int RULE_RANGE = 0, RULE_NTH = 1, RULE_EASTER = 2;
    private static final String[] SLOTS = {"specials_back", "specials_front", "surprises_sky", "surprises_back", "surprises_front"};
    private static final int[] BAYER = {0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5};

    private static final int OP_RECOLOUR = 0, OP_SHIFT = 1, OP_SHEAR = 2;

    // ------------------------------------------------------------------------------------------- reading the files

    /** Reads and decodes every file once. */
    public Scene(Files files) throws IOException {
        Map<String, Object> sc = obj(Json.parse(text(files, "scene.json")));
        List<Object> dayColors = list(obj(Json.parse(text(files, "palettes/day.json"))).get("colors"));
        for (int i = 0; i < dayColors.size(); i++) roleIndex.put((String) obj(dayColors.get(i)).get("name"), i);
        this.files = files;
        monthFadeDays = num(obj(sc.get("months")).get("fade_days"));

        List<Object> orderList = list(sc.get("order"));
        order = new String[orderList.size()];
        for (int i = 0; i < order.length; i++) order[i] = (String) orderList.get(i);
        List<Object> cno = list(sc.get("clear_night_only"));
        clearNightOnly = new boolean[order.length];
        for (int i = 0; i < order.length; i++) clearNightOnly[i] = cno.contains(order[i]);
        moonClearNightOnly = cno.contains("moon");
        Map<String, Object> full = obj(sc.get("full_layers"));
        for (Map.Entry<String, Object> e : full.entrySet()) fullLayers.put(e.getKey(), layer(files, (String) e.getValue()));

        Map<String, Object> states = obj(sc.get("states"));
        for (int s = 0; s < 6; s++) {
            Map<String, Object> st = obj(states.get(STATES[s]));
            stateSky[s] = layer(files, (String) st.get("sky"));
            stateSea[s] = layer(files, (String) st.get("sea"));
            stateSand[s] = layer(files, (String) st.get("sand"));
            stateSun[s] = st.get("sun") == null ? null : ints(st.get("sun"));
        }
        Map<String, Object> parts = obj(sc.get("day_parts"));
        sunrise = ints(parts.get("sunrise"));
        sunset = ints(parts.get("sunset"));
        if (sunrise.length != 12 || sunset.length != 12) throw new IOException("scene.json: day_parts needs twelve months");
        summerTime = "us".equals(parts.get("summer_time"));
        System.arraycopy(ints(parts.get("dawn")), 0, dawn, 0, 2);
        System.arraycopy(ints(parts.get("dusk")), 0, dusk, 0, 2);

        Map<String, Object> s0 = obj(sc.get("sun"));
        sun = layer(files, (String) s0.get("file"));
        sunCx = ints(s0.get("centre"))[0];
        sunCy = ints(s0.get("centre"))[1];
        Map<String, Object> m = obj(sc.get("moon"));
        moon = layer(files, (String) m.get("file"));
        moonSize = num(m.get("size"));
        moonCx = ints(m.get("centre"))[0];
        moonCy = ints(m.get("centre"))[1];
        moonX = ints(m.get("at"))[0];
        moonY = ints(m.get("at"))[1];
        for (Object o : list(m.get("states"))) moonStates[state((String) o)] = true;
        moonEpoch = (Long) m.get("epoch_jd_e9");
        moonMonth = (Long) m.get("month_e9");

        Map<String, Object> g = obj(sc.get("glints"));
        glintRoles = roles(list(g.get("roles")));
        glintStep = num(g.get("ticks_per_step"));
        glintShown = num(g.get("shown"));
        Map<String, Object> p = obj(sc.get("paths"));
        pathStep = num(p.get("ticks_per_step"));
        pathFrames = num(p.get("frames"));
        List<Integer> pr = new ArrayList<>();
        List<String> pd0 = new ArrayList<>();
        for (Object prefix : list(p.get("prefixes"))) {
            for (Object c : dayColors) {
                String name = (String) obj(c).get("name"), pre = (String) prefix;
                if (name.startsWith(pre) && name.length() > pre.length() && name.substring(pre.length()).chars().allMatch(Character::isDigit)) {
                    pr.add(roleIndex.get(name));
                    pd0.add(name.substring(pre.length()));
                }
            }
        }
        pathRoles = new int[pr.size()];
        pathDigits = new String[pr.size()];
        for (int i = 0; i < pathRoles.length; i++) {
            pathRoles[i] = pr.get(i);
            pathDigits[i] = pd0.get(i);
        }
        Map<String, Object> t = obj(sc.get("twinkle"));
        twinkleRoles = roles(list(t.get("roles")));
        twinkleSlot = num(t.get("slot"));
        twinkleOneIn = num(t.get("one_in"));
        twinkleSalt = num(t.get("salt"));
        twinkleDimTo = role((String) t.get("dim_to"));

        Map<String, Object> b = obj(sc.get("beam"));
        beam = layer(files, (String) b.get("file"));
        beamX = ints(b.get("at"))[0];
        beamY = ints(b.get("at"))[1];
        beamW = ints(b.get("size"))[0];
        beamTicks = num(b.get("ticks_per_frame"));
        beamFrames = num(b.get("frames"));
        Map<String, Object> f = obj(sc.get("foam"));
        foam = layer(files, (String) f.get("file"));
        foamTop = num(f.get("top"));
        foamH = num(f.get("frame_height"));
        foamFrames = num(f.get("frames"));
        foamTicks = num(f.get("ticks_per_frame"));
        Map<String, Object> r = obj(sc.get("ripples"));
        ripples = layer(files, (String) r.get("file"));
        ripplesTop = num(r.get("top"));
        ripplesH = num(r.get("frame_height"));
        ripplesFrames = num(r.get("frames"));
        ripplesTicks = num(r.get("ticks_per_frame"));
        ripplesWeather = weather((String) r.get("weather"));
        Map<String, Object> rn = obj(sc.get("rain"));
        rainWeather = weather((String) rn.get("weather"));
        rainTileW = ints(rn.get("tile"))[0];
        rainTileH = ints(rn.get("tile"))[1];
        rainLean = num(rn.get("lean"));
        Map<String, Object> rl = obj(rn.get("layers"));
        rainFar = layer(files, (String) obj(rl.get("rain_far")).get("file"));
        rainFarSpeed = num(obj(rl.get("rain_far")).get("speed"));
        rainNear = layer(files, (String) obj(rl.get("rain_near")).get("file"));
        rainNearSpeed = num(obj(rl.get("rain_near")).get("speed"));
        Map<String, Object> fd = obj(sc.get("fade"));
        fadeSteps = num(fd.get("steps"));
        fadeTicks = num(fd.get("ticks"));
        lightMinutes = num(obj(fd.get("light")).get("minutes"));
        lightSteps = num(obj(fd.get("light")).get("steps"));

        Map<String, Object> c = obj(sc.get("clouds"));
        clouds = layer(files, (String) c.get("file"));
        for (int w = 0; w < 3; w++) {
            cloudsShown[w] = num(obj(c.get("shown")).get(WEATHERS[w]));
            cloudsGrown[w] = (Boolean) obj(c.get("grown")).get(WEATHERS[w]);
        }
        cloudsShownClear = ints(c.get("shown_clear"));
        if (cloudsShownClear.length != 12) throw new IOException("scene.json: clouds.shown_clear needs twelve months");
        Map<String, Object> sp = obj(sc.get("specials"));
        specials = layer(files, (String) sp.get("file"));
        List<Object> spItems = list(sp.get("items"));
        specialItems = new Special[spItems.size()];
        specialToday = new boolean[specialItems.length];
        for (int i = 0; i < specialItems.length; i++) {
            Map<String, Object> e = obj(spItems.get(i));
            Special it = gates(e);
            String slot = (String) e.get("slot");
            it.slot = java.util.Arrays.asList(SLOTS).indexOf(slot);
            if (it.slot < 0) throw new IOException("scene.json: unknown slot " + slot);
            int[] at = ints(e.get("at")), sheet = ints(e.get("sheet"));
            it.x = at[0];
            it.y = at[1];
            it.sx = sheet[0];
            it.sy = sheet[1];
            it.w = sheet[2];
            it.h = sheet[3];
            it.frames = num(e.get("frames"));
            it.ticks = num(e.get("ticks_per_frame"));
            it.ahead = num(e.get("ahead"));
            it.once = Boolean.TRUE.equals(e.get("once"));
            it.every = e.get("every") == null ? null : ints(e.get("every"));
            it.move = e.get("move") == null ? null : ints(e.get("move"));
            it.jitter = e.get("jitter") == null ? null : ints(e.get("jitter"));
            it.fade = num(e.get("fade"));
            if (it.fade > 0 && it.every == null) throw new IOException("scene.json: " + it.name + " fades without a timetable");
            specialItems[i] = it;
        }
        slotOfOrder = new int[order.length];
        for (int i = 0; i < order.length; i++) slotOfOrder[i] = java.util.Arrays.asList(SLOTS).indexOf(order[i]);
        List<Object> tintList = list(sp.get("tints"));
        tints = new Special[tintList.size()];
        tintRoles = new int[tints.length][];
        tintRgb = new int[tints.length][];
        for (int i = 0; i < tints.length; i++) {
            Map<String, Object> e = obj(tintList.get(i));
            tints[i] = gates(e);
            Map<String, Object> colours = obj(e.get("roles"));
            tintRoles[i] = new int[colours.size()];
            tintRgb[i] = new int[colours.size()];
            int k = 0;
            for (Map.Entry<String, Object> colour : colours.entrySet()) {
                tintRoles[i][k] = role(colour.getKey());
                tintRgb[i][k++] = Integer.parseInt((String) colour.getValue(), 16);
            }
        }
        Map<String, Object> me = obj(sp.get("meteors"));
        meteorSlot = num(me.get("slot_ms"));
        meteorOneIn = num(me.get("one_in"));
        meteorLife = num(me.get("life_ms"));
        meteorFade = num(me.get("fade_ms"));
        meteorTail = num(me.get("tail"));
        meteorSalt = num(me.get("salt"));
        meteorBox = ints(me.get("box"));
        meteorSpeed = ints(me.get("speed"));
        meteorSlope = ints(me.get("slope"));
        meteorLevels = roles(list(me.get("levels")));
        List<Object> showers = list(me.get("showers"));
        meteorShowers = new int[showers.size()][];
        for (int i = 0; i < meteorShowers.length; i++) meteorShowers[i] = ints(showers.get(i));
        if (meteorTail + 1 > meteorPx.length / 3) throw new IOException("scene.json: the shooting star's tail is too long");
        for (Map.Entry<String, Integer> named : roleIndex.entrySet()) {
            String n = named.getKey();
            skyRole[named.getValue()] = n.startsWith("SKY_") || n.startsWith("STAR_") || n.startsWith("AURORA_");
        }
        cloudSpan = num(c.get("span"));
        cloudLeft = num(c.get("left"));
        List<Object> tracks = list(c.get("tracks"));
        cloudTracks = new int[tracks.size()][];
        for (int k = 0; k < tracks.size(); k++) {
            Map<String, Object> tr = obj(tracks.get(k));
            int[] row = new int[15];
            row[0] = num(tr.get("row"));
            row[1] = num(tr.get("start_x"));
            row[2] = num(tr.get("ticks_per_px"));
            for (int sz = 0; sz < 2; sz++) {
                Map<String, Object> one = obj(tr.get(sz == 0 ? "normal" : "grown"));
                int[] sh = ints(one.get("sheet"));
                System.arraycopy(sh, 0, row, 3 + sz * 6, 4);
                row[7 + sz * 6] = num(one.get("dx"));
                row[8 + sz * 6] = num(one.get("dy"));
            }
            cloudTracks[k] = row;
        }

        Map<String, Object> d = obj(sc.get("dog"));
        dogX = num(d.get("x"));
        dogY = num(d.get("y"));
        List<Object> ps = list(d.get("poses"));
        poseNames = new String[ps.size()];
        poses = new Part[ps.size()][];
        int largest = 0;
        for (int k = 0; k < poses.length; k++) {
            Map<String, Object> pose = obj(ps.get(k));
            poseNames[k] = (String) pose.get("name");
            List<Object> pl = list(pose.get("parts"));
            poses[k] = new Part[pl.size()];
            for (int j = 0; j < pl.size(); j++) {
                Part part = part(files, obj(pl.get(j)));
                poses[k][j] = part;
                largest = Math.max(largest, part.w * part.h);
            }
        }
        Map<String, Object> houseEntry = obj(sc.get("house"));
        house = part(files, obj(houseEntry.get("cast")));
        house.frame = house.still;                        // it has no moves
        if (houseEntry.containsKey("pose")) {
            Map<String, Object> doorPose = obj(houseEntry.get("pose")), stayEntry = obj(houseEntry.get("stay"));
            List<Object> doorList = list(doorPose.get("parts"));
            doorName = (String) doorPose.get("name");
            doorParts = new Part[doorList.size()];
            for (int j = 0; j < doorParts.length; j++) {
                doorParts[j] = part(files, obj(doorList.get(j)));
                largest = Math.max(largest, doorParts[j].w * doorParts[j].h);
            }
            stayLook = ints(stayEntry.get("look_minutes"));
            stayOutOneIn = num(stayEntry.get("out_one_in"));
            staySalt = num(stayEntry.get("salt"));
        }
        moveScratch = new byte[largest];
        orderNow = new int[poses.length];
        orderBefore = new int[poses.length];
        Map<String, Object> pc = obj(d.get("pose_change"));
        poseHold = num(pc.get("hold"));
        poseJitter = num(pc.get("jitter"));
        poseFadeTicks = num(pc.get("fade_ticks"));
        poseSalt = num(pc.get("salt"));
        poseOrderSalt = num(pc.get("order_salt"));
        for (int s = 0; s < 7; s++) {
            String key = s == NO_MOON ? "no_moon" : STATES[s];
            shadowLean[s] = ints(obj(d.get("shadow")).get(key));
            shadowThick[s] = num(obj(d.get("shadow_thick")).get(key));
        }
        List<Object> byMonth = list(d.get("shadow_day"));
        for (int k = 0; k < 12; k++) shadowDay[k] = ints(byMonth.get(k));
        byte shadowRole = (byte) role("DOG_SHADOW");      // scene.py's sand_roles: every index in any state's sand
        for (int s = 0; s < 6; s++) for (byte v : stateSand[s].index) if (v != 0) shadowTarget[v & 255] = shadowRole;
        for (Map.Entry<String, Object> e : obj(d.get("shadow_onto")).entrySet()) {
            shadowTarget[role(e.getKey())] = (byte) role((String) e.getValue());
        }
        textRole = role("TEXT");
        edgeRole = role("TEXT_EDGE");

        Map<String, Object> tx = obj(sc.get("text"));
        for (int s = 0; s < 6; s++) textOpacity[s] = num(obj(tx.get("opacity")).get(STATES[s]));
        font = layer(files, (String) tx.get("font"));
        digits = layer(files, (String) tx.get("digits"));
        fontChars = (String) tx.get("chars");
        cellW = ints(tx.get("cell"))[0];
        advance = num(tx.get("advance"));
        line = num(tx.get("line"));
        marginX = num(tx.get("margin_x"));
        marginY = num(tx.get("margin_y"));
        quoteChars = num(tx.get("quote_chars"));
        quoteLines = num(tx.get("quote_lines"));
        quoteEpoch = num(tx.get("quote_epoch_year"));
        Map<String, Object> dc = obj(tx.get("digit_cells"));
        for (int k = 0; k < 11; k++) digitCells[k] = ints(dc.get(k < 10 ? String.valueOf(k) : ":"));
        try (BufferedReader in = new BufferedReader(new InputStreamReader(files.open((String) tx.get("quotes")), StandardCharsets.UTF_8))) {
            for (String q; (q = in.readLine()) != null; ) if (!q.trim().isEmpty()) quotes.add(q.trim());
        }
        quoteSalt = num(tx.get("quote_salt"));
        quotePass = new int[quotes.size()];
        quotePassBefore = new int[quotes.size()];

        Map<String, Object> wt = obj(sc.get("weather"));
        List<Object> names = list(wt.get("names"));
        for (int k = 0; k < 3; k++) if (!WEATHERS[k].equals(names.get(k))) throw new IOException("scene.json: weather names out of order");
        List<Object> odds = list(wt.get("odds"));
        for (int k = 0; k < 12; k++) weatherOdds[k] = ints(odds.get(k));
        Map<String, Object> gl = obj(wt.get("gloom"));
        gloomOdds = ints(gl.get("odds"));
        gloomQuestion = num(gl.get("question"));
        gloomUntil = num(gl.get("until"));
        gloomUntilQuestion = num(gl.get("until_question"));
        gloomUntilRange = num(gl.get("until_range"));
        rollQuestion = num(wt.get("roll_question"));
        rollBound = num(wt.get("roll_bound"));
        Map<String, Object> sh = obj(wt.get("shower"));
        showerStart = num(sh.get("start"));
        showerStartQuestion = num(sh.get("start_question"));
        showerStartRange = num(sh.get("start_range"));
        showerLength = num(sh.get("length"));
        showerLengthQuestion = num(sh.get("length_question"));
        showerLengthRange = num(sh.get("length_range"));
        ticksPerSecond = num(sc.get("ticks_per_second"));
        Map<String, Object> ev = obj(sc.get("evening"));
        brightDay = num(ev.get("day"));
        brightEvening = num(ev.get("evening"));
        brightNight = num(ev.get("night"));
        nightFrom = num(ev.get("night_from"));
        nightRamp = num(ev.get("night_ramp"));
        holdMinutes = num(ev.get("hold_minutes"));
        fadeMinutes = num(ev.get("fade_minutes"));
        eveningDawn = num(ev.get("dawn_ramp"));
        eveningWarmAfter = num(ev.get("warm_after_sunset"));
        eveningGreen = num(ev.get("warm_green"));
        eveningBlue = num(ev.get("warm_blue"));
    }

    /** scene.py's load_part: one entry of a pose's parts, with its image read from the art folder. */
    private Part part(Files files, Map<String, Object> e) throws IOException {
        String file = (String) e.get("file");
        Png png = Png.read(files.open(file), file);
        Part p = new Part();
        p.still = png.index;
        p.w = png.width;
        p.h = png.height;
        p.frame = new byte[p.w * p.h];
        if (e.containsKey("at")) {
            p.atX = ints(e.get("at"))[0];
            p.atY = ints(e.get("at"))[1];
        }
        p.flat = Boolean.TRUE.equals(e.get("flat"));
        if (!p.flat) p.ground = groundRows(p, e.get("ground"));
        List<Object> mv = e.containsKey("moves") ? list(e.get("moves")) : new ArrayList<>();
        p.moves = new Move[mv.size()];
        for (int k = 0; k < p.moves.length; k++) p.moves[k] = move(obj(mv.get(k)));
        return p;
    }

    /** scene.py's ground_rows: the one row given for every column, or for "outline" the lowest opaque row of each
     *  column of the image as loaded, -1 in a column with no opaque pixel. */
    private static int[] groundRows(Part p, Object ground) {
        int[] rows = new int[p.w];
        if (!"outline".equals(ground)) {
            java.util.Arrays.fill(rows, num(ground));
            return rows;
        }
        for (int x = 0; x < p.w; x++) {
            rows[x] = -1;
            for (int y = p.h - 1; y >= 0; y--) {
                if (p.still[y * p.w + x] != 0) {
                    rows[x] = y;
                    break;
                }
            }
        }
        return rows;
    }

    private Move move(Map<String, Object> m) {
        Move mv = new Move();
        Map<String, Object> t = obj(m.get("timetable"));
        mv.regular = t.containsKey("period");
        mv.length = num(t.get("length"));
        if (mv.regular) {
            mv.period = num(t.get("period"));
        } else {
            mv.slot = num(t.get("slot"));
            mv.spread = num(t.get("spread"));
            mv.a = ints(t.get("chance"))[0];
            mv.b = ints(t.get("chance"))[1];
            mv.salt = num(t.get("salt"));
        }
        mv.ticksPerFrame = num(m.get("ticks_per_frame"));
        List<Object> frames = list(m.get("frames"));
        mv.frames = new int[frames.size()][];
        for (int k = 0; k < frames.size(); k++) {
            List<Integer> ops = new ArrayList<>();
            for (Object o : list(frames.get(k))) {
                Map<String, Object> op = obj(o);
                String kind = (String) op.get("op");
                if (kind.equals("recolour")) {
                    List<Object> cells = list(op.get("cells"));
                    ops.add(OP_RECOLOUR);
                    ops.add(role((String) op.get("to")));
                    ops.add(cells.size());
                    for (Object cell : cells) {
                        ops.add(ints(cell)[0]);
                        ops.add(ints(cell)[1]);
                    }
                } else if (kind.equals("shift")) {
                    int[] rect = ints(op.get("rect"));
                    ops.add(OP_SHIFT);
                    for (int v : rect) ops.add(v);
                    ops.add(num(op.get("dx")));
                    ops.add(num(op.get("dy")));
                    ops.add(op.get("fill") == null ? 0 : role((String) op.get("fill")));
                } else if (kind.equals("shear")) {
                    int[] rect = ints(op.get("rect")), dx = ints(op.get("dx"));
                    ops.add(OP_SHEAR);
                    for (int v : rect) ops.add(v);
                    ops.add(dx.length);
                    for (int v : dx) ops.add(v);
                } else {
                    throw new IllegalArgumentException("scene.json: unknown dog operation " + kind);
                }
            }
            int[] flat = new int[ops.size()];
            for (int i = 0; i < flat.length; i++) flat[i] = ops.get(i);
            mv.frames[k] = flat;
        }
        return mv;
    }

    /** What says when an item of the specials, or a tint, may show: its name, states, weather, hours, date rules and day lottery. */
    private static Special gates(Map<String, Object> e) throws IOException {
        Special it = new Special();
        it.name = (String) e.get("name");
        if (e.get("states") != null) {
            it.states = new boolean[6];
            for (Object o : list(e.get("states"))) it.states[state((String) o)] = true;
        }
        if (e.get("hours") != null) {
            it.hourFrom = ints(e.get("hours"))[0];
            it.hourTo = ints(e.get("hours"))[1];
        }
        it.clear = Boolean.TRUE.equals(e.get("clear"));
        it.days = e.get("days") == null ? null : ints(e.get("days"));
        it.anyDate = e.get("when") == null;
        List<Object> rules = it.anyDate ? new ArrayList<>() : list(e.get("when"));
        it.when = new int[rules.size()][];
        for (int q = 0; q < it.when.length; q++) {
            List<Object> rule = list(rules.get(q));
            String kind = (String) rule.get(0);
            int[] v = new int[rule.size()];
            v[0] = kind.equals("range") ? RULE_RANGE : kind.equals("nth") ? RULE_NTH : kind.equals("easter") ? RULE_EASTER : -1;
            if (v[0] < 0 || v.length != (v[0] == RULE_RANGE ? 5 : v[0] == RULE_NTH ? 6 : 3)) throw new IOException("scene.json: a rule Scene does not know: " + rule);
            for (int k = 1; k < v.length; k++) v[k] = num(rule.get(k));
            it.when[q] = v;
        }
        return it;
    }

    private Png layer(Files files, String name) throws IOException {
        Png png = layers.get(name);
        if (png == null) {
            png = Png.read(files.open("layers/" + name), "layers/" + name);
            layers.put(name, png);
        }
        return png;
    }

    private static String text(Files files, String path) throws IOException {
        return new String(Png.readAll(files.open(path)), StandardCharsets.UTF_8);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> obj(Object o) {
        return (Map<String, Object>) o;
    }

    @SuppressWarnings("unchecked")
    private static List<Object> list(Object o) {
        return (List<Object>) o;
    }

    private static int num(Object o) {
        return Math.toIntExact((Long) o);
    }

    private static int[] ints(Object o) {
        List<Object> l = list(o);
        int[] out = new int[l.size()];
        for (int i = 0; i < out.length; i++) out[i] = num(l.get(i));
        return out;
    }

    private int role(String name) {
        Integer i = roleIndex.get(name);
        if (i == null) throw new IllegalArgumentException("no role " + name + " in palettes/day.json");
        return i;
    }

    private int[] roles(List<Object> names) {
        int[] out = new int[names.size()];
        for (int i = 0; i < out.length; i++) out[i] = role((String) names.get(i));
        return out;
    }

    static int state(String name) {
        for (int s = 0; s < 6; s++) if (STATES[s].equals(name)) return s;
        throw new IllegalArgumentException("no state " + name);
    }

    static int weather(String name) {
        for (int w = 0; w < 3; w++) if (WEATHERS[w].equals(name)) return w;
        throw new IllegalArgumentException("no weather " + name);
    }

    // ------------------------------------------------------------------------------------------- the day

    /** scene.py's beach_hash: depends only on the low 32 bits of each input, so a long slot number is passed as (int) slot. */
    static int hash(int x, int y, int seed) {
        int h = x * 0x27D4EB2D + y * 0x165667B1 + seed * 0x9E3779B9;
        h ^= h >>> 15;
        h *= 0x85EBCA6B;
        h ^= h >>> 13;
        h *= 0xC2B2AE35;
        return (h ^ (h >>> 16)) & 0x7FFFFFFF;
    }

    static int daysInMonth(int year, int month) {
        if (month == 2) return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0) ? 29 : 28;
        return month == 4 || month == 6 || month == 9 || month == 11 ? 30 : 31;
    }

    /** scene.py's between_months: the date's value from a table of twelve, one for the 15th of each month. */
    static int betweenMonths(int[] table, int year, int month, int day) {
        int a, b, n, k;
        if (day >= 15) {
            a = month;
            b = month % 12 + 1;
            n = daysInMonth(year, month);
            k = day - 15;
        } else {
            a = (month + 10) % 12 + 1;
            n = daysInMonth(month > 1 ? year : year - 1, a);
            b = month;
            k = n - (15 - day);
        }
        return (table[a - 1] * (n - k) + table[b - 1] * k + n / 2) / n;
    }

    /** scene.py's us_summer_time: from 03:00 on the second Sunday of March until 01:00 on the first Sunday of November. */
    static boolean usSummerTime(int year, int month, int day, int hour) {
        if (month != 3 && month != 11) return month > 3 && month < 11;
        int firstSunday = 1 + (int) ((7 - (julianDay(year, month, 1) + 1) % 7) % 7);    // (jd + 1) % 7 is 0 on a Sunday
        if (month == 3) return day > firstSunday + 7 || (day == firstSunday + 7 && hour >= 3);
        return day < firstSunday || (day == firstSunday && hour < 1);
    }

    /** For eveningFactors: the brightness the hour settles at, however long the screensaver has run. */
    public static final long SETTLED = Long.MIN_VALUE;

    /** scene.py's settled_brightness: the picture's brightness in thousandths once the screensaver has run its hold
     *  and its fade: day from sunrise to sunset, down to evening over warm_after_sunset minutes after sunset, down to
     *  night over night_ramp minutes from night_from, back to day over the dawn_ramp minutes before sunrise. */
    int settledBrightness(int year, int month, int day, int hour, int minute, int second) {
        int s = hour * 3600 + minute * 60 + second, ahead = summerTime && usSummerTime(year, month, day, hour) ? 60 : 0;
        int rise = 60 * (betweenMonths(sunrise, year, month, day) + ahead), set = 60 * (betweenMonths(sunset, year, month, day) + ahead);
        int dayB = 10 * brightDay, eveningB = 10 * brightEvening, nightB = 10 * brightNight;
        int dawnS = 60 * eveningDawn, afterS = 60 * eveningWarmAfter, b;
        if (s < rise - dawnS) b = nightB;
        else if (s < rise) b = nightB + Math.floorDiv((dayB - nightB) * (s - (rise - dawnS)), dawnS);
        else if (s < set) b = dayB;
        else if (s < set + afterS) b = dayB + Math.floorDiv((eveningB - dayB) * (s - set), afterS);
        else b = eveningB;
        if (s >= 60 * nightFrom) {
            int ramp = 60 * nightRamp;
            b = b + Math.floorDiv((nightB - b) * Math.min(s - 60 * nightFrom, ramp), ramp);
        }
        return b;
    }

    /**
     * scene.py's evening_factors: how the finished frame is shown at this moment, as thousandths of red, green and
     * blue. The brightness is full when the screensaver starts and for hold_minutes after, then falls to
     * settledBrightness over fade_minutes (dreamingMs: how long the screensaver has run, below 0 counted as 0; SETTLED
     * for the level it settles at). The warmth:
     * after sunset green and blue fall to warm_green and warm_blue percent over warm_after_sunset minutes, stay
     * through the night and come back over the dawn_ramp minutes before sunrise. The television's backlight cannot be
     * set by an app; a darker picture is what dims it.
     */
    public void eveningFactors(int year, int month, int day, int hour, int minute, int second, long dreamingMs, int[] out) {
        int m = hour * 60 + minute, ahead = summerTime && usSummerTime(year, month, day, hour) ? 60 : 0;
        int rise = betweenMonths(sunrise, year, month, day) + ahead, set = betweenMonths(sunset, year, month, day) + ahead;
        int warm = 0;                                     // thousandths
        if (m < rise - eveningDawn) warm = 1000;
        else if (m < rise) warm = 1000 - 1000 * (m - (rise - eveningDawn)) / eveningDawn;
        else if (m >= set + eveningWarmAfter) warm = 1000;
        else if (m >= set) warm = 1000 * (m - set) / eveningWarmAfter;
        int b = settledBrightness(year, month, day, hour, minute, second);
        if (dreamingMs != SETTLED) {
            long fade = 60_000L * fadeMinutes, k = Math.min(Math.max(dreamingMs - 60_000L * holdMinutes, 0), fade);
            b = (int) (1000 - (1000 - b) * k / fade);
        }
        factors(b, warm, out);
    }

    /** The clock's colour (TEXT) in the palette of the frame drawn last, 0xRRGGBB: for the brightness test's label. */
    public int textColour() {
        return frameRgb[textRole];
    }

    /** The night's factors (fully warm) at a brightness in percent: for the brightness test (SceneView). */
    public void nightFactors(int percent, int[] out) {
        factors(10 * percent, 1000, out);
    }

    /** b: brightness in thousandths; warm: thousandths of the night's warmth. */
    private void factors(int b, int warm, int[] out) {
        out[0] = b;
        out[1] = b * (1000 - (100 - eveningGreen) * warm / 100) / 1000;
        out[2] = b * (1000 - (100 - eveningBlue) * warm / 100) / 1000;
    }

    int chooseState(int year, int month, int day, int hour, int minute, int weather) {
        int m = hour * 60 + minute, ahead = summerTime && usSummerTime(year, month, day, hour) ? 60 : 0;
        int rise = betweenMonths(sunrise, year, month, day) + ahead, set = betweenMonths(sunset, year, month, day) + ahead;
        if (m < rise + dawn[0] || m >= set + dusk[1]) return NIGHT;
        if (weather != CLEAR) return weather == CLOUDY ? OVERCAST : WET;
        if (m < rise + dawn[1]) return DAWN;
        if (m >= set + dusk[0]) return DUSK;
        return DAY;
    }

    static long julianDay(int year, int month, int day) {
        int a = (14 - month) / 12, y = year + 4800 - a, m = month + 12 * a - 3;
        return day + (153 * m + 2) / 5 + 365L * y + y / 4 - y / 100 + y / 400 - 32045;
    }

    /** scene.py's easter: {month, day} of Easter Sunday of the western churches in a year of the Gregorian calendar. */
    static int[] easter(int year) {
        int a = year % 19, b = year / 100, c = year % 100, d = b / 4, e = b % 4, g = (8 * b + 13) / 25;
        int h = (19 * a + b - d - g + 15) % 30, i = c / 4, k = c % 4, m = (32 + 2 * e + 2 * i - h - k) % 7;
        int n = (a + 11 * h + 19 * m) / 433, month = (h + m - 7 * n + 90) / 25;
        return new int[] {month, (h + m - 7 * n + 33 * month + 19) % 32};
    }

    /** scene.py's special_on: true on a date that one of the rules names (tools/scene_specials.py describes them). */
    static boolean specialOn(int[][] when, int year, int month, int day) {
        long jd = julianDay(year, month, day);
        for (int[] r : when) {
            if (r[0] == RULE_RANGE) {
                int first = r[1] * 100 + r[2], last = r[3] * 100 + r[4], here = month * 100 + day;
                if (first <= last ? first <= here && here <= last : here >= first || here <= last) return true;
                continue;
            }
            long target;
            int before, after;
            if (r[0] == RULE_NTH) {                      // julianDay % 7 is 0 on a Monday
                before = r[4];
                after = r[5];
                if (r[3] > 0) {
                    target = julianDay(year, r[1], 1);
                    target += Math.floorMod(r[2] - target, 7L) + 7L * (r[3] - 1);
                } else {
                    target = julianDay(year, r[1], daysInMonth(year, r[1]));
                    target -= Math.floorMod(target - r[2], 7L);
                }
            } else {
                int[] e = easter(year);
                target = julianDay(year, e[0], e[1]);
                before = r[1];
                after = r[2];
            }
            if (target - before <= jd && jd <= target + after) return true;
        }
        return false;
    }

    /** Fills specialToday for the date; kept while the date stays. */
    private void specialsOfDate(int year, int month, int day) {
        int key = year * 10000 + month * 100 + day;
        if (key == specialKey) return;
        for (int i = 0; i < specialItems.length; i++) specialToday[i] = specialItems[i].anyDate || specialOn(specialItems[i].when, year, month, day);
        specialKey = key;
    }

    /** The names of the items whose date rule holds on the date, in scene.json's order, with a space between; "-" for none. */
    String specialsOn(int year, int month, int day) {
        StringBuilder out = new StringBuilder();
        for (Special it : specialItems) if (!it.anyDate && specialOn(it.when, year, month, day)) out.append(out.length() > 0 ? " " : "").append(it.name);
        return out.length() > 0 ? out.toString() : "-";
    }

    /** scene.py's day_key: the number of the day, or block of days, that a lottery draws for. */
    private static long dayKey(int[] days, long jd, int hour) {
        return Math.floorDiv(jd - (days[3] != 0 && hour < 12 ? 1 : 0), (long) days[2]);
    }

    /** scene.py's gates_open, given whether the date rules hold. */
    private static boolean open(Special it, boolean dateOk, long jd, int hour, int weather, int state) {
        if (!dateOk || (it.states != null && !it.states[state]) || (it.clear && weather != CLEAR)) return false;
        if (it.hourFrom >= 0 && (hour < it.hourFrom || hour >= it.hourTo)) return false;
        return it.days == null || hash((int) dayKey(it.days, jd, hour), 0, it.days[1]) % it.days[0] == 0;
    }

    /** scene.py's window_start: the tick at which slot s of a timetable shows its item, or -1. */
    static long windowStart(int[] every, long s) {
        if (hash((int) s, 1, every[3]) % every[1] != 0) return -1;
        return s * every[0] + hash((int) s, 2, every[3]) % (every[0] - every[2] + 1);
    }

    private Special special(String name) {
        for (Special it : specialItems) if (it.name.equals(name)) return it;
        for (Special it : tints) if (it.name.equals(name)) return it;
        throw new IllegalArgumentException("scene.json has no special " + name);
    }

    /** For the tests: the start of slot s of an item's timetable, or -1. */
    long surpriseWindow(String name, long s) {
        return windowStart(special(name).every, s);
    }

    /** For the tests: whether an item's (or a tint's) day lottery lets it show on the date at that hour. */
    boolean surpriseLottery(String name, int year, int month, int day, int hour) {
        int[] days = special(name).days;
        return hash((int) dayKey(days, julianDay(year, month, day), hour), 0, days[1]) % days[0] == 0;
    }

    /** Shows one surprise (every item whose name begins with this, a tint of this name, or "shooting_star") over and
     *  over from this tick on, whatever the date, the hour, the light and the weather; null ends it. For looking at it
     *  on the television without waiting. */
    public void setDemo(String name, long tick) {
        demo = name;
        demoTick = tick;
    }

    /** The items of one slot of the specials: scene.py's special_piece for each, stamped. */
    private void specials(int slot, int year, int month, int day, int hour, int weather, int state, long tick) {
        specialsOfDate(year, month, day);
        long jd = julianDay(year, month, day);
        for (int i = 0; i < specialItems.length; i++) {
            Special it = specialItems[i];
            if (it.slot != slot) continue;
            boolean forced = demo != null && it.name.startsWith(demo);     // "aurora" is also its glints on the sea
            if (!forced && !open(it, specialToday[i], jd, hour, weather, state)) continue;
            long t = tick, key = it.days != null ? dayKey(it.days, jd, hour) : 0;
            if (it.every != null && forced) {            // the demo: its window again and again, three seconds apart
                long span = it.every[2] + 24;
                key = Math.floorDiv(tick - demoTick, span);
                t = Math.floorMod(tick - demoTick, span);
                if (t >= it.every[2]) continue;
            } else if (it.every != null) {
                key = Math.floorDiv(tick, (long) it.every[0]);
                long start = windowStart(it.every, key);
                if (start < 0 || tick < start || tick - start >= it.every[2]) continue;
                t = tick - start;
            }
            long k = Math.floorDiv(t + it.ahead, (long) it.ticks);
            int frame = it.once ? (int) Math.min(k, it.frames - 1) : (int) Math.floorMod(k, (long) it.frames);
            int x = it.x, y = it.y, level = 16;
            if (it.jitter != null) {
                x += hash((int) key, 3, it.jitter[2]) % (it.jitter[0] + 1);
                y += hash((int) key, 4, it.jitter[2]) % (it.jitter[1] + 1);
            }
            if (it.move != null) {
                x += (int) Math.floorDiv(t * it.move[0], (long) it.move[1]);
                y += (int) Math.floorDiv(t * it.move[2], (long) it.move[3]);
            }
            if (it.fade > 0) level = (int) Math.min(16, Math.min(16 * (t + 1) / it.fade, 16 * (it.every[2] - t) / it.fade));
            stamp(specials.index, specials.width, it.sx + frame * it.w, it.sy, it.w, it.h, x, y, level);
        }
    }

    /** scene.py's meteor_pixels: the shooting star of slot s, u milliseconds into its flight: x, y, level for each of
     *  its pixels in out; returns how many pixels. */
    private int meteorAt(long s, long u, int[] out) {
        if (u < 0 || u >= meteorLife) return 0;
        int k0 = (int) s, salt = meteorSalt;
        int hx = meteorBox[0] + hash(k0, 3, salt) % (meteorBox[2] - meteorBox[0] + 1);
        int hy = meteorBox[1] + hash(k0, 4, salt) % (meteorBox[3] - meteorBox[1] + 1);
        int way = hash(k0, 5, salt) % 2 != 0 ? 1 : -1;
        int speed = meteorSpeed[0] + hash(k0, 6, salt) % (meteorSpeed[1] - meteorSpeed[0] + 1);
        int slope = meteorSlope[0] + hash(k0, 7, salt) % (meteorSlope[1] - meteorSlope[0] + 1);
        int gone = (int) (u * speed / 1000), left = (int) (meteorLife - u), tail = Math.min(gone, meteorTail), n = 0;
        if (left < meteorFade) tail = tail * left / meteorFade;
        for (int k = 0; k <= tail; k++) {
            int d = gone - k, x = hx + way * d, y = hy + d * slope / 100;
            if (x < 0 || x >= W || y < 0 || y >= H) continue;
            out[n++] = x;
            out[n++] = y;
            out[n++] = k == 0 && left >= meteorFade ? 0 : k <= 3 ? 1 : 2;
        }
        return n / 3;
    }

    /** For the tests: scene.py's meteor_pixels at a millisecond, as "x,y,level x,y,level" ("-" for none), with the
     *  given odds of a slot. */
    String meteorPixels(long ms, int oneIn) {
        long s = Math.floorDiv(ms, (long) meteorSlot);
        if (hash((int) s, 1, meteorSalt) % oneIn != 0) return "-";
        int n = meteorAt(s, ms - s * meteorSlot - hash((int) s, 2, meteorSalt) % (meteorSlot - meteorLife + 1), meteorPx);
        StringBuilder b = new StringBuilder();
        for (int j = 0; j < n; j++) b.append(j > 0 ? " " : "").append(meteorPx[3 * j]).append(',').append(meteorPx[3 * j + 1]).append(',').append(meteorPx[3 * j + 2]);
        return n > 0 ? b.toString() : "-";
    }

    /** The shooting star at this millisecond, for the view to draw over the frame it last asked for: x, y and colour
     *  (0xFFrrggbb) of each of its pixels that lies on the sky of that frame; returns how many. Only on a clear
     *  night (scene.py's meteor). out holds three numbers a pixel. On the thread that draws the frames. The view
     *  uses meteorOver over a slot's snapshot; this is the reference that shootingStarFromASnapshot holds it to. */
    int meteor(long ms, int[] out) {
        int[] levels = new int[meteorLevels.length];
        for (int k = 0; k < levels.length; k++) levels[k] = frameRgb[meteorLevels[k]];
        return meteorOver(ms, idx, levels, lastState, lastWeather, lastMonth, lastDay, "shooting_star".equals(demo), meteorPx, out);
    }

    /** The number of colour levels of the shooting star (meteorLevelColours). */
    int meteorLevelCount() {
        return meteorLevels.length;
    }

    /** What meteorOver needs of the frame drawn last, copied for another thread: its indexes and the star's colours. */
    void meteorSnapshot(byte[] idxOut, int[] levelsOut) {
        System.arraycopy(idx, 0, idxOut, 0, idx.length);
        for (int k = 0; k < meteorLevels.length; k++) levelsOut[k] = frameRgb[meteorLevels[k]];
    }

    int lastState() {
        return lastState;
    }

    int lastWeather() {
        return lastWeather;
    }

    int lastMonth() {
        return lastMonth;
    }

    int lastDay() {
        return lastDay;
    }

    /** Whether the demo shows the shooting star over and over. */
    boolean starDemo() {
        return "shooting_star".equals(demo);
    }

    /** meteor over a frame given by its parts (meteorSnapshot, lastState ...): reads only scene.json's numbers, so
     *  any thread may call it with its own px (3 * METEOR_PIXELS) and out. */
    int meteorOver(long ms, byte[] frameIdx, int[] levels, int state, int weather, int month, int day, boolean forced,
                   int[] px, int[] out) {
        if (!forced && (state != NIGHT || weather != CLEAR)) return 0;
        long s, u;
        if (forced) {                                    // the demo: one every two and a half seconds
            s = Math.floorDiv(ms, 2500L);
            u = Math.floorMod(ms, 2500L);
        } else {
            int oneIn = meteorOneIn;
            for (int[] sh : meteorShowers) {
                int first = sh[0] * 100 + sh[1], last = sh[2] * 100 + sh[3], here = month * 100 + day;
                if (first <= last ? first <= here && here <= last : here >= first || here <= last) oneIn = sh[4];
            }
            s = Math.floorDiv(ms, (long) meteorSlot);
            if (hash((int) s, 1, meteorSalt) % oneIn != 0) return 0;
            u = ms - s * meteorSlot - hash((int) s, 2, meteorSalt) % (meteorSlot - meteorLife + 1);
        }
        int n = meteorAt(s, u, px), kept = 0;
        for (int j = 0; j < n; j++) {
            int x = px[3 * j], y = px[3 * j + 1];
            if (!skyRole[frameIdx[y * W + x] & 255]) continue;
            out[3 * kept] = x;
            out[3 * kept + 1] = y;
            out[3 * kept++ + 2] = 0xFF000000 | levels[px[3 * j + 2]];
        }
        return kept;
    }

    int moonFrame(int year, int month, int day) {
        long since = Math.floorMod(julianDay(year, month, day) * 1_000_000_000L - moonEpoch, moonMonth);
        return (int) ((since * 16 + moonMonth) / (2 * moonMonth) % 8);
    }

    private static long mix64(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }

    static int pick(int year, int month, int day, int question, int bound) {
        long seed = mix64(year * 10000L + month * 100L + day);
        return (int) Long.remainderUnsigned(mix64(seed + question * 0x9E3779B97F4A7C15L), bound);
    }

    int dayWeather(int year, int month, int day) {
        int roll = pick(year, month, day, rollQuestion, rollBound);
        int[] odds = weatherOdds[month - 1];
        for (int w = 0; w < 3; w++) if (roll < odds[w]) return w;
        throw new IllegalStateException("weather odds do not reach the roll");
    }

    /** The weather for one minute: a rain day rains during its shower and is cloudy the rest of the day; a clear day
     *  with morning cloud (scene.py's gloom_end) is cloudy until that clears. */
    int weatherName(int year, int month, int day, int hour, int minute) {
        int w = dayWeather(year, month, day), m = hour * 60 + minute;
        if (w == CLEAR) {
            if (pick(year, month, day, gloomQuestion, 100) >= gloomOdds[month - 1]) return CLEAR;
            return m < gloomUntil + pick(year, month, day, gloomUntilQuestion, gloomUntilRange) ? CLOUDY : CLEAR;
        }
        if (w != RAIN) return w;
        int start = showerStart + pick(year, month, day, showerStartQuestion, showerStartRange);
        int end = Math.min(1440, start + showerLength + pick(year, month, day, showerLengthQuestion, showerLengthRange));
        return m >= start && m < end ? RAIN : CLOUDY;
    }

    /** Sets py, pm, pd, ph, pmi to the minute before. */
    private void minuteBefore(int year, int month, int day, int hour, int minute) {
        py = year;
        pm = month;
        pd = day;
        ph = hour;
        pmi = minute - 1;
        if (pmi >= 0) return;
        pmi = 59;
        ph = hour - 1;
        if (ph >= 0) return;
        ph = 23;
        LocalDate before = LocalDate.of(year, month, day).minusDays(1);
        py = before.getYear();
        pm = before.getMonthValue();
        pd = before.getDayOfMonth();
    }

    private long ticksIntoMinute(int second, int micros) {
        return (second * 1_000_000L + micros) * ticksPerSecond / 1_000_000;
    }

    /** scene.py's quote_of: the quote for the date and hour (minutes do not matter). A pass is n hours, in which every
     *  quote shows once for an hour; each pass has its own order (passOrder). H = whole days from 1 January of the epoch
     *  year to the date (29 February counts) * 24 + hour; the quote is place H mod n of pass H div n (floor division,
     *  so dates before the epoch work too). With two quotes they alternate, H mod 2; with one, it shows. */
    String quoteOf(int year, int month, int day, int hour) {
        int n = quotes.size();
        if (n == 1) return quotes.get(0);
        long h = (julianDay(year, month, day) - julianDay(quoteEpoch, 1, 1)) * 24 + hour;
        if (n == 2) return quotes.get((int) Math.floorMod(h, 2L));
        long p = Math.floorDiv(h, n);
        if (p != quotePassNumber) {
            passOrder(p);
            quotePassNumber = p;
        }
        return quotes.get(quotePass[(int) Math.floorMod(h, (long) n)]);
    }

    /** scene.py's pass_order, into quotePass: pass p's shuffle, with its first two places swapped when its first quote
     *  is the last of pass p - 1 (no quote two hours in a row; with n >= 3 the swap never moves a pass's last place). */
    private void passOrder(long p) {
        shuffled(p, quoteSalt, quotePass);
        shuffled(p - 1, quoteSalt, quotePassBefore);
        int n = quotePass.length;
        if (quotePass[0] == quotePassBefore[n - 1]) {
            int k = quotePass[0];
            quotePass[0] = quotePass[1];
            quotePass[1] = k;
        }
    }

    /** For the fast mode, whose clock runs through a day in seconds: the quote of this hour of the day shown, for the
     *  whole day; -1 for the clock's hour. */
    public void setFixedQuoteHour(int hour) {
        fixedQuoteHour = hour;
    }

    /** scene.py's wrap: lines of at most width characters, broken at spaces, and balanced: the text is filled at the
     *  narrowest width that still gives the same number of lines, so the last line is not left holding one short word. */
    static List<String> wrap(String text, int width) {
        List<String> lines = fill(text, width);
        int longest = 0;
        for (String word : text.trim().split("\\s+")) longest = Math.max(longest, word.length());
        for (int narrow = Math.max(1, Math.min(longest, width)); narrow < width; narrow++) {
            List<String> fewer = fill(text, narrow);
            if (fewer.size() == lines.size()) return fewer;
        }
        return lines;
    }

    /** scene.py's fill: each line takes as many words as fit in width characters; a longer word is cut. */
    static List<String> fill(String text, int width) {
        List<String> lines = new ArrayList<>();
        StringBuilder line = new StringBuilder();
        for (String word : text.trim().split("\\s+")) {
            while (word.length() > width) {
                if (line.length() > 0) {
                    lines.add(line.toString());
                    line.setLength(0);
                }
                lines.add(word.substring(0, width));
                word = word.substring(width);
            }
            if (word.isEmpty()) continue;
            if (line.length() > 0 && line.length() + 1 + word.length() > width) {
                lines.add(line.toString());
                line.setLength(0);
            }
            if (line.length() > 0) line.append(' ');
            line.append(word);
        }
        if (line.length() > 0) lines.add(line.toString());
        return lines;
    }

    // ------------------------------------------------------------------------------------------- the frame

    /** scene.render_now: the frame for a moment of local wall-clock time; out holds W*H pixels as 0xFFRRGGBB. pose as
     *  for render: -1 for the schedule. */
    public void renderNow(int[] out, int year, int month, int day, int hour, int minute, int second, int millis, long epochMs,
                          int pose) {
        long tick = Math.floorDiv(epochMs * ticksPerSecond, 1000);
        int now = weatherName(year, month, day, hour, minute);
        minuteBefore(year, month, day, hour, minute);
        int before = weatherName(py, pm, pd, ph, pmi);
        long ticks = ticksIntoMinute(second, millis * 1000);
        if (now == before || ticks >= fadeTicks) {
            render(out, year, month, day, hour, minute, second, millis * 1000, now, now, -1, tick, -1, pose);
        } else {
            render(out, year, month, day, hour, minute, second, millis * 1000, before, now, (int) (ticks * fadeSteps / fadeTicks), tick, -1, pose);
        }
    }

    /** scene.render. weatherStep &lt; 0: plain weatherNew; otherwise the fade (weatherOld, weatherNew, step). state: -1 for the one the time gives, or 0..5 in the order dawn, day, dusk, night, cloudy, rain. pose: -1 for the schedule (poseAt, with its fades), or a pose index (see pose) shown with no fade. */
    public void render(int[] out, int year, int month, int day, int hour, int minute, int second, int micros,
                       int weatherOld, int weatherNew, int weatherStep, long tick, int state, int pose) {
        if (pose >= 0) {
            chosen[0] = -1;
            chosen[1] = pose;
            chosen[2] = -1;
        } else {
            placeAt(chosen, year, month, day, hour, minute, second, micros, tick);
        }
        if (weatherStep < 0) {
            frame(out, year, month, day, hour, minute, second, micros, weatherNew, tick, state);
        } else {
            frame(fadeOld, year, month, day, hour, minute, second, micros, weatherOld, tick, state);
            frame(fadeNew, year, month, day, hour, minute, second, micros, weatherNew, tick, state);
            blend(fadeOld, fadeNew, weatherStep, out);
        }
    }

    /** scene.py's state_fade: true while the light changes from one state to the next, with light = {the state before,
     *  the state after, the step of lightSteps}. The change takes lightMinutes: into dawn or dusk in the minutes before
     *  that state begins, otherwise in the minutes after the boundary. A boundary is a minute b of this day, 1 to 1439,
     *  whose state differs from minute b - 1's; they are tried from the earliest. */
    private boolean stateFade(int year, int month, int day, int hour, int minute, int second, int micros, int weather) {
        int m = hour * 60 + minute, total = lightMinutes * 60 * ticksPerSecond;
        long intoMinute = ticksIntoMinute(second, micros);
        int first = Math.max(1, m - lightMinutes + 1), last = Math.min(1439, m + lightMinutes);
        int before = chooseState(year, month, day, (first - 1) / 60, (first - 1) % 60, weather);
        for (int b = first; b <= last; b++) {
            int after = chooseState(year, month, day, b / 60, b % 60, weather);
            if (after != before) {
                int start = after == DAWN || after == DUSK ? b - lightMinutes : b;
                long ticks = (long) (m - start) * 60 * ticksPerSecond + intoMinute;
                if (ticks >= 0 && ticks < total) {
                    light[0] = before;
                    light[1] = after;
                    light[2] = (int) (ticks * lightSteps / total);
                    return true;
                }
            }
            before = after;
        }
        return false;
    }

    /** One weather's frame; while the light changes (stateFade), the blend of the two states' frames. */
    private void frame(int[] dst, int year, int month, int day, int hour, int minute, int second, int micros, int weather,
                       long tick, int state) {
        boolean fading = state < 0 && stateFade(year, month, day, hour, minute, second, micros, weather);
        int now = state >= 0 ? state : fading ? light[1] : chooseState(year, month, day, hour, minute, weather);
        lastYear = year;
        lastMonth = month;
        lastDay = day;
        lastState = now;
        lastWeather = weather;
        // The state faded from is drawn first, so that idx and frameRgb end as the state faded to, for meteor.
        if (fading) finished(statePrev, year, month, day, hour, minute, weather, tick, light[0]);
        finished(dst, year, month, day, hour, minute, weather, tick, now);
        if (fading) blend(statePrev, dst, light[2], lightSteps, dst);
    }

    private void blend(int[] old, int[] now, int step, int[] out) {
        blend(old, now, step, fadeSteps, out);
    }

    /** scene.py's blend: each channel (old * (n - step) + now * step + n / 2) / n. */
    private void blend(int[] old, int[] now, int step, int n, int[] out) {
        int keep = n - step, half = n / 2;
        for (int i = 0; i < W * H; i++) {
            int a = old[i], b = now[i];
            int r = (((a >> 16) & 255) * keep + ((b >> 16) & 255) * step + half) / n;
            int g = (((a >> 8) & 255) * keep + ((b >> 8) & 255) * step + half) / n;
            int bl = ((a & 255) * keep + (b & 255) * step + half) / n;
            out[i] = 0xFF000000 | (r << 16) | (g << 8) | bl;
        }
    }

    /** One state's frame with the poses of this render: while a change of pose fades, the blend of the old pose's frame
     *  and the new one's. */
    private void finished(int[] dst, int year, int month, int day, int hour, int minute, int weather, long tick, int state) {
        // The old pose is drawn first, so that idx and frameRgb end as the new pose's, for meteor.
        if (chosen[0] >= 0) {
            indexes(year, month, day, hour, minute, weather, tick, state, chosen[0]);
            colours(poseOld, state);
        }
        indexes(year, month, day, hour, minute, weather, tick, state, chosen[1]);
        colours(dst, state);
        if (chosen[0] >= 0) blend(poseOld, dst, chosen[2], dst);
    }

    /** scene.py's coloured: the index frame as colours. In a state whose text is not solid, every pixel that the clock
     *  and the words changed is mixed with what lies under it. */
    private void colours(int[] dst, int state) {
        int a = textOpacity[state], b = 100 - a;
        for (int i = 0; i < W * H; i++) {
            int c = frameRgb[idx[i] & 255];
            if (a < 100 && idx[i] != textUnder[i]) {
                int u = frameRgb[textUnder[i] & 255];
                c = ((((c >> 16) & 255) * a + ((u >> 16) & 255) * b + 50) / 100 << 16)
                        | ((((c >> 8) & 255) * a + ((u >> 8) & 255) * b + 50) / 100 << 8) | (((c & 255) * a + (u & 255) * b + 50) / 100);
            }
            dst[i] = 0xFF000000 | c;
        }
    }

    /** scene.py's month_palette: the six palettes of month 1..12, read once. */
    private void readMonth(int month) {
        if (monthRgb[month - 1] != null) return;
        int[][] rgb = new int[6][256];
        boolean[][] shown = new boolean[6][256];
        try {
            for (int s = 0; s < 6; s++) {
                String path = "palettes/" + (month < 10 ? "0" : "") + month + "/" + STATES[s] + ".json";
                List<Object> colors = list(obj(Json.parse(text(files, path))).get("colors"));
                for (int i = 1; i < colors.size(); i++) {
                    Object hex = obj(colors.get(i)).get("hex");
                    if (hex == null) continue;
                    rgb[s][i] = Integer.parseInt((String) hex, 16);
                    shown[s][i] = true;
                }
            }
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
        monthRgb[month - 1] = rgb;
        monthShown[month - 1] = shown;
    }

    /** scene.py's palette(state, time) for all six states, into mixRgb and mixShown: the month's palette, mixed on the
     *  month's last fade days with the next month's (month_mix, mixed_palette). Kept while the date stays. */
    private void datePalette(int year, int month, int day) {
        int key = year * 10000 + month * 100 + day;
        if (key == mixKey) return;
        int k = Math.max(0, day - (daysInMonth(year, month) - monthFadeDays)), n = monthFadeDays + 1, next = month % 12 + 1;
        readMonth(month);
        if (k > 0) readMonth(next);
        boolean late = 2 * k >= n;
        for (int s = 0; s < 6; s++) {
            int[] a = monthRgb[month - 1][s];
            boolean[] sa = monthShown[month - 1][s];
            if (k == 0) {
                System.arraycopy(a, 0, mixRgb[s], 0, 256);
                System.arraycopy(sa, 0, mixShown[s], 0, 256);
                continue;
            }
            int[] b = monthRgb[next - 1][s];
            boolean[] sb = monthShown[next - 1][s];
            for (int i = 0; i < 256; i++) {
                if (sa[i] && sb[i]) {
                    int ca = a[i], cb = b[i];
                    int r = (((ca >> 16) & 255) * (n - k) + ((cb >> 16) & 255) * k + n / 2) / n;
                    int g = (((ca >> 8) & 255) * (n - k) + ((cb >> 8) & 255) * k + n / 2) / n;
                    int bl = ((ca & 255) * (n - k) + (cb & 255) * k + n / 2) / n;
                    mixRgb[s][i] = (r << 16) | (g << 8) | bl;
                    mixShown[s][i] = true;
                } else {                                  // a role only one month shows: its colour, from or until the middle
                    mixRgb[s][i] = sa[i] ? a[i] : sb[i] ? b[i] : 0;
                    mixShown[s][i] = sa[i] ? !late : sb[i] && late;
                }
            }
        }
        mixKey = key;
    }

    /** The palette of the state and the date (datePalette, called first) for this tick: glint groups and path roles out
     *  of phase hidden, twinkling stars dimmed. */
    private void frameColours(int state, long tick, int year, int month, int day, int hour) {
        System.arraycopy(mixRgb[state], 0, frameRgb, 0, 256);
        System.arraycopy(mixShown[state], 0, frameShown, 0, 256);
        for (int i = 0; i < tints.length; i++) {         // roles in another colour on some days (the surf that glows)
            Special t = tints[i];
            if (!t.name.equals(demo) && !open(t, t.anyDate || specialOn(t.when, year, month, day), julianDay(year, month, day), hour, CLEAR, state)) continue;
            for (int k = 0; k < tintRoles[i].length; k++) frameRgb[tintRoles[i][k]] = tintRgb[i][k];
        }
        int n = glintRoles.length, phase = (int) Math.floorMod(Math.floorDiv(tick, glintStep), (long) n);
        for (int k = 0; k < n; k++) if (Math.floorMod(k - phase, n) >= glintShown) frameShown[glintRoles[k]] = false;
        char digit = (char) ('0' + Math.floorMod(Math.floorDiv(tick, pathStep), (long) pathFrames));
        for (int k = 0; k < pathRoles.length; k++) if (pathDigits[k].indexOf(digit) < 0) frameShown[pathRoles[k]] = false;
        // scene.py: a group that twinkles in its slot fades to the dim stars' colour and back, evenly over the slot.
        int half = twinkleSlot / 2, stride = twinkleSlot / twinkleRoles.length, dim = frameRgb[twinkleDimTo];
        for (int k = 0; k < twinkleRoles.length; k++) {
            long shifted = tick + (long) k * stride;
            int slot = (int) Math.floorDiv(shifted, twinkleSlot);      // low 32 bits: all the hash uses
            if (hash(k, slot, twinkleSalt) % twinkleOneIn != 0) continue;
            int at = (int) Math.floorMod(shifted, (long) twinkleSlot), a = half - Math.abs(at - half), keep = half - a;
            int c = frameRgb[twinkleRoles[k]];
            int r = (((c >> 16) & 255) * keep + ((dim >> 16) & 255) * a + half / 2) / half;
            int g = (((c >> 8) & 255) * keep + ((dim >> 8) & 255) * a + half / 2) / half;
            int b = ((c & 255) * keep + (dim & 255) * a + half / 2) / half;
            frameRgb[twinkleRoles[k]] = (r << 16) | (g << 8) | b;
        }
    }

    /** scene.py's pose_indexes: the frame as palette indexes in idx, with pose (-1: no dog), and its colours in frameRgb. */
    private void indexes(int year, int month, int day, int hour, int minute, int weather, long tick, int state, int pose) {
        datePalette(year, month, day);
        frameColours(state, tick, year, month, day, hour);
        java.util.Arrays.fill(idx, (byte) 0);
        Part[] parts = pose < 0 ? NO_PARTS : pose == poses.length ? doorParts : poses[pose];
        for (Part p : parts) partAt(p, tick);
        boolean clearNight = state == NIGHT && weather != CLEAR;
        for (int o = 0; o < order.length; o++) {
            if (clearNight && clearNightOnly[o]) continue;
            if (slotOfOrder[o] >= 0) {
                specials(slotOfOrder[o], year, month, day, hour, weather, state, tick);
                continue;
            }
            String name = order[o];
            switch (name) {
                case "sky":
                    whole(stateSky[state], 0, 0);
                    break;
                case "sea":
                    whole(stateSea[state], 0, 0);
                    break;
                case "sand":
                    whole(stateSand[state], 0, 0);
                    break;
                case "sun":
                    if (stateSun[state] != null) whole(sun, stateSun[state][0] - sunCx, stateSun[state][1] - sunCy);
                    break;
                case "moon":
                case "path_moon": {
                    int k = moonFrame(year, month, day);
                    if (!moonStates[state] || k == 0) break;
                    if (name.equals("path_moon")) whole(fullLayers.get(name), 0, 0);
                    else stamp(moon.index, moon.width, k * moonSize, 0, moonSize, moon.height, moonX - moonCx, moonY - moonCy);
                    break;
                }
                case "clouds": {
                    int size = cloudsGrown[weather] ? 1 : 0;
                    int shown = weather == CLEAR ? cloudsShownClear[month - 1] : cloudsShown[weather];
                    for (int k = 0; k < shown && k < cloudTracks.length; k++) {
                        int[] t = cloudTracks[k];
                        int x = (int) Math.floorMod(t[1] + Math.floorDiv(tick, t[2]), (long) cloudSpan) + cloudLeft;
                        int b = 3 + size * 6;
                        stamp(clouds.index, clouds.width, t[b], t[b + 1], t[b + 2], t[b + 3], x + t[b + 4], t[0] + t[b + 5]);
                    }
                    break;
                }
                case "foam": {
                    int k = (int) Math.floorMod(Math.floorDiv(tick, foamTicks), (long) foamFrames);
                    stamp(foam.index, foam.width, 0, k * foamH, foam.width, foamH, 0, foamTop);
                    break;
                }
                case "ripples": {
                    if (weather != ripplesWeather) break;
                    int k = (int) Math.floorMod(Math.floorDiv(tick, ripplesTicks), (long) ripplesFrames);
                    stamp(ripples.index, ripples.width, 0, k * ripplesH, ripples.width, ripplesH, 0, ripplesTop);
                    break;
                }
                case "beam": {
                    int k = (int) Math.floorMod(Math.floorDiv(tick, beamTicks), (long) beamFrames);
                    stamp(beam.index, beam.width, k * beamW, 0, beamW, beam.height, beamX, beamY);
                    break;
                }
                case "rain_far":
                case "rain_near":
                    if (weather == rainWeather) rain(name.equals("rain_far") ? rainFar : rainNear, name.equals("rain_far") ? rainFarSpeed : rainNearSpeed, tick);
                    break;
                case "dog_shadow": {
                    if (parts.length == 0) break;
                    for (Part p : parts) if (p.flat) stamp(p.frame, p.w, 0, 0, p.w, p.h, dogX + p.atX, dogY + p.atY);
                    System.arraycopy(idx, 0, shadowBase, 0, idx.length);
                    int key = shadowKey(state, clearNight, year, month, day);
                    for (Part p : parts) if (!p.flat) shadow(p, key, month);
                    break;
                }
                case "house_shadow":
                    System.arraycopy(idx, 0, shadowBase, 0, idx.length);
                    shadow(house, shadowKey(state, clearNight, year, month, day), month);
                    break;
                case "dog":
                    for (Part p : parts) if (!p.flat) stamp(p.frame, p.w, 0, 0, p.w, p.h, dogX + p.atX, dogY + p.atY);
                    break;
                case "text":
                    System.arraycopy(idx, 0, textUnder, 0, idx.length);
                    text(year, month, day, hour, minute);
                    break;
                default: {
                    Png full = fullLayers.get(name);
                    if (full == null) throw new IllegalStateException("scene.json names a layer Scene does not know: " + name);
                    whole(full, 0, 0);
                }
            }
        }
    }

    /** scene.py's shadow_key: the state, or NO_MOON in a state that has a moon while none is drawn (nothing casts then). */
    private int shadowKey(int state, boolean clearNight, int year, int month, int day) {
        return moonStates[state] && ((clearNight && moonClearNightOnly) || moonFrame(year, month, day) == 0) ? NO_MOON : state;
    }

    private void whole(Png png, int x, int y) {
        stamp(png.index, png.width, 0, 0, png.width, png.height, x, y);
    }

    /** Puts the (sx, sy, w, h) part of an image with its top-left at (x, y): each pixel whose role is shown replaces what is under it. */
    private void stamp(byte[] img, int imgW, int sx, int sy, int w, int h, int x, int y) {
        stamp(img, imgW, sx, sy, w, h, x, y, 16);
    }

    /** stamp through a dither: of 16 levels, a pixel shows when the number of its place on the screen (BAYER, 4 x 4) is under level. */
    private void stamp(byte[] img, int imgW, int sx, int sy, int w, int h, int x, int y, int level) {
        int x0 = Math.max(x, 0), y0 = Math.max(y, 0), x1 = Math.min(x + w, W), y1 = Math.min(y + h, H);
        for (int yy = y0; yy < y1; yy++) {
            int src = (sy + yy - y) * imgW + sx - x, dst = yy * W;
            for (int xx = x0; xx < x1; xx++) {
                int v = img[src + xx] & 255;
                if (frameShown[v] && (level >= 16 || BAYER[((yy & 3) << 2) | (xx & 3)] < level)) idx[dst + xx] = (byte) v;
            }
        }
    }

    /** A rain tile moved down by speed * tick and left by a lean's share of that, wrapping both ways. */
    private void rain(Png tile, int speed, long tick) {
        long down = speed * tick, left = Math.floorDiv(down, rainLean);
        for (int y = 0; y < H; y++) {
            int ty = (int) Math.floorMod(y - down, (long) rainTileH) * rainTileW;
            int tx = (int) Math.floorMod(left, (long) rainTileW);
            for (int x = 0; x < W; x++) {
                int v = tile.index[ty + tx] & 255;
                if (frameShown[v]) idx[y * W + x] = (byte) v;
                if (++tx == rainTileW) tx = 0;
            }
        }
    }

    // ------------------------------------------------------------------------------------------- the poses

    /** The pose index of a name in scene.json, -1 for null or a name it does not hold. */
    public int pose(String name) {
        if (name != null) for (int k = 0; k < poseNames.length; k++) if (poseNames[k].equals(name)) return k;
        if (name != null && name.equals(doorName)) return poses.length;      // the dog in the doghouse's doorway
        return -1;
    }

    /** scene.py's chosen_poses for the schedule at a time: poseAt, with the doghouse. The pose of a slot he spends in
     *  the house (inHouse) is the doorway's, index poseCount(); a change between two such slots is no change. */
    void placeAt(int[] out, int year, int month, int day, int hour, int minute, int second, int micros, long tick) {
        poseAt(tick, out);
        if (doorParts == null || out[1] < 0) return;
        long s = Math.floorDiv(tick, poseHold);
        if (inHouse(tick < changeStart(s) ? s - 1 : s, year, month, day, hour, minute, second, micros, tick)) out[1] = poses.length;
        if (out[0] >= 0 && inHouse(s - 1, year, month, day, hour, minute, second, micros, tick)) out[0] = poses.length;
        if (out[0] == out[1]) {
            out[0] = -1;
            out[2] = -1;
        }
    }

    /** scene.py's in_house: true when the dog spends pose slot s in the doghouse: when at one of stayLook minutes after
     *  the slot's first tick it rains, or when at one of them it is night and hash(s, 2, salt) % out_one_in is not 0.
     *  The slot's first tick is s * hold; its minute is the frame's time moved by the ticks from that tick to the
     *  frame's (floor), counted from the midnight of the frame's day. */
    private boolean inHouse(long s, int year, int month, int day, int hour, int minute, int second, int micros, long tick) {
        long us = ((hour * 60L + minute) * 60 + second) * 1_000_000L + micros;
        long first = Math.floorDiv(us - (tick - s * poseHold) * (1_000_000 / ticksPerSecond), 60_000_000L);
        LocalDateTime midnight = LocalDateTime.of(year, month, day, 0, 0);
        boolean night = false;
        for (int look : stayLook) {
            LocalDateTime t = midnight.plusMinutes(first + look);
            int w = weatherName(t.getYear(), t.getMonthValue(), t.getDayOfMonth(), t.getHour(), t.getMinute());
            if (w == RAIN) return true;
            night = night || chooseState(t.getYear(), t.getMonthValue(), t.getDayOfMonth(), t.getHour(), t.getMinute(), w) == NIGHT;
        }
        return night && hash((int) s, 2, staySalt) % stayOutOneIn != 0;   // low 32 bits: all the hash uses
    }

    /** The number of poses in scene.json. */
    int poseCount() {
        return poses.length;
    }

    /** scene.py's pose_at: out gets old, new and step for this tick; old and step are -1 unless a change is fading. In
     *  slot s = tick div hold, slot s - 1's pose shows until changeStart(s); for fade_ticks ticks from there the step is
     *  (tick - start) * steps / fade_ticks. With one pose: (-1, 0, -1); with none, new is -1 too. */
    void poseAt(long tick, int[] out) {
        int n = poses.length;
        out[0] = -1;
        out[2] = -1;
        if (n <= 1) {
            out[1] = n - 1;
            return;
        }
        long s = Math.floorDiv(tick, poseHold), start = changeStart(s);
        if (tick < start) {
            out[1] = poseOfSlot(s - 1);
        } else if (tick - start < poseFadeTicks) {
            out[0] = poseOfSlot(s - 1);
            out[1] = poseOfSlot(s);
            out[2] = (int) ((tick - start) * fadeSteps / poseFadeTicks);
        } else {
            out[1] = poseOfSlot(s);
        }
    }

    /** scene.py's change_start: the tick at which the change of pose in slot s starts. */
    private long changeStart(long s) {
        return s * poseHold + hash((int) s, 1, poseSalt) % poseJitter;   // low 32 bits: all the hash uses
    }

    /** scene.py's pose_of_slot, for two poses or more. With two the poses alternate: s mod 2 (slot -1 gives 1); the
     *  block rule below would change a two-place block's last place and could show a pose twice in a row. With three
     *  or more: place s mod n of block s div n, whose first two places swap when its first pose is the last of the
     *  block before (no pose twice in a row). */
    private int poseOfSlot(long s) {
        int n = poses.length;
        if (n == 2) return (int) Math.floorMod(s, 2L);
        long b = Math.floorDiv(s, n);
        shuffled(b, poseOrderSalt, orderNow);
        shuffled(b - 1, poseOrderSalt, orderBefore);
        if (orderNow[0] == orderBefore[n - 1]) {
            int k = orderNow[0];
            orderNow[0] = orderNow[1];
            orderNow[1] = k;
        }
        return orderNow[(int) Math.floorMod(s, (long) n)];
    }

    /** scene.py's shuffled: block b's order of the poses, or pass b's of the quotes, before the fix at its start. */
    private static void shuffled(long b, int salt, int[] order) {
        for (int i = 0; i < order.length; i++) order[i] = i;
        for (int i = order.length - 1; i > 0; i--) {
            int j = hash(i, (int) b, salt) % (i + 1), k = order[i];   // low 32 bits of b: all the hash uses
            order[i] = order[j];
            order[j] = k;
        }
    }

    // ------------------------------------------------------------------------------------------- the dog

    /** scene.py's dog_frame: the part's image with every movement that is happening applied, in order, into p.frame. */
    private void partAt(Part p, long tick) {
        System.arraycopy(p.still, 0, p.frame, 0, p.frame.length);
        for (Move m : p.moves) {
            int k = moveFrame(m, tick);
            if (k >= 0) apply(p, m.frames[k]);
        }
    }

    /** Which frame of a movement shows at this tick, or -1 while it is not happening. */
    static int moveFrame(Move m, long tick) {
        long start, at;
        if (m.regular) {
            start = 0;
            at = Math.floorMod(tick, (long) m.period);
        } else {
            int slot = (int) Math.floorDiv(tick, m.slot);   // low 32 bits: all the hash uses
            at = Math.floorMod(tick, (long) m.slot);
            if (hash(slot, 0, m.salt) % m.b >= m.a) return -1;
            start = hash(slot, 1, m.salt) % m.spread;
        }
        if (at < start || at >= start + m.length) return -1;
        return (int) ((at - start) / m.ticksPerFrame % m.frames.length);
    }

    private void apply(Part p, int[] ops) {
        int i = 0;
        while (i < ops.length) {
            int kind = ops[i++];
            if (kind == OP_RECOLOUR) {
                int to = ops[i++], n = ops[i++];
                for (int c = 0; c < n; c++, i += 2) p.frame[ops[i + 1] * p.w + ops[i]] = (byte) to;
            } else if (kind == OP_SHIFT) {
                movePixels(p, ops[i], ops[i + 1], ops[i + 2], ops[i + 3], ops[i + 4], ops[i + 5], ops[i + 6]);
                i += 7;
            } else {
                int x = ops[i], y = ops[i + 1], w = ops[i + 2], n = ops[i + 4];
                for (int k = 0; k < n; k++) movePixels(p, x, y + k, w, 1, ops[i + 5 + k], 0, 0);
                i += 5 + n;
            }
        }
    }

    /** The opaque pixels inside the rect move by (dx, dy); where they were becomes fill; where they land is replaced. */
    private void movePixels(Part p, int x, int y, int w, int h, int dx, int dy, int fill) {
        byte[] f = p.frame;
        int pw = p.w, ph = p.h;
        int x0 = Math.max(x, 0), y0 = Math.max(y, 0), x1 = Math.min(x + w, pw), y1 = Math.min(y + h, ph);
        for (int yy = y0; yy < y1; yy++) {
            for (int xx = x0; xx < x1; xx++) {
                moveScratch[yy * pw + xx] = f[yy * pw + xx];
                if (f[yy * pw + xx] != 0) f[yy * pw + xx] = (byte) fill;
            }
        }
        for (int yy = y0; yy < y1; yy++) {
            for (int xx = x0; xx < x1; xx++) {
                byte v = moveScratch[yy * pw + xx];
                int nx = xx + dx, ny = yy + dy;
                if (v != 0 && nx >= 0 && nx < pw && ny >= 0 && ny < ph) f[ny * pw + nx] = v;
            }
        }
    }

    /** scene.py's cast_shadow, for one part placed at (x, y) = (dogX + atX, dogY + atY): each opaque pixel (col, row)
     *  of its frame at h = max(0, ground[col] - row) casts onto column x + col + h * ax / bx, rows top .. top + thick - 1
     *  with top = y + ground[col] + h * ay / by (floor division; [ax, bx, ay, by] = the lean of key, a state or NO_MOON). A
     *  frame pixel it lands on takes the shadow target of what it held before any shadow was laid (shadowBase), unless
     *  that is 0. A pixel in a column without ground casts nothing. */
    private void shadow(Part p, int key, int month) {
        int[] lean = key == DAY ? shadowDay[month - 1] : shadowLean[key];      // scene.py's shadow_lean
        int thick = shadowThick[key], x = dogX + p.atX, y = dogY + p.atY;
        for (int row = 0; row < p.h; row++) {
            for (int col = 0; col < p.w; col++) {
                int g = p.ground[col];
                if (p.frame[row * p.w + col] == 0 || g < 0) continue;
                int h = Math.max(0, g - row);
                int sx = x + col + Math.floorDiv(h * lean[0], lean[1]);
                if (sx < 0 || sx >= W) continue;
                int top = y + g + Math.floorDiv(h * lean[2], lean[3]);
                for (int k = 0; k < thick; k++) {
                    int sy = top + k;
                    if (sy < 0 || sy >= H) continue;
                    int at = sy * W + sx;
                    byte t = shadowTarget[shadowBase[at] & 255];
                    if (t != 0) idx[at] = t;
                }
            }
        }
    }

    // ------------------------------------------------------------------------------------------- the words

    /** scene.py's text_pieces: the clock, AM or PM and the date on the left; the quote on the right, its first line at the
     *  top margin, right-aligned. Every glyph is stamped first as edge, then as ink. */
    private void text(int year, int month, int day, int hour, int minute) {
        int quoteHour = fixedQuoteHour >= 0 ? fixedQuoteHour : hour;
        long key = ((year * 100L + month) * 100 + day) * 100 + quoteHour;
        if (key != textKey) {
            textKey = key;
            int iso = (int) Math.floorMod(julianDay(year, month, day), 7L) + 1;   // 1 = Monday .. 7 = Sunday
            textDate = DAYS[iso % 7] + " " + day + " " + MONTHS[month - 1];
            textQuote = wrap(quoteOf(year, month, day, quoteHour), quoteChars);
        }
        glyphs = 0;
        int x = marginX, y = marginY, h12 = hour % 12 == 0 ? 12 : hour % 12;
        if (h12 >= 10) x = figure(1, x, y);
        x = figure(h12 % 10, x, y);
        figure(10, x, y);       // the colon is always lit: it does not blink
        x += 6;
        x = figure(minute / 10, x, y);
        x = figure(minute % 10, x, y);
        words(hour < 12 ? "AM" : "PM", x + 1, y + 12);
        words(textDate, marginX, y + 26);
        int right = W - marginX;
        for (int k = 0; k < textQuote.size() && k < quoteLines; k++) {
            String s = textQuote.get(k);
            words(s, right - (s.isEmpty() ? 0 : s.length() * advance - 1), y + k * (line + 1));
        }
        for (int pass = 0; pass < 2; pass++) {
            for (int g = 0; g < glyphs; g++) {
                Png sheet = glyphSheet[g] == 0 ? font : digits;
                int x0 = Math.max(glyphX[g], 0), y0 = Math.max(glyphY[g], 0);
                int x1 = Math.min(glyphX[g] + glyphW[g], W), y1 = Math.min(glyphY[g] + sheet.height, H);
                for (int yy = y0; yy < y1; yy++) {
                    for (int xx = x0; xx < x1; xx++) {
                        int v = sheet.index[(yy - glyphY[g]) * sheet.width + glyphSx[g] + xx - glyphX[g]] & 255;
                        int put = pass == 0 ? (v != 0 ? edgeRole : 0) : (v == textRole ? textRole : 0);
                        if (frameShown[put]) idx[yy * W + xx] = (byte) put;
                    }
                }
            }
        }
    }

    /** Places one clock figure (0..9, 10 for the colon) and returns the x of the next. */
    private int figure(int d, int x, int y) {
        int[] c = digitCells[d];
        addGlyph(1, c[0], c[2], x - 1, y - 1);
        return x + (d == 1 || d == 10 ? 6 : 14);
    }

    private void words(String s, int x, int y) {
        for (int k = 0; k < s.length(); k++) {
            int i = fontChars.indexOf(Character.toUpperCase(s.charAt(k)));
            if (i >= 0) addGlyph(0, i * cellW, cellW, x + k * advance - 1, y - 1);
        }
    }

    private void addGlyph(int sheet, int sx, int w, int x, int y) {
        if (glyphs == glyphSheet.length) throw new IllegalStateException("more than " + glyphs + " glyphs on screen");
        glyphSheet[glyphs] = sheet;
        glyphSx[glyphs] = sx;
        glyphW[glyphs] = w;
        glyphX[glyphs] = x;
        glyphY[glyphs++] = y;
    }
}
