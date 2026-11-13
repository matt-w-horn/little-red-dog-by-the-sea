package io.matthorn.littlereddog;

/**
 * The dimming of a finished frame through three tables of 256 entries, one for each channel: the same numbers as
 * (c * factor + 500) / 1000 for every pixel (scene.py's on_screen), without a division for each pixel.
 *
 * The other curves are for the dark-edge test only (SceneView, demo setting `curve`): each gives the frame the same
 * mean as MULTIPLY in every channel, so that a phase differs from another in its contrast and not in its light.
 */
final class Dim {

    static final int MULTIPLY = 0, FLAT = 1, FLOOR = 2, GAMMA = 3;
    static final String[] CURVE_NAMES = {"A MULTIPLY", "B FLAT", "C RAISED BLACK", "D GAMMA"};
    /** FLOOR: the black rises to this share of the channel's mean, in percent. */
    static final int FLOOR_PERCENT = 40;
    /** GAMMA: out = k * c^(GAMMA_EXPONENT), which lifts the dark values and keeps the mean. */
    static final double GAMMA_EXPONENT = 0.6;

    private Dim() {
    }

    /** t[c] = (c * factor + 500) / 1000 for c = 0..255; factor in thousandths, 0..1000. */
    static void table(int factor, int[] t) {
        for (int c = 0; c < 256; c++) t[c] = (c * factor + 500) / 1000;
    }

    /** dst[i] = src[i] with each channel looked up in its table; opaque. */
    static void apply(int[] src, int[] dst, int[] r, int[] g, int[] b) {
        for (int i = 0; i < src.length; i++) {
            int c = src[i];
            dst[i] = 0xFF000000 | (r[(c >> 16) & 255] << 16) | (g[(c >> 8) & 255] << 8) | b[c & 255];
        }
    }

    /** How many pixels of the frame have each value, for each channel: hist[channel * 256 + value], red first. */
    static void histogram(int[] src, long[] hist) {
        java.util.Arrays.fill(hist, 0);
        for (int c : src) {
            hist[(c >> 16) & 255]++;
            hist[256 + ((c >> 8) & 255)]++;
            hist[512 + (c & 255)]++;
        }
    }

    /** One channel's table for a curve, with the same mean over the frame as MULTIPLY at this factor. hist: that
     *  channel's 256 counts. */
    static void curve(int kind, int factor, long[] hist, int offset, int[] t) {
        table(factor, t);
        if (kind == MULTIPLY) return;
        long n = 0;
        double sum = 0, want = 0;
        for (int c = 0; c < 256; c++) {
            n += hist[offset + c];
            sum += (double) c * hist[offset + c];
            want += (double) t[c] * hist[offset + c];
        }
        if (n == 0 || sum == 0) return;
        double mean = want / n;                           // the mean that MULTIPLY gives
        if (kind == FLAT) {
            int v = (int) Math.round(mean);
            for (int c = 0; c < 256; c++) t[c] = v;
        } else if (kind == FLOOR) {
            double floor = mean * FLOOR_PERCENT / 100, slope = (mean - floor) / (sum / n);
            for (int c = 0; c < 256; c++) t[c] = clamp(Math.round(floor + c * slope));
        } else {
            double lifted = 0;
            for (int c = 0; c < 256; c++) lifted += Math.pow(c / 255.0, GAMMA_EXPONENT) * hist[offset + c];
            double k = mean / (lifted / n);
            for (int c = 0; c < 256; c++) t[c] = clamp(Math.round(k * Math.pow(c / 255.0, GAMMA_EXPONENT)));
        }
    }

    private static int clamp(long v) {
        return (int) Math.max(0, Math.min(255, v));
    }
}
