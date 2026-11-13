package io.matthorn.littlereddog;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import org.junit.Test;

/**
 * Scene against tools/scene.py: every case of art/reference/manifest.json is drawn and its RGB bytes hashed, and a
 * few answers (quotes, weather, one layer read by Png) are compared with what Python and Pillow give.
 */
public class SceneReferenceTest {

    /** The art folder: the system property art.dir (Gradle sets it from -PartDir=/absolute/path), or ../art, as
     *  Gradle runs unit tests with app/ as the working directory. */
    private static final File ART = new File(System.getProperty("art.dir", "../art"));

    private static Scene scene() throws IOException {
        return new Scene(path -> new FileInputStream(new File(ART, path)));
    }

    @Test
    public void everyReferenceFrameMatches() throws Exception {
        Scene scene = scene();
        @SuppressWarnings("unchecked")
        List<Object> cases = (List<Object>) Json.parse(new String(Files.readAllBytes(new File(ART, "reference/manifest.json").toPath()),
                StandardCharsets.UTF_8));
        int[] px = new int[Scene.W * Scene.H];
        StringBuilder differ = new StringBuilder();
        for (Object o : cases) {
            @SuppressWarnings("unchecked") Map<String, Object> c = (Map<String, Object>) o;
            draw(scene, c, px);
            if (!sha(px).equals(c.get("sha256"))) differ.append(' ').append(c.get("file"));
        }
        System.out.println("everyReferenceFrameMatches: " + cases.size() + " cases drawn from " + ART.getAbsolutePath());
        assertTrue("frames that differ from the reference:" + differ, differ.length() == 0);
        assertTrue("the manifest lists no cases", cases.size() > 0);
    }

    /** Every line of art/reference/pose_schedule.txt, which scene_export.py writes with scene.pose_at when there are two
     *  poses or more: tick, old, new, step (pose names, - for none). */
    @Test
    public void poseScheduleAsInPython() throws Exception {
        File file = new File(ART, "reference/pose_schedule.txt");
        if (!file.exists()) {
            System.out.println("poseScheduleAsInPython: no " + file + " (one pose), nothing compared");
            return;
        }
        Scene s = scene();
        List<String> lines = Files.readAllLines(file.toPath(), StandardCharsets.UTF_8);
        String[] names = lines.get(0).split(" ");
        assertEquals("the header", "poses", names[0]);
        assertEquals("poses in the header and in scene.json", names.length - 1, s.poseCount());
        for (int k = 1; k < names.length; k++) assertEquals("pose " + names[k], k - 1, s.pose(names[k]));
        int[] got = new int[3];
        StringBuilder differ = new StringBuilder();
        for (String line : lines.subList(1, lines.size())) {
            String tick = line.split("\t", 2)[0];
            s.poseAt(Long.parseLong(tick), got);
            String mine = tick + "\t" + (got[0] < 0 ? "-" : names[got[0] + 1]) + "\t" + (got[1] < 0 ? "-" : names[got[1] + 1])
                    + "\t" + (got[2] < 0 ? "-" : String.valueOf(got[2]));
            if (!mine.equals(line)) differ.append("\n  python ").append(line).append("  java ").append(mine);
        }
        System.out.println("poseScheduleAsInPython: " + (lines.size() - 1) + " lines compared");
        assertTrue("lines that differ from the reference:" + differ, differ.length() == 0);
        assertTrue("the schedule lists no ticks", lines.size() > 1);
    }

    /** Scene.wrap against literal text (the quote list does not matter here). */
    @Test
    public void quotesAsWrapped() throws Exception {
        // wrap balances the lines, and cuts a word longer than the width.
        assertEquals(Arrays.asList("Water the plants", "early in the morning,", "before the sun gets", "high enough."),
                Scene.wrap("Water the plants early in the morning, before the sun gets high enough.", 24));
        assertEquals(Arrays.asList("aaaaaaaaaaaaaaaaaaaaaaaa", "aaaaaa b"), Scene.wrap("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa b", 24));
        assertEquals(Arrays.asList("aa bb", "cc dd"), Scene.wrap("aa bb cc dd", 5));
        assertEquals(0, Scene.wrap("", 24).size());
    }

