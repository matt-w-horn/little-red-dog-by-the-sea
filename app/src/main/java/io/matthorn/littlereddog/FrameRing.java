package io.matthorn.littlereddog;

/**
 * The hand-off between the thread that draws frames ahead (the writer) and the thread that puts them on the screen
 * at each vsync (the reader). It holds only the bookkeeping: which slot holds which tick, and in what state. The
 * frames themselves are arrays the caller keeps, one set for each slot.
 *
 * The writer claims a slot for the next tick to draw, at most AHEAD ticks after the tick of now, never one before
 * now: when it falls behind it jumps to now, and counts the ticks it skipped; when the wall clock goes back it starts
 * again at the new now. The reader takes the newest ready tick
 * that is not after now, and never a tick in the future; the slot it shows is never given to the writer. bump() drops
 * every frame drawn before a change of the inputs (the fast mode, a pose); close() ends the ring for good.
 */
final class FrameRing {

    static final int EMPTY = 0, WRITING = 1, READY = 2, SHOWN = 3;

    private final int[] state;
    private final long[] tick;
    private final int[] version;
    private final int ahead;
    private int current;                                  // the version of the inputs
    private long last = Long.MIN_VALUE;                   // the last tick claimed in this version
    private long skipped;
    private boolean closed;

    FrameRing(int slots, int ahead) {
        state = new int[slots];
        tick = new long[slots];
        version = new int[slots];
        this.ahead = ahead;
    }

    /** The writer: a slot to draw the next tick into, or -1 when it is far enough ahead or no slot is free. */
    synchronized int claim(long now) {
        if (closed) return -1;
        if (last != Long.MIN_VALUE && last > now + ahead) {    // the wall clock went back: start again at now
            last = Long.MIN_VALUE;
            for (int i = 0; i < state.length; i++) if (state[i] == READY && tick[i] > now + ahead) state[i] = EMPTY;
        }
        long next = last == Long.MIN_VALUE ? now : Math.max(last + 1, now);
        if (next > now + ahead) return -1;
        int free = -1;
        for (int i = 0; i < state.length && free < 0; i++) if (state[i] == EMPTY) free = i;
        if (free < 0) {                                   // else the oldest frame that is too late to show
            for (int i = 0; i < state.length; i++) {
                if (state[i] == READY && tick[i] < now && (free < 0 || tick[i] < tick[free])) free = i;
            }
        }
        if (free < 0) return -1;
        if (last != Long.MIN_VALUE && next > last + 1) skipped += next - last - 1;
        last = next;
        state[free] = WRITING;
        tick[free] = next;
        version[free] = current;
        return free;
    }

    synchronized long tickOf(int slot) {
        return tick[slot];
    }

    /** The writer has drawn the slot: ready to show, unless the inputs changed or the ring closed meanwhile. */
    synchronized boolean publish(int slot) {
        if (state[slot] != WRITING) return false;
        boolean ok = !closed && version[slot] == current;
        state[slot] = ok ? READY : EMPTY;
        notifyAll();
        return ok;
    }

    /** The reader: the slot to show from now on (the newest ready tick not after now), or -1 to keep what is shown. */
    synchronized int take(long now) {
        int best = -1;
        for (int i = 0; i < state.length; i++) {
            if (state[i] == READY && tick[i] <= now && (best < 0 || tick[i] > tick[best])) best = i;
        }
        if (best < 0) return -1;
        for (int i = 0; i < state.length; i++) {
            if (state[i] == SHOWN || (state[i] == READY && tick[i] < tick[best])) state[i] = EMPTY;
        }
        state[best] = SHOWN;
        notifyAll();
        return best;
    }

    /** The inputs changed: every frame not yet shown is dropped, and the writer starts again at now. */
    synchronized void bump() {
        current++;
        last = Long.MIN_VALUE;
        for (int i = 0; i < state.length; i++) if (state[i] == READY) state[i] = EMPTY;
        notifyAll();
    }

    synchronized void close() {
        closed = true;
        notifyAll();
    }

    synchronized boolean isClosed() {
        return closed;
    }

    /** The writer waits up to ms for a change (a slot taken, a bump, a close). */
    synchronized void await(long ms) throws InterruptedException {
        if (!closed && ms > 0) wait(ms);
    }

    /** Ticks the writer jumped over since the last call. */
    synchronized long takeSkipped() {
        long s = skipped;
        skipped = 0;
        return s;
    }

    synchronized int stateOf(int slot) {
        return state[slot];
    }
}
