package io.matthorn.littlereddog;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.view.Choreographer;
import android.view.SurfaceHolder;
import android.view.SurfaceView;

import java.io.IOException;
import java.util.Calendar;

/**
 * Puts the beach on the screen. The picture itself comes from {@link Scene}, which draws the art files of the art
 * folder (packaged under assets/art) exactly as tools/scene.py does. The 480x270 art changes on a tick, eight times a
 * second, and is drawn enlarged by a whole number with no filtering, so each art pixel is a square block of screen
 * pixels and nothing ever sits between two of them.
 *
 * Two threads. The drawing thread ("beach-draw") owns the Scene: it loads the art, draws each tick up to AHEAD ticks
 * before it is due into a ring of SLOTS frames (FrameRing), and reads the demo setting. The
 * screen thread ("beach") is called on every vsync (60 a second): when a new tick is due it takes that tick's frame
 * from the ring, dims and warms it through three tables (Dim, Scene.eveningFactors) and puts it on the screen. A
 * frame takes about 22 ms to draw on a TV, longer than a vsync; drawn ahead on its own thread, it no longer
 * holds up the screen. The dimming is done when the frame is put up, so a key brightens the picture at once.
 *
 * One thing moves between ticks: a shooting star. Scene.meteorOver names its pixels for the millisecond over the frame
 * shown (each slot keeps that frame's indexes), and the frame is put up again on every vsync with those pixels over
 * it, each a whole art pixel, so the star crosses the sky in steps of a sixtieth of a second.
 *
 * For looking at one surprise without waiting, the global setting littlereddog_demo names it (Scene.setDemo); it is read
 * every two seconds: `settings put global littlereddog_demo aurora`, and `settings delete global littlereddog_demo` to end.
 */
public class SceneView extends SurfaceView implements Choreographer.FrameCallback, SurfaceHolder.Callback {

    private static final String TAG = "LittleRedDog";
    private static final int STATS_EVERY = 3600;
    /** The ring: SLOTS frames, drawn at most AHEAD ticks before they are due (a lead covers a stall, not overload). */
    private static final int SLOTS = 4, AHEAD = 2;
    /**
     * The hidden fast mode, paced for showing it to someone: it starts ten minutes before dawn, and a day and a night
     * pass in about 40 seconds. The clock runs FAST_TWILIGHT times as fast through dawn and dusk (about 8 seconds
     * each), FAST_DAY times through the day (about 14 seconds) and FAST_NIGHT times through the night (about 9). A
     * change of light or weather fades in over FAST_FADE_TICKS ticks, in FADE_STEPS steps as Scene's own fades do.
     */
    private static final int FAST_TWILIGHT = 720, FAST_DAY = 2400, FAST_NIGHT = 4320, FAST_FADE_TICKS = 8, FADE_STEPS = 32;

    /** One frame of the ring and what the screen thread needs to show it, all written by the drawing thread. */
    private static final class Slot {
        final int[] frame = new int[Scene.W * Scene.H];   // finished, not yet dimmed
        final byte[] idx = new byte[Scene.W * Scene.H];   // its indexes, for the shooting star
        final int[] starLevels;
        int state, weather, starMonth, starDay, textColour;
        boolean starForced, star;                         // star: false in the fast mode
        // for the dimming: the moment shown, whether it shows the level the hour settles at, the brightness test
        int year, month, day, hour, minute, second, bright, curve;
        boolean settled;

        Slot(int levels) {
            starLevels = new int[levels];
        }
    }

    private final Bitmap bitmap = Bitmap.createBitmap(Scene.W, Scene.H, Bitmap.Config.ARGB_8888);
    private final Paint paint = new Paint();
    private final Rect dst = new Rect();

    private volatile Scene scene;
    private final Object life = new Object();
    private final Object sceneLock = new Object();             // held for each frame drawn: one drawing thread at a time
    private final Object screenLock = new Object();            // held for each vsync: one screen thread at a time
    private int generation;                                    // guarded by life: which start is the current one
    private volatile boolean running;
    private HandlerThread screen;
    private volatile Looper looper;                            // the screen thread's looper while the view runs
    private volatile FrameRing ring;
    private Slot[] slots;                                      // the ring's frames, made for each start