    /** Every hour of art/reference/quotes_wrapped.txt ('YYYY-MM-DD HH<TAB>line|line'), which scene_export.py writes with
     *  scene.quote_of and scene.wrap: the last day before the epoch, the first three passes (3 n hours, n quotes) and
     *  28 February to 1 March 2028. */
    @Test
    public void everyHourOfTheQuoteReferenceWrapsAsInPython() throws Exception {
        Scene s = scene();
        List<String> lines = Files.readAllLines(new File(ART, "reference/quotes_wrapped.txt").toPath(), StandardCharsets.UTF_8);
        int width = Integer.parseInt(lines.get(0).substring("width ".length()));
        StringBuilder differ = new StringBuilder();
        for (String line : lines.subList(1, lines.size())) {
            String[] part = line.split("\t", 2), d = part[0].split("[- ]");
            String got = String.join("|", Scene.wrap(s.quoteOf(Integer.parseInt(d[0]), Integer.parseInt(d[1]), Integer.parseInt(d[2]),
                    Integer.parseInt(d[3])), width));
            if (!got.equals(part[1])) differ.append(' ').append(part[0].replace(' ', 'T'));
        }
        long n = Files.readAllLines(new File(ART, "quotes.txt").toPath(), StandardCharsets.UTF_8).stream()
                .filter(q -> !q.trim().isEmpty()).count();
        System.out.println("everyHourOfTheQuoteReferenceWrapsAsInPython: " + (lines.size() - 1) + " hours compared, " + n + " quotes");
        assertEquals("hours in the reference", 24 + 3 * n + 72, lines.size() - 1);
        assertTrue("hours whose quote wraps differently:" + differ, differ.length() == 0);
    }

    /** Every line of art/reference/specials_days.txt ('YYYY-MM-DD<TAB>name name ...', - for none), which scene_export.py
     *  writes with scene.special_on: for every day of ten years, the items of scene.json's specials whose date rule
     *  holds (fixed dates, the n-th weekday of a month, Easter). */
    @Test
    public void specialsOfEveryDayAsInPython() throws Exception {
        Scene s = scene();
        List<String> lines = Files.readAllLines(new File(ART, "reference/specials_days.txt").toPath(), StandardCharsets.UTF_8);
        StringBuilder differ = new StringBuilder();
        int wrong = 0, withItems = 0;
        for (String line : lines) {
            String[] part = line.split("\t", 2), d = part[0].split("-");
            String got = s.specialsOn(Integer.parseInt(d[0]), Integer.parseInt(d[1]), Integer.parseInt(d[2]));
            if (!got.equals("-")) withItems++;
            if (!got.equals(part[1]) && wrong++ < 8) differ.append("\n  ").append(line).append("  java ").append(got);
        }
        System.out.println("specialsOfEveryDayAsInPython: " + lines.size() + " days compared, " + withItems + " with an item");
        assertTrue(wrong + " days whose specials differ from the reference:" + differ, wrong == 0);
        assertTrue("the reference lists fewer than ten years", lines.size() >= 3652);
        assertTrue("no day of the reference has an item", withItems > 0);
    }

