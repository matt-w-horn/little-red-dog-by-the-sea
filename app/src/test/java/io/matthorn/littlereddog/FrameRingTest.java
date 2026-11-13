package io.matthorn.littlereddog;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.concurrent.atomic.AtomicReference;
import org.junit.Test;

public class FrameRingTest {

    @Test
    public void writerStaysAheadButNotTooFar() {
        FrameRing r = new FrameRing(4, 2);
        for (long want = 10; want <= 12; want++) {
            int i = r.claim(10);
            assertTrue("a slot for " + want, i >= 0);
            assertEquals(want, r.tickOf(i));
            assertTrue(r.publish(i));
        }
        assertEquals("three ahead is too far", -1, r.claim(10));
        int shown = r.take(10);
        assertEquals(10, r.tickOf(shown));
        assertEquals("the reader never takes a future tick", -1, r.take(10));
        int next = r.claim(11);
        assertEquals("after a tick, the next one", 13, r.tickOf(next));
        assertTrue("the shown slot is never given out", next != shown);
    }

    @Test
    public void behindWriterJumpsToNowAndCountsSkips() {
        FrameRing r = new FrameRing(4, 2);
        r.publish(r.claim(5));
        int i = r.claim(9);
        assertEquals(9, r.tickOf(i));
        assertEquals(3, r.takeSkipped());
        r.publish(i);
        assertEquals("the newest ready tick not after now", 9, r.tickOf(r.take(9)));
    }

    @Test
    public void bumpDropsFramesAndCloseStopsPublishing() {
        FrameRing r = new FrameRing(4, 2);
        r.publish(r.claim(0));
        int drawing = r.claim(0);
        r.bump();
        assertEquals("ready frames of the old inputs are dropped", -1, r.take(5));
        assertFalse("a frame drawn for the old inputs is not published", r.publish(drawing));
        int i = r.claim(0);
        assertEquals("the writer starts again at now", 0, r.tickOf(i));
        r.close();
        assertFalse(r.publish(i));
        assertEquals(-1, r.claim(0));
    }

    /** The wall clock set back: the writer starts again at the new now instead of waiting for the clock to catch up,
     *  and frames drawn for the later ticks give their slots back. */
    @Test
    public void clockSetBack() {
        FrameRing r = new FrameRing(4, 2);
        for (int k = 0; k < 3; k++) r.publish(r.claim(100));
        r.take(100);
        int i = r.claim(50);
        assertTrue("a slot after the clock went back", i >= 0);
        assertEquals(50, r.tickOf(i));
        r.publish(i);
        assertEquals(50, r.tickOf(r.take(50)));
        for (int k = 0; k < 2; k++) assertTrue("the slots of ticks 101 and 102 came back", r.claim(50) >= 0);
    }

    @Test
    public void slotsNeverFillUp() {
        FrameRing r = new FrameRing(4, 2);
        for (long now = 0; now < 1000; now++) {
            int i;
            while ((i = r.claim(now)) >= 0) r.publish(i);
            int shown = r.take(now);
            assertTrue("tick " + now + " is ready when due", shown >= 0 && r.tickOf(shown) == now);
        }
    }

    /** A writer and a reader on their own threads with a clock that moves on: every slot the reader takes holds the
     *  tick the ring says, never a future one, and a slot is never written while it is shown. */
    @Test
    public void underStress() throws Exception {
        FrameRing r = new FrameRing(4, 2);
        long[] payload = new long[4];                           // what the writer wrote into each slot
        long t0 = System.nanoTime();
        java.util.function.LongSupplier clock = () -> (System.nanoTime() - t0) / 1_000_000;   // a tick a millisecond
        AtomicReference<String> error = new AtomicReference<>();
        Thread writer = new Thread(() -> {
            try {
                while (!r.isClosed()) {
                    int i = r.claim(clock.getAsLong());
                    if (i < 0) {
                        r.await(1);
                        continue;
                    }
                    long t = r.tickOf(i);
                    if (r.stateOf(i) != FrameRing.WRITING) error.compareAndSet(null, "slot " + i + " not WRITING while written");
                    payload[i] = -1;
                    Thread.yield();
                    payload[i] = t;
                    if (t % 97 == 0) Thread.sleep(3);           // a slow frame now and then
                    r.publish(i);
                    if (t % 211 == 0) r.bump();                 // a change of the inputs now and then
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });
        writer.start();
        long shownTick = Long.MIN_VALUE;
        int taken = 0;
        int shown = -1;
        while (clock.getAsLong() < 3000) {
            long now = clock.getAsLong();
            int i = r.take(now);
            if (i >= 0) {
                shown = i;
                long t = r.tickOf(i);
                if (t > now) error.compareAndSet(null, "took future tick " + t + " at " + now);
                if (t < shownTick) error.compareAndSet(null, "went back from " + shownTick + " to " + t);
                shownTick = t;
                taken++;
            }
            if (shown >= 0) {
                long p = payload[shown];
                if (p != r.tickOf(shown) || r.stateOf(shown) != FrameRing.SHOWN) {
                    error.compareAndSet(null, "slot " + shown + " changed while shown: payload " + p);
                }
            }
        }
        r.close();
        writer.join(5000);
        assertEquals(null, error.get());
        assertTrue("frames were taken: " + taken, taken > 50);   // that the loop ran; how many depends on the machine's load
    }
}
