package io.matthorn.littlereddog;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.zip.DataFormatException;
import java.util.zip.Inflater;

/**
 * A palette PNG read into its indexes. Only what the art uses: colour type 3 (palette), bit depth 8, not interlaced.
 * The palette and transparency chunks are skipped: the colours live in the palette files, and index 0 is transparent.
 */
public final class Png {

    public final int width, height;
    /** One index per pixel, row by row, width * height bytes. */
    public final byte[] index;

    private Png(int width, int height, byte[] index) {
        this.width = width;
        this.height = height;
        this.index = index;
    }

    /** @param name the file's name, for the error message */
    public static Png read(InputStream in, String name) throws IOException {
        byte[] b = readAll(in);
        byte[] sig = {(byte) 137, 80, 78, 71, 13, 10, 26, 10};
        for (int k = 0; k < 8; k++) if (b.length < 8 || b[k] != sig[k]) throw new IOException(name + ": not a PNG");
        int w = 0, h = 0;
        ByteArrayOutputStream idat = new ByteArrayOutputStream();
        int at = 8;
        while (at + 8 <= b.length) {
            int n = int32(b, at);
            String type = new String(b, at + 4, 4, "US-ASCII");
            if (type.equals("IHDR")) {
                w = int32(b, at + 8);
                h = int32(b, at + 12);
                int depth = b[at + 16] & 255, colour = b[at + 17] & 255, interlace = b[at + 20] & 255;
                if (depth != 8 || colour != 3 || interlace != 0) {
                    throw new IOException(name + ": bit depth " + depth + ", colour type " + colour + ", interlace " + interlace
                            + "; only 8-bit palette, not interlaced, is read");
                }
            } else if (type.equals("IDAT")) {
                idat.write(b, at + 8, n);
            } else if (type.equals("IEND")) {
                break;
            }
            at += 12 + n;
        }
        if (w <= 0 || h <= 0) throw new IOException(name + ": no IHDR");
        byte[] raw = new byte[(w + 1) * h];
        Inflater inf = new Inflater();
        inf.setInput(idat.toByteArray());
        try {
            int got = 0;
            while (got < raw.length && !inf.finished()) {
                int k = inf.inflate(raw, got, raw.length - got);
                if (k == 0 && (inf.needsInput() || inf.needsDictionary())) break;
                got += k;
            }
            if (got != raw.length) throw new IOException(name + ": image data ends early");
        } catch (DataFormatException e) {
            throw new IOException(name + ": " + e.getMessage(), e);
        } finally {
            inf.end();
        }
        byte[] out = new byte[w * h];
        for (int y = 0; y < h; y++) {
            int filter = raw[y * (w + 1)] & 255, src = y * (w + 1) + 1, row = y * w, up = row - w;
            for (int x = 0; x < w; x++) {
                int a = x > 0 ? out[row + x - 1] & 255 : 0, c = y > 0 ? out[up + x] & 255 : 0;
                int d = x > 0 && y > 0 ? out[up + x - 1] & 255 : 0, v = raw[src + x] & 255;
                switch (filter) {
                    case 0: break;
                    case 1: v += a; break;
                    case 2: v += c; break;
                    case 3: v += (a + c) >> 1; break;
                    case 4: v += paeth(a, c, d); break;
                    default: throw new IOException(name + ": unknown row filter " + filter);
                }
                out[row + x] = (byte) v;
            }
        }
        return new Png(w, h, out);
    }

    private static int paeth(int a, int b, int c) {
        int p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
        return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
    }

    private static int int32(byte[] b, int at) {
        return ((b[at] & 255) << 24) | ((b[at + 1] & 255) << 16) | ((b[at + 2] & 255) << 8) | (b[at + 3] & 255);
    }

    static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[1 << 16];
        for (int n; (n = in.read(buf)) > 0; ) out.write(buf, 0, n);
        in.close();
        return out.toByteArray();
    }
}