    /** The surprises' timetables, day lotteries and the shooting star by the millisecond, as scene_export.py writes
     *  them with scene.window_start, scene.day_key and scene.meteor_pixels (art/reference/surprise_windows.txt,
     *  surprise_days.txt, meteors.txt). */
    @Test
    public void surprisesAsInPython() throws Exception {
        Scene s = scene();
        StringBuilder differ = new StringBuilder();
        int wrong = 0, windows = 0, hits = 0, lit = 0;
        List<String> lines = Files.readAllLines(new File(ART, "reference/surprise_windows.txt").toPath(), StandardCharsets.UTF_8);
        for (String line : lines) {
            String[] part = line.split("\t");
            long start = s.surpriseWindow(part[0], Long.parseLong(part[1]));
            if (start >= 0) windows++;
            if (!(start < 0 ? "-" : String.valueOf(start)).equals(part[2]) && wrong++ < 8) differ.append("\n  ").append(line).append("  java ").append(start);
        }
        List<String> days = Files.readAllLines(new File(ART, "reference/surprise_days.txt").toPath(), StandardCharsets.UTF_8);
        for (String line : days) {
            String[] part = line.split("\t"), d = part[1].split("-");
            boolean hit = s.surpriseLottery(part[0], Integer.parseInt(d[0]), Integer.parseInt(d[1]), Integer.parseInt(d[2]), Integer.parseInt(part[2]));
            if (hit) hits++;
            if (hit != part[3].equals("1") && wrong++ < 8) differ.append("\n  ").append(line).append("  java ").append(hit);
        }
        List<String> stars = Files.readAllLines(new File(ART, "reference/meteors.txt").toPath(), StandardCharsets.UTF_8);
        for (String line : stars) {
            String[] part = line.split("\t");
            String got = s.meteorPixels(Long.parseLong(part[0]), Integer.parseInt(part[1]));
            if (!got.equals("-")) lit++;
            if (!got.equals(part[2]) && wrong++ < 8) differ.append("\n  ").append(line).append("  java ").append(got);
        }
        System.out.println("surprisesAsInPython: " + lines.size() + " slots (" + windows + " with a window), " + days.size()
                + " lottery days (" + hits + " hits), " + stars.size() + " milliseconds of shooting stars (" + lit + " lit)");
        assertTrue(wrong + " lines that differ from the reference:" + differ, wrong == 0);
        assertTrue("a reference file is empty or shows nothing", windows > 0 && hits > 0 && lit > 0);
    }

    /** Every line of art/reference/day_states.txt ('YYYY-MM-DD HH:MM<TAB>weather<TAB>state'), which scene_export.py
     *  writes with scene.weather_name and scene.choose_state: the sun times by month, summer time, the weather's odds
     *  by month and the morning cloud. */
    @Test
    public void weatherAndStateOfEveryDayAsInPython() throws Exception {
        Scene s = scene();
        List<String> lines = Files.readAllLines(new File(ART, "reference/day_states.txt").toPath(), StandardCharsets.UTF_8);
        StringBuilder differ = new StringBuilder();
        int wrong = 0;
        int[] seenWeather = new int[3], seenState = new int[6];
        for (String line : lines) {
            String[] part = line.split("\t"), d = part[0].split("[- :]");
            int y = Integer.parseInt(d[0]), mo = Integer.parseInt(d[1]), da = Integer.parseInt(d[2]);
            int h = Integer.parseInt(d[3]), mi = Integer.parseInt(d[4]);
            int w = s.weatherName(y, mo, da, h, mi), st = s.chooseState(y, mo, da, h, mi, w);
            seenWeather[w]++;
            seenState[st]++;
            if (w != Scene.weather(part[1]) || st != Scene.state(part[2])) {
                if (wrong++ < 8) differ.append(' ').append(part[0].replace(' ', 'T'));
            }
        }
        System.out.println("weatherAndStateOfEveryDayAsInPython: " + lines.size() + " lines compared; weather "
                + Arrays.toString(seenWeather) + ", states " + Arrays.toString(seenState));
        assertEquals("lines in the reference", (365 + 60) * 24, lines.size());
        for (int n : seenWeather) assertTrue("a weather never came up", n > 0);
        for (int n : seenState) assertTrue("a state never came up", n > 0);
        assertTrue(wrong + " lines differ from the reference, the first:" + differ, wrong == 0);
    }