    // For screenshots and checks: a fixed minute of the day, date, weather and lighting state. -1 or 0: the real one.
    private volatile int fixedMinute = -1, fixedWeather = -1, fixedState = -1;
    private volatile int fixedYear, fixedMonth, fixedDay;
    /** For screenshots: a pose of scene.json to show instead of the schedule; null, or a name it does not hold, for the schedule. */
    private volatile String pose;
    /** When the view started or a key was last pressed, on the clock that a change of the wall clock does not move:
     *  the brightness is full then (Scene.eveningFactors). */
    private volatile long awakeSince = SystemClock.elapsedRealtime();
    /** 0 while the fast mode is off, else the millisecond it was switched on. */
    private volatile long fastSince;

    // ------------------------------------------------------------------ the drawing thread's own (see Slot for the rest)
    private final Calendar now = Calendar.getInstance();
    private final int[] fadeFrom = new int[Scene.W * Scene.H];
    private long fastSeen, fadeStart, fastClock, fastClockAt;
    private int toState, toWeather, fromState, fromWeather;
    private String demoSeen;
    private int bright, curve;                                 // the brightness and curve tests: 0 off, -1 cycling, else held
    private long brightSince;

    /**
     * The brightness test, for choosing how dark the night should be: the demo setting `bright` cycles the picture
     * through BRIGHT_LEVELS (percent), BRIGHT_MS each, in the night's full warmth, with the level written over the
     * sky; `bright35` holds 35 %. The curve test, for the dark edges of the panel: `curve` cycles the Dim curves at
     * CURVE_PERCENT, BRIGHT_MS each, every one with the same mean light; `curve2` holds the third (C). The panel's
     * backlight cannot be set by an app: a darker picture is what dims it.
     */
    private static final int[] BRIGHT_LEVELS = {100, 75, 60, 50, 40, 35, 30, 25, 20, 15, 10};
    private static final int BRIGHT_MS = 10_000, CURVE_PERCENT = 25, W_HALF = Scene.W / 2;

    /** The brightness test the demo name asks for: 0 for none, -1 for the cycle, else a percent from 1 to 100. */
    static int brightness(String name) {
        int k = test(name, "bright", 1, 100);
        return k == -2 ? 0 : k;
    }

    /** The curve test the demo name asks for: 0 for none, -1 for the cycle, else the curve's number + 1. */
    static int curveTest(String name) {
        int k = test(name, "curve", 0, Dim.CURVE_NAMES.length - 1);
        return k == -2 ? 0 : k == -1 ? -1 : k + 1;
    }

