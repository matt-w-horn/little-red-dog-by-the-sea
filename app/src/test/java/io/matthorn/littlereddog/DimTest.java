package io.matthorn.littlereddog;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Random;
import org.junit.Test;

public class DimTest {

    /** The tables give exactly scene.py's on_screen, (c * factor + 500) // 1000, for every factor and value. */
    @Test
    public void tableIsTheFormula() {
        int[] t = new int[256];
        for (int f = 0; f <= 1000; f++) {
            Dim.table(f, t);
            for (int c = 0; c < 256; c++) assertEquals("factor " + f + ", value " + c, (c * f + 500) / 1000, t[c]);
        }
    }

    /** apply looks each channel up in its own table and keeps the pixel opaque. */
    @Test
    public void applyUsesEachChannelsTable() {
        int[] r = new int[256], g = new int[256], b = new int[256];
        Dim.table(1000, r);
        Dim.table(930, g);
        Dim.table(250, b);
        Random rnd = new Random(1);
        int[] src = new int[4096], dst = new int[4096];
        for (int i = 0; i < src.length; i++) src[i] = rnd.nextInt();
        Dim.apply(src, dst, r, g, b);
        for (int i = 0; i < src.length; i++) {
            int c = src[i];
            int want = 0xFF000000 | (((c >> 16) & 255) * 1000 + 500) / 1000 << 16 | (((c >> 8) & 255) * 930 + 500) / 1000 << 8
                    | ((c & 255) * 250 + 500) / 1000;
            assertEquals("pixel " + i, want, dst[i]);
        }
    }

    /** Every curve keeps the mean light of MULTIPLY within one step, never darkens a lighter value below a darker
     *  one, and FLAT is one value; FLOOR and GAMMA lift the black. */
    @Test
    public void curvesKeepTheMean() {
        Random rnd = new Random(2);
        int[] t = new int[256], m = new int[256];
        long[] hist = new long[768];
        int[] frame = new int[Scene.W * Scene.H];
        for (int trial = 0; trial < 20; trial++) {
            int dark = rnd.nextInt(256);
            for (int i = 0; i < frame.length; i++) {          // a night-like frame: mostly dark, a few light pixels
                int v = rnd.nextInt(10) == 0 ? rnd.nextInt(256) : rnd.nextInt(Math.max(1, dark / 3 + 1));
                frame[i] = 0xFF000000 | v << 16 | (v * 7 / 8) << 8 | (v * 3 / 4);
            }
            Dim.histogram(frame, hist);
            for (int f : new int[] {250, 232, 185, 700, 1000}) {
                Dim.table(f, m);
                double want = mean(m, hist, 0);
                for (int kind = Dim.MULTIPLY; kind <= Dim.GAMMA; kind++) {
                    Dim.curve(kind, f, hist, 0, t);
                    String at = "trial " + trial + ", factor " + f + ", curve " + Dim.CURVE_NAMES[kind];
                    assertTrue(at + ": mean " + mean(t, hist, 0) + " not " + want, Math.abs(mean(t, hist, 0) - want) <= 1.0);
                    for (int c = 1; c < 256; c++) assertTrue(at + ": falls at " + c, t[c] >= t[c - 1]);
                    if (kind == Dim.FLAT) assertEquals(at, t[0], t[255]);
                    if ((kind == Dim.FLOOR || kind == Dim.GAMMA) && want >= 2) assertTrue(at + ": black not lifted", t[1] >= m[1]);
                }
            }
        }
    }

    private static double mean(int[] t, long[] hist, int offset) {
        double sum = 0;
        long n = 0;
        for (int c = 0; c < 256; c++) {
            sum += (double) t[c] * hist[offset + c];
            n += hist[offset + c];
        }
        return sum / n;
    }
}