    /** Every line of art/reference/dog_places.txt, which scene_export.py writes with scene.chosen_poses at a time: epoch
     *  milliseconds, old, new, step, where the doorway's pose stands for a slot the dog spends in the doghouse. */
    @Test
    public void dogPlacesAsInPython() throws Exception {
        File file = new File(ART, "reference/dog_places.txt");
        Scene s = scene();
        assertTrue("no " + file + ": scene.json has no pose in the doghouse's doorway", file.exists());
        List<String> lines = Files.readAllLines(file.toPath(), StandardCharsets.UTF_8);
        String door = lines.get(0).split(" ")[1];
        assertEquals("the doorway's pose comes after the poses of the schedule", s.poseCount(), s.pose(door));
        List<String> names = poseNames();
        assertEquals("poses in scene.json and in Scene", names.size(), s.poseCount());
        int[] got = new int[3];
        int inHouse = 0, outAtNight = 0, fadesWithHouse = 0;
        StringBuilder differ = new StringBuilder();
        for (String line : lines.subList(1, lines.size())) {
            long ms = Long.parseLong(line.split("\t", 2)[0]);
            java.time.ZonedDateTime t = java.time.Instant.ofEpochMilli(ms).atZone(HOME);
            s.placeAt(got, t.getYear(), t.getMonthValue(), t.getDayOfMonth(), t.getHour(), t.getMinute(), t.getSecond(),
                    t.getNano() / 1000, Math.floorDiv(ms * s.ticksPerSecond, 1000L));
            String mine = ms + "\t" + (got[0] < 0 ? "-" : name(names, got[0], door)) + "\t" + name(names, got[1], door)
                    + "\t" + (got[2] < 0 ? "-" : String.valueOf(got[2]));
            if (!mine.equals(line)) differ.append("\n  python ").append(line).append("  java ").append(mine);
            boolean night = s.chooseState(t.getYear(), t.getMonthValue(), t.getDayOfMonth(), t.getHour(), t.getMinute(),
                    s.weatherName(t.getYear(), t.getMonthValue(), t.getDayOfMonth(), t.getHour(), t.getMinute())) == Scene.NIGHT;
            if (got[1] == s.poseCount()) inHouse++;
            else if (night && got[0] < 0) outAtNight++;
            if (got[0] >= 0 && (got[0] == s.poseCount() || got[1] == s.poseCount())) fadesWithHouse++;
        }
        System.out.println("dogPlacesAsInPython: " + (lines.size() - 1) + " lines compared; in the house in " + inHouse
                + ", out at night in " + outAtNight + ", in a fade into or out of the house in " + fadesWithHouse);
        assertTrue("lines that differ from the reference:" + (differ.length() > 4000 ? differ.substring(0, 4000) : differ), differ.length() == 0);
        assertTrue("too few lines in the house: " + inHouse, inHouse > 1000);
        assertTrue("never out at night", outAtNight > 20);
        assertTrue("no fade into or out of the house", fadesWithHouse > 20);
    }

    /** The name of a pose index: scene.json's own (dog.poses, in order), or the doorway's after them. */
    private static String name(List<String> names, int pose, String door) {
        return pose >= 0 && pose < names.size() ? names.get(pose) : pose == names.size() ? door : "?" + pose;
    }

    @SuppressWarnings("unchecked")
    private static List<String> poseNames() throws IOException {
        Map<String, Object> sc = (Map<String, Object>) Json.parse(new String(Files.readAllBytes(new File(ART, "scene.json").toPath()),
                StandardCharsets.UTF_8));
        List<String> names = new java.util.ArrayList<>();
        for (Object p : (List<Object>) ((Map<String, Object>) sc.get("dog")).get("poses")) names.add((String) ((Map<String, Object>) p).get("name"));
        return names;
    }

    private static final java.time.ZoneId HOME = java.time.ZoneId.of("America/Los_Angeles");

    private static void renderAt(Scene s, int[] out, long ms) {
        java.time.ZonedDateTime t = java.time.Instant.ofEpochMilli(ms).atZone(HOME);
        s.renderNow(out, t.getYear(), t.getMonthValue(), t.getDayOfMonth(), t.getHour(), t.getMinute(), t.getSecond(),
                t.getNano() / 1_000_000, ms, -1);
    }

    private static long msAt(int y, int mo, int d, int h, int mi, int sec) {
        return java.time.ZonedDateTime.of(y, mo, d, h, mi, sec, 0, HOME).toInstant().toEpochMilli();
    }