    /** -2: the name is not this test; -1: the cycle; else the number after the word, held to low..high. */
    private static int test(String name, String word, int low, int high) {
        if (name == null || !name.startsWith(word)) return -2;
        String rest = name.substring(word.length());
        if (rest.isEmpty()) return -1;
        try {
            return Math.max(low, Math.min(high, Integer.parseInt(rest)));
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    // ------------------------------------------------------------------ the screen thread's own
    private Slot shown;
    private final int[] dimmed = new int[Scene.W * Scene.H];
    private final int[] evening = new int[3], tableFactors = {-1, -1, -1};
    private final int[] tableR = new int[256], tableG = new int[256], tableB = new int[256];
    private final long[] hist = new long[768];
    private int tableCurve = -1;
    private final int[] meteor = new int[3 * Scene.METEOR_PIXELS], meteorPx = new int[3 * Scene.METEOR_PIXELS];
    private final Paint dot = new Paint();
    private final Paint label = new Paint();
    private final android.graphics.Path labelPath = new android.graphics.Path();
    private String labelText;
    private boolean meteorShown, bitmapStale;
    private long lastTick = Long.MIN_VALUE, shownTick = Long.MIN_VALUE;
    // the screen thread's figures, logged every STATS_EVERY vsyncs
    private int vsyncs, shownFrames, missed, loggedWidth;
    private long statsStartNs, lateNs, worstLateNs, presentNs, worstPresentNs;

    public SceneView(Context context) {
        super(context);
        paint.setFilterBitmap(false);
        paint.setAntiAlias(false);
        paint.setDither(false);
        label.setTextAlign(Paint.Align.CENTER);
        label.setTypeface(android.graphics.Typeface.create(android.graphics.Typeface.MONOSPACE, android.graphics.Typeface.BOLD));
        label.setAntiAlias(true);
        getHolder().addCallback(this);
    }

    /**
     * The surface keeps the size the television gives its apps (1920x1080 on a 4K TV, whose panel is 3840x2160),
     * and the television doubles it. A surface of the panel's own size (holder.setFixedSize(3840, 2160)) was tried on
     * 2026-11-10 so that an art pixel would be exactly 8 by 8 panel pixels: the television showed a black screen,
     * although a screenshot taken over ADB showed the picture. Do not judge this by a screenshot.
     */
    @Override
    public void surfaceCreated(SurfaceHolder holder) {
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        bitmapStale = true;
    }

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
    }

    public void start() {
        synchronized (life) {
            if (running) return;
            running = true;
            awakeSince = SystemClock.elapsedRealtime();
            int gen = ++generation;
            FrameRing r = new FrameRing(SLOTS, AHEAD);
            ring = r;
            screen = new HandlerThread("beach");
            screen.start();
            looper = screen.getLooper();
            Handler h = new Handler(looper);
            new Thread(() -> drawing(gen, r, h), "beach-draw").start();
        }
    }

    /** A key was pressed: the picture goes back to full brightness, and dims again after the hold. */
    public void interacted() {
        awakeSince = SystemClock.elapsedRealtime();
    }

    public void stop() {
        synchronized (life) {
            running = false;
            generation++;
            if (ring != null) ring.close();
            if (screen != null) screen.quitSafely();
            screen = null;
            looper = null;
        }
    }

    private boolean current(int gen) {
        synchronized (life) {
            return running && gen == generation;
        }
    }

    public void setFixedMinute(int minute) {
        fixedMinute = Math.floorMod(minute, 1440);
        inputsChanged();
    }

    public void setFixedDate(int year, int month, int dayOfMonth) {
        fixedYear = year;
        fixedMonth = month;
        fixedDay = dayOfMonth;
        inputsChanged();
    }

    /** 0 clear, 1 cloudy, 2 rain. */
    public void setFixedWeather(int weather) {
        fixedWeather = Math.max(0, Math.min(2, weather));
        inputsChanged();
    }

    /** 0 dawn, 1 day, 2 dusk, 3 night, 4 cloudy, 5 rain. */
    public void setFixedState(int state) {
        fixedState = Math.max(0, Math.min(5, state));
        inputsChanged();
    }

    /** A pose of scene.json by name, shown instead of the schedule; null or an unknown name keeps the schedule. */
    public void setPose(String name) {
        pose = name;
        inputsChanged();
    }

    /** Switches the hidden fast mode on or off: the clock and the sky run through a day in about 40 seconds. */
    public void setFast(boolean on) {
        fastSince = on ? System.currentTimeMillis() : 0;
        inputsChanged();
    }

    public boolean isFast() {
        return fastSince != 0;
    }

    /** The frames drawn ahead were drawn for the inputs before: drop them. */
    private void inputsChanged() {
        FrameRing r = ring;
        if (r != null) r.bump();
    }

    // ================================================================== the drawing thread

    private void drawing(int gen, FrameRing r, Handler screenHandler) {
        Scene s = scene;
        if (s == null) {
            try {
                long t0 = System.nanoTime();
                s = new Scene(path -> getContext().getAssets().open("art/" + path));
                Log.i(TAG, "art loaded in " + (System.nanoTime() - t0) / 1_000_000 + " ms");
            } catch (IOException | RuntimeException e) {
                Log.e(TAG, "the art did not load", e);
                return;
            }
        }
        Slot[] ss;
        synchronized (life) {
            if (scene == null) scene = s;                      // a scene a frame may be drawing is never swapped
            s = scene;
            if (!running || gen != generation) return;         // a stop came while the art loaded
            ss = new Slot[SLOTS];
            for (int i = 0; i < SLOTS; i++) ss[i] = new Slot(s.meteorLevelCount());
            slots = ss;
        }
        screenHandler.post(() -> {
            statsStartNs = System.nanoTime();
            shown = null;
            lastTick = shownTick = Long.MIN_VALUE;
            Choreographer.getInstance().postFrameCallback(this);
        });
        synchronized (sceneLock) {
            fastClockAt = System.currentTimeMillis();          // the fast clock goes on from here, not by the pause
        }
        int tps = s.ticksPerSecond, drawn = 0;
        long statsAt = SystemClock.elapsedRealtime(), drawNs = 0, worstDrawNs = 0;
        try {
            while (current(gen)) {
                long ms = System.currentTimeMillis(), nowTick = Math.floorDiv(ms * tps, 1000);
                int i = r.claim(nowTick);
                if (i < 0) {                                   // far enough ahead: wait for the next tick, or a change
                    r.await(Math.max(1, Math.floorDiv((nowTick + 1) * 1000 + tps - 1, tps) - ms));
                    continue;
                }
                long tick = r.tickOf(i), t0 = System.nanoTime();
                synchronized (sceneLock) {
                    if (!current(gen)) break;
                    draw(s, ss[i], Math.floorDiv(tick * 1000 + tps - 1, tps), tick);   // the tick's first millisecond
                }
                long took = System.nanoTime() - t0;
                drawNs += took;
                worstDrawNs = Math.max(worstDrawNs, took);
                drawn++;
                r.publish(i);
                if (SystemClock.elapsedRealtime() - statsAt >= 60_000) {
                    Log.i(TAG, String.format("drawing: %d frames, %.2f ms each, worst %.1f ms, %d ticks skipped",
                            drawn, drawNs / 1e6 / Math.max(1, drawn), worstDrawNs / 1e6, r.takeSkipped()));
                    statsAt = SystemClock.elapsedRealtime();
                    drawn = 0;
                    drawNs = worstDrawNs = 0;
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    /**
     * The fast mode's clock at this real moment, in milliseconds. When the mode has just been switched on it is set
     * to ten minutes before today's dawn; after that it moves on from where it was, at the speed of the light being
     * shown.
     */
    private long fastTime(Scene s, long ms, long since) {
        if (fastSeen != since) {
            fastSeen = since;
            now.setTimeInMillis(ms);
            now.set(Calendar.HOUR_OF_DAY, 0);
            now.set(Calendar.MINUTE, 0);
            now.set(Calendar.SECOND, 0);
            now.set(Calendar.MILLISECOND, 0);
            int month = now.get(Calendar.MONTH) + 1, dawn = 0;
            while (dawn < 1439 && s.chooseState(now.get(Calendar.YEAR), month, now.get(Calendar.DAY_OF_MONTH), dawn / 60, dawn % 60, Scene.CLEAR) == Scene.NIGHT) dawn++;
            fastClock = now.getTimeInMillis() + (dawn - 10) * 60_000L;
            toState = Scene.NIGHT;
            toWeather = s.weatherName(now.get(Calendar.YEAR), month, now.get(Calendar.DAY_OF_MONTH), dawn / 60, dawn % 60);
            fadeStart = Long.MIN_VALUE / 2;
        } else {
            int speed = toState == Scene.NIGHT ? FAST_NIGHT : toState == Scene.DAWN || toState == Scene.DUSK ? FAST_TWILIGHT : FAST_DAY;
            fastClock += Math.max(0, ms - fastClockAt) * speed;
        }
        fastClockAt = ms;
        return fastClock;
    }

    /**
     * The fast mode's frame. The time of day is the hurried one; the waves, the clouds and the dog keep their own
     * pace, because the tick is the real one. Scene's own fades last 5 minutes (the light) and 8 seconds (the weather) of
     * the clock, which pass here in moments and at a state the hurried clock gives by force, so a change of light or
     * weather is faded in here instead, over one real second.
     */
    private void drawFast(Scene s, int[] frame, int year, int month, int day, int hour, int minute, long tick, int pose) {
        int weather = s.weatherName(year, month, day, hour, minute);
        int state = s.chooseState(year, month, day, hour, minute, weather);
        if (state != toState || weather != toWeather) {
            fromState = toState;
            fromWeather = toWeather;
            toState = state;
            toWeather = weather;
            fadeStart = tick;
        }
        long into = tick - fadeStart;
        if (into >= 0 && into < FAST_FADE_TICKS) {               // the old one first, so the last frame drawn is the new one
            s.render(fadeFrom, year, month, day, hour, minute, 30, 0, fromWeather, fromWeather, -1, tick, fromState, pose);
        }
        s.render(frame, year, month, day, hour, minute, 30, 0, toWeather, toWeather, -1, tick, toState, pose);
        if (into < 0 || into >= FAST_FADE_TICKS) return;
        int step = (int) (into * FADE_STEPS / FAST_FADE_TICKS), keep = FADE_STEPS - step, half = FADE_STEPS / 2;
        for (int i = 0; i < frame.length; i++) {
            int a = fadeFrom[i], b = frame[i];
            int r = (((a >> 16) & 255) * keep + ((b >> 16) & 255) * step + half) / FADE_STEPS;
            int g = (((a >> 8) & 255) * keep + ((b >> 8) & 255) * step + half) / FADE_STEPS;
            int bl = ((a & 255) * keep + (b & 255) * step + half) / FADE_STEPS;
            frame[i] = 0xFF000000 | (r << 16) | (g << 8) | bl;
        }
    }

    /** Draws the tick that begins at ms into the slot, with what the screen thread needs to show it. */
    private void draw(Scene s, Slot slot, long ms, long tick) {
        long fast = fastSince;
        now.setTimeInMillis(fast == 0 ? ms : fastTime(s, ms, fast));
        if (fixedYear > 0 && fast == 0) now.set(fixedYear, fixedMonth - 1, fixedDay);
        int year = now.get(Calendar.YEAR), month = now.get(Calendar.MONTH) + 1, day = now.get(Calendar.DAY_OF_MONTH);
        int poseIndex = s.pose(pose);
        if (tick % (2L * s.ticksPerSecond) == 0) {             // the demo setting, every two seconds
            String name = null;
            try {
                name = android.provider.Settings.Global.getString(getContext().getContentResolver(), "littlereddog_demo");
            } catch (RuntimeException e) {
                Log.w(TAG, "littlereddog_demo cannot be read", e);
            }
            if (name != null && name.isEmpty()) name = null;
            if (name == null ? demoSeen != null : !name.equals(demoSeen)) {
                demoSeen = name;
                bright = brightness(name);
                curve = curveTest(name);
                brightSince = ms;
                s.setDemo(bright == 0 && curve == 0 ? name : null, tick);
                Log.i(TAG, "demo: " + name);
            }
        }
        // The minute shown: the fixed one for a fixed picture, so that its dimming and warmth are that minute's.
        boolean fixed = fast == 0 && (fixedMinute >= 0 || fixedWeather >= 0 || fixedState >= 0);
        int hourNow = now.get(Calendar.HOUR_OF_DAY), minuteNow = now.get(Calendar.MINUTE);
        if (fixed && fixedMinute >= 0) {
            hourNow = fixedMinute / 60;
            minuteNow = fixedMinute % 60;
        }
        // An hourly quote would change every couple of seconds in the fast mode: there it is hour 12's, all day.
        s.setFixedQuoteHour(fast != 0 ? 12 : -1);
        if (fast != 0) {
            drawFast(s, slot.frame, year, month, day, now.get(Calendar.HOUR_OF_DAY), now.get(Calendar.MINUTE), tick, poseIndex);
        } else if (!fixed) {
            s.renderNow(slot.frame, year, month, day, now.get(Calendar.HOUR_OF_DAY), now.get(Calendar.MINUTE),
                    now.get(Calendar.SECOND), now.get(Calendar.MILLISECOND), ms, poseIndex);
        } else {
            // A fixed picture: the given minute (half a minute in, clear of any fade), weather and state.
            int minute = hourNow * 60 + minuteNow;
            int weather = fixedWeather >= 0 ? fixedWeather : Scene.CLEAR;
            s.render(slot.frame, year, month, day, minute / 60, minute % 60, 30, 0, weather, weather, -1, tick, fixedState, poseIndex);
        }
        s.meteorSnapshot(slot.idx, slot.starLevels);
        slot.state = s.lastState();
        slot.weather = s.lastWeather();
        slot.starMonth = s.lastMonth();
        slot.starDay = s.lastDay();
        slot.starForced = s.starDemo();
        slot.star = fast == 0;
        slot.textColour = s.textColour();
        slot.year = year;
        slot.month = month;
        slot.day = day;
        slot.hour = hourNow;
        slot.minute = minuteNow;
        boolean settled = fixed || fast != 0;
        slot.second = settled ? 30 : now.get(Calendar.SECOND);
        slot.settled = settled;
        slot.bright = 0;
        slot.curve = -1;
        if (fast == 0 && bright != 0) {
            // floorDiv and floorMod: ms is before brightSince when the wall clock was set back
            slot.bright = bright > 0 ? bright : BRIGHT_LEVELS[(int) Math.floorMod(Math.floorDiv(ms - brightSince, (long) BRIGHT_MS), (long) BRIGHT_LEVELS.length)];
        } else if (fast == 0 && curve != 0) {
            slot.bright = CURVE_PERCENT;
            slot.curve = curve > 0 ? curve - 1 : (int) Math.floorMod(Math.floorDiv(ms - brightSince, (long) BRIGHT_MS), (long) Dim.CURVE_NAMES.length);
        }
    }

    // ================================================================== the screen thread

    @Override
    public void doFrame(long vsyncNs) {
        // One frame at a time: an old screen thread already inside a frame when a stop and a start come finishes it
        // before the new one goes on, and then sees that it is no longer the current one.
        synchronized (screenLock) {
            if (!running || Looper.myLooper() != looper) return;
            frameNow(vsyncNs);
        }
    }

    private void frameNow(long vsyncNs) {
        long late = System.nanoTime() - vsyncNs;
        Choreographer.getInstance().postFrameCallback(this);
        FrameRing r = ring;
        Scene s = scene;
        Slot[] ss = slots;
        if (r == null || s == null || ss == null) return;
        vsyncs++;
        lateNs += late;
        worstLateNs = Math.max(worstLateNs, late);
        long ms = System.currentTimeMillis(), tick = Math.floorDiv(ms * s.ticksPerSecond, 1000);
        if (shownTick != tick) {                                // until this tick's frame is up, look on every vsync
            int i = r.take(tick);
            if (i >= 0) {
                shown = ss[i];
                shownTick = r.tickOf(i);
                bitmapStale = true;
                shownFrames++;
            }
        }
        if (tick != lastTick) {
            if (lastTick != Long.MIN_VALUE && shownTick < lastTick) missed++;   // that tick never came up in time
            lastTick = tick;
        }
        if (shown != null) {
            long t0 = System.nanoTime();
            if (show(s, shown, ms)) {
                long took = System.nanoTime() - t0;
                presentNs += took;
                worstPresentNs = Math.max(worstPresentNs, took);
            }
        }
        if (vsyncs >= STATS_EVERY) {
            long span = vsyncNs - statsStartNs;
            Runtime rt = Runtime.getRuntime();
            Log.i(TAG, String.format("screen: vsync %.1f/s, frames %.1f/s, %d late ticks, callback late %.2f ms (worst %.1f), "
                            + "put up %.2f ms (worst %.1f), heap %d KB, surface %d wide",
                    vsyncs * 1e9 / span, shownFrames * 1e9 / span, missed, lateNs / 1e6 / vsyncs, worstLateNs / 1e6,
                    presentNs / 1e6 / Math.max(1, shownFrames), worstPresentNs / 1e6,
                    (rt.totalMemory() - rt.freeMemory()) / 1024, loggedWidth));
            statsStartNs = vsyncNs;
            vsyncs = shownFrames = missed = 0;
            lateNs = worstLateNs = presentNs = worstPresentNs = 0;
        }
    }

    /** Dims the slot's frame if it or the factors changed, and puts it up when anything on the screen changed; true when
     *  it was put up. */
    private boolean show(Scene s, Slot slot, long ms) {
        // The dimming and warmth (Scene.eveningFactors), in whole numbers so that the screen holds exactly what
        // tools/scene.py's on_screen gives: full brightness when the view starts or a key is pressed, then, after a
        // hold, down to the level of the hour. A fixed picture and the fast mode show the level the hour settles at.
        if (slot.bright > 0) s.nightFactors(slot.bright, evening);
        else s.eveningFactors(slot.year, slot.month, slot.day, slot.hour, slot.minute, slot.second,
                slot.settled ? Scene.SETTLED : SystemClock.elapsedRealtime() - awakeSince, evening);
        boolean changed = bitmapStale;
        if (evening[0] != tableFactors[0] || evening[1] != tableFactors[1] || evening[2] != tableFactors[2]
                || slot.curve != tableCurve || (slot.curve > Dim.MULTIPLY && bitmapStale)) {
            if (slot.curve > Dim.MULTIPLY) {
                Dim.histogram(slot.frame, hist);
                Dim.curve(slot.curve, evening[0], hist, 0, tableR);
                Dim.curve(slot.curve, evening[1], hist, 256, tableG);
                Dim.curve(slot.curve, evening[2], hist, 512, tableB);
            } else {
                Dim.table(evening[0], tableR);
                Dim.table(evening[1], tableG);
                Dim.table(evening[2], tableB);
            }
            System.arraycopy(evening, 0, tableFactors, 0, 3);
            tableCurve = slot.curve;
            changed = true;
        }
        if (changed) {
            Dim.apply(slot.frame, dimmed, tableR, tableG, tableB);
            bitmap.setPixels(dimmed, 0, Scene.W, 0, 0, Scene.W, Scene.H);
            bitmapStale = false;
            labelText = slot.curve >= 0 ? "CURVE " + Dim.CURVE_NAMES[slot.curve] : slot.bright > 0 ? "BRIGHTNESS " + slot.bright + "%" : null;
        }
        int n = slot.star ? s.meteorOver(ms, slot.idx, slot.starLevels, slot.state, slot.weather, slot.starMonth,
                slot.starDay, slot.starForced, meteorPx, meteor) : 0;
        if (!changed && n == 0 && !meteorShown) return false;
        return present(n, slot.textColour);
    }

    /** Puts the dimmed frame on the screen, with the first n pixels of the shooting star (x, y, colour each) over it,
     *  dimmed and warmed through the same tables; false when there was no surface to draw on. */
    private boolean present(int n, int textColour) {
        SurfaceHolder holder = getHolder();
        if (!holder.getSurface().isValid()) {
            bitmapStale = true;
            return false;
        }
        Canvas canvas = holder.lockHardwareCanvas();
        if (canvas == null) {                                  // tried again on the next vsync
            bitmapStale = true;
            return false;
        }
        try {
            // A whole number of surface pixels for each art pixel: 4 on a 1920x1080 surface.
            int scale = Math.max(1, Math.min(canvas.getWidth() / Scene.W, canvas.getHeight() / Scene.H));
            int w = Scene.W * scale, h = Scene.H * scale;
            int left = (canvas.getWidth() - w) / 2, top = (canvas.getHeight() - h) / 2;
            dst.set(left, top, left + w, top + h);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(bitmap, null, dst, paint);
            for (int j = 0; j < n; j++) {
                int c = meteor[3 * j + 2], x = left + meteor[3 * j] * scale, y = top + meteor[3 * j + 1] * scale;
                dot.setColor(0xFF000000 | (tableR[(c >> 16) & 255] << 16) | (tableG[(c >> 8) & 255] << 8) | tableB[c & 255]);
                canvas.drawRect(x, y, x + scale, y + scale, dot);
            }
            if (labelText != null) {                           // a test's label: the clock's colour, dimmed by the factors
                int c = textColour;                            // (not by a curve's tables: FLAT would hide it)
                label.setColor(0xFF000000 | ((((c >> 16) & 255) * tableFactors[0] + 500) / 1000 << 16)
                        | ((((c >> 8) & 255) * tableFactors[1] + 500) / 1000 << 8) | (((c & 255) * tableFactors[2] + 500) / 1000));
                label.setTextSize(12 * scale);
                // As a path, not as text: some TVs have high-contrast text on, which draws all text white with a
                // black outline whatever its colour.
                label.getTextPath(labelText, 0, labelText.length(), left + W_HALF * scale, top + 30 * scale, labelPath);
                canvas.drawPath(labelPath, label);
            }
            loggedWidth = canvas.getWidth();
        } finally {
            holder.unlockCanvasAndPost(canvas);
        }
        meteorShown = n > 0;
        return true;
    }
}