    /** A frame depends on its tick alone: renderNow at the first and the last millisecond of a tick gives the same
     *  pixels, in a change of light, a change of weather, a change of pose and across midnight. The view draws each
     *  tick ahead at its first millisecond and rests on this. */
    @Test
    public void aFrameIsTheSameAllThroughItsTick() throws Exception {
        Scene s = scene();
        int tps = s.ticksPerSecond, tickMs = 1000 / tps;
        assertEquals("a tick is a whole number of milliseconds", 1000, tickMs * tps);
        java.util.List<Long> ticks = new java.util.ArrayList<>();
        int[][] days = {{2026, 1, 15}, {2026, 3, 8}, {2026, 6, 21}, {2026, 11, 1}, {2026, 11, 10}, {2026, 12, 31}};
        int changes = 0;
        for (int[] d : days) {
            int beforeState = -1, beforeWeather = -1;
            for (int m = 0; m < 1440; m++) {
                int w = s.weatherName(d[0], d[1], d[2], m / 60, m % 60), st = s.chooseState(d[0], d[1], d[2], m / 60, m % 60, w);
                if (beforeState >= 0 && (st != beforeState || w != beforeWeather)) {
                    long start = msAt(d[0], d[1], d[2], m / 60, m % 60, 0) / tickMs;
                    for (long k : new long[] {-1, 0, 1, 5, 31, 63, 64, 65}) ticks.add(start + k);
                    long light = 5L * 60 * tps;               // a change of light takes 5 minutes, before or after the boundary
                    for (long k : new long[] {-light - 1, -light, -light + 1, -light / 2, light / 2, light - 1, light, light + 1}) ticks.add(start + k);
                    changes++;
                }
                beforeState = st;
                beforeWeather = w;
            }
        }
        int[] chosen = new int[3];
        long from = msAt(2026, 11, 10, 20, 0, 0) / tickMs, poseFades = 0;
        for (long t = from; t < from + 4L * 3600 * tps && poseFades < 12; t++) {
            s.poseAt(t, chosen);
            if (chosen[0] >= 0) {
                ticks.add(t);
                poseFades++;
            }
        }
        long midnight = msAt(2027, 1, 1, 0, 0, 0) / tickMs;
        for (long k = -2; k <= 2; k++) ticks.add(midnight + k);
        int[] a = new int[Scene.W * Scene.H], b = new int[Scene.W * Scene.H];
        for (long t : ticks) {
            renderAt(s, a, t * tickMs);
            renderAt(s, b, t * tickMs + tickMs - 1);
            assertArrayEquals("tick " + t + " (" + java.time.Instant.ofEpochMilli(t * tickMs).atZone(HOME) + ")", a, b);
        }
        System.out.println("aFrameIsTheSameAllThroughItsTick: " + ticks.size() + " ticks, " + changes + " changes of light or weather, "
                + poseFades + " ticks in pose fades");
        assertTrue("too few changes found: " + changes, changes >= 12);
        assertTrue("no pose fade found", poseFades > 0);
    }

    /** The shooting star the view draws from a slot's snapshot is the one Scene.meteor gives over the frame drawn last:
     *  forced by the demo, and on a clear night with no demo, every 7 ms over two hours. */
    @Test
    public void shootingStarFromASnapshot() throws Exception {
        Scene s = scene();
        int[] frame = new int[Scene.W * Scene.H], a = new int[3 * Scene.METEOR_PIXELS], b = new int[3 * Scene.METEOR_PIXELS];
        int[] px = new int[3 * Scene.METEOR_PIXELS], levels = new int[s.meteorLevelCount()];
        byte[] idx = new byte[Scene.W * Scene.H];
        int pixels = 0, moments = 0;
        for (int round = 0; round < 2; round++) {
            long start = msAt(2026, 11, 10, 23, 0, 0);
            s.setDemo(round == 0 ? "shooting_star" : null, start * s.ticksPerSecond / 1000);
            renderAt(s, frame, start);
            assertEquals("a clear night", Scene.NIGHT, s.lastState());
            s.meteorSnapshot(idx, levels);
            long span = round == 0 ? 60_000 : 2 * 3600_000;
            for (long ms = start; ms < start + span; ms += 7) {
                int n = s.meteor(ms, a);
                int m = s.meteorOver(ms, idx, levels, s.lastState(), s.lastWeather(), s.lastMonth(), s.lastDay(), s.starDemo(), px, b);
                assertEquals("pixels at " + ms, n, m);
                for (int k = 0; k < 3 * n; k++) assertEquals("at " + ms, a[k], b[k]);
                pixels += n;
                moments++;
            }
        }
        System.out.println("shootingStarFromASnapshot: " + moments + " moments, " + pixels + " star pixels");
        assertTrue("no star was drawn", pixels > 1000);
    }

    /** The brightness rule over 2026 and 2027, every minute: settled, it stays between the night's and the day's level
     *  and moves at most a ramp's step a minute (midnight included); after a start or a key it is full for the hold,
     *  then falls to the settled level and never rises; warmth only lowers green and blue. */
    @Test
    @SuppressWarnings("unchecked")
    public void brightnessKeepsItsRules() throws Exception {
        Scene s = scene();
        Map<String, Object> scene = (Map<String, Object>) Json.parse(new String(Files.readAllBytes(new File(ART, "scene.json").toPath()),
                StandardCharsets.UTF_8));
        Map<String, Object> e = (Map<String, Object>) scene.get("evening");
        int day = 10 * ((Long) e.get("day")).intValue(), evening = 10 * ((Long) e.get("evening")).intValue();
        int night = 10 * ((Long) e.get("night")).intValue();
        long hold = 60_000L * (Long) e.get("hold_minutes"), fade = 60_000L * (Long) e.get("fade_minutes");
        // The most a minute can move: the ramps' slopes added, as the one after sunset can overlap the one at night_from.
        int step = (Math.max(day, evening) - night) / ((Long) e.get("night_ramp")).intValue()
                + (day - night) / ((Long) e.get("dawn_ramp")).intValue()
                + Math.abs(day - evening) / ((Long) e.get("warm_after_sunset")).intValue() + 3;
        int[] f = new int[3];
        int before = -1, low = 1000, high = 0, checked = 0;
        for (java.time.LocalDate d = java.time.LocalDate.of(2026, 1, 1); d.getYear() < 2028; d = d.plusDays(1)) {
            for (int m = 0; m < 1440; m++) {
                int b = s.settledBrightness(d.getYear(), d.getMonthValue(), d.getDayOfMonth(), m / 60, m % 60, 0);
                assertTrue(d + " " + m + ": settled " + b, b >= night && b <= Math.max(day, evening));
                if (before >= 0) assertTrue(d + " " + m + ": a jump from " + before + " to " + b, Math.abs(b - before) <= step);
                before = b;
                low = Math.min(low, b);
                high = Math.max(high, b);
                s.eveningFactors(d.getYear(), d.getMonthValue(), d.getDayOfMonth(), m / 60, m % 60, 0, Scene.SETTLED, f);
                assertTrue(d + " " + m + ": warmth raised a colour", f[0] == b && f[1] <= f[0] && f[2] <= f[1]);
                if (m % 60 == 0) {                        // the fade after a start, each hour
                    int last = 1000;
                    for (long ms = -60_000; ms <= hold + fade + 60_000; ms += 1000) {
                        s.eveningFactors(d.getYear(), d.getMonthValue(), d.getDayOfMonth(), m / 60, m % 60, 0, ms, f);
                        if (ms <= hold) assertEquals(d + " " + m + " " + ms + " ms: not full in the hold", 1000, f[0]);
                        if (ms >= hold + fade) assertEquals(d + " " + m + " " + ms + " ms: not settled after the fade", b, f[0]);
                        assertTrue(d + " " + m + " " + ms + " ms: rose in the fade", f[0] <= last && f[0] >= b);
                        last = f[0];
                        checked++;
                    }
                }
            }
        }
        System.out.println("brightnessKeepsItsRules: settled from " + low + " to " + high + "; " + checked + " moments of fades");
        assertEquals("the night's level is never reached", night, low);
        assertEquals("the day's level is never reached", Math.max(day, evening), high);
    }

    /** Every line of art/reference/evening.txt ('YYYY-MM-DD HH:MM:SS<TAB>D<TAB>red green blue', D the milliseconds since
     *  the screensaver started or '-' for settled), which scene_export.py writes with scene.evening_factors: the
     *  dimming and the warmth. */
    @Test
    public void eveningFactorsAsInPython() throws Exception {
        Scene s = scene();
        List<String> lines = Files.readAllLines(new File(ART, "reference/evening.txt").toPath(), StandardCharsets.UTF_8);
        int[] got = new int[3];
        int wrong = 0, dimmed = 0, warmed = 0;
        StringBuilder differ = new StringBuilder();
        for (String line : lines) {
            String[] part = line.split("\t"), d = part[0].split("[- :]"), want = part[2].split(" ");
            s.eveningFactors(Integer.parseInt(d[0]), Integer.parseInt(d[1]), Integer.parseInt(d[2]), Integer.parseInt(d[3]),
                    Integer.parseInt(d[4]), Integer.parseInt(d[5]), part[1].equals("-") ? Scene.SETTLED : Long.parseLong(part[1]), got);
            if (got[0] < 1000) dimmed++;
            if (got[2] < got[0]) warmed++;
            if (got[0] != Integer.parseInt(want[0]) || got[1] != Integer.parseInt(want[1]) || got[2] != Integer.parseInt(want[2])) {
                if (wrong++ < 8) differ.append(' ').append(part[0].replace(' ', 'T')).append('/').append(part[1]);
            }
        }
        System.out.println("eveningFactorsAsInPython: " + lines.size() + " lines compared; dimmed in " + dimmed + ", warmed in " + warmed);
        assertTrue("lines in the reference: " + lines.size(), lines.size() > 6 * 144 * 6);
        assertTrue("no minute is dimmed, or none is warmed", dimmed > 100 && warmed > 100);
        assertTrue(wrong + " lines differ from the reference, the first:" + differ, wrong == 0);
    }

    /** layers/clouds.png as Pillow reads it: art/reference/layer_counts.txt holds its size and, for each index, how many
     *  pixels have it (scene_export.py writes it with numpy.unique). */
    @Test
    public void pngReadsALayerAsPillowDoes() throws Exception {
        List<String> lines = Files.readAllLines(new File(ART, "reference/layer_counts.txt").toPath(), StandardCharsets.UTF_8);
        String[] head = lines.get(0).split(" ");
        Png png = Png.read(new FileInputStream(new File(ART, "layers/" + head[0])), "layers/" + head[0]);
        assertEquals(Integer.parseInt(head[1]), png.width);
        assertEquals(Integer.parseInt(head[2]), png.height);
        int[] count = new int[256], want = new int[256];
        for (byte b : png.index) count[b & 255]++;
        for (String line : lines.subList(1, lines.size())) want[Integer.parseInt(line.split(" ")[0])] = Integer.parseInt(line.split(" ")[1]);
        assertTrue("the reference lists fewer than three indexes", lines.size() > 3);
        assertArrayEquals(want, count);
    }

    private static void draw(Scene scene, Map<String, Object> c, int[] px) {
        String[] d = ((String) c.get("date")).split("-"), t = ((String) c.get("time")).split("[:.]");
        int y = Integer.parseInt(d[0]), mo = Integer.parseInt(d[1]), da = Integer.parseInt(d[2]);
        int h = Integer.parseInt(t[0]), mi = Integer.parseInt(t[1]), s = Integer.parseInt(t[2]), us = Integer.parseInt(t[3]);
        if ("render_now".equals(c.get("via"))) {
            scene.renderNow(px, y, mo, da, h, mi, s, us / 1000, (Long) c.get("epoch_ms"), -1);
            return;
        }
        Object w = c.get("weather");
        int old, now, step;
        if (w instanceof String) {
            old = now = Scene.weather((String) w);
            step = -1;
        } else {
            List<?> l = (List<?>) w;
            old = Scene.weather((String) l.get(0));
            now = Scene.weather((String) l.get(1));
            step = ((Long) l.get(2)).intValue();
        }
        int state = c.get("state") == null ? -1 : Scene.state((String) c.get("state"));
        String name = (String) c.get("pose");
        int pose = scene.pose(name);
        if (name != null && pose < 0) throw new AssertionError(c.get("file") + ": scene.json has no pose " + name);
        scene.render(px, y, mo, da, h, mi, s, us, old, now, step, (Long) c.get("frame_number"), state, pose);
    }

    private static String sha(int[] px) throws Exception {
        byte[] rgb = new byte[px.length * 3];
        for (int i = 0; i < px.length; i++) {
            rgb[3 * i] = (byte) (px[i] >> 16);
            rgb[3 * i + 1] = (byte) (px[i] >> 8);
            rgb[3 * i + 2] = (byte) px[i];
        }
        StringBuilder out = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(rgb)) out.append(String.format("%02x", b));
        return out.toString();
    }
}
