package io.matthorn.littlereddog;

import android.view.KeyEvent;

/**
 * The hidden key sequence that starts and stops the fast mode: Up, Up, Down, Down, Left, Right, Left, Right.
 * The tile and the screensaver each keep one of these and give it every key that goes down.
 */
final class Secret {

    /** What a key did to the sequence: it does not belong, it continues the sequence, or it completes it. */
    static final int MISS = 0, PART = 1, DONE = 2;

    private static final int[] KEYS = {KeyEvent.KEYCODE_DPAD_UP, KeyEvent.KEYCODE_DPAD_UP, KeyEvent.KEYCODE_DPAD_DOWN,
            KeyEvent.KEYCODE_DPAD_DOWN, KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.KEYCODE_DPAD_RIGHT,
            KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.KEYCODE_DPAD_RIGHT};

    /** How many keys of the sequence have been pressed in order. */
    private int at;

    /** A key went down. */
    int press(int keyCode) {
        if (keyCode == KEYS[at]) {
            if (++at < KEYS.length) return PART;
            at = 0;
            return DONE;
        }
        // A third Up still leaves the last two Ups in place; any other wrong key starts over.
        at = keyCode != KEYS[0] ? 0 : at == 2 ? 2 : 1;
        return MISS;
    }

    void reset() {
        at = 0;
    }

    /** OK on the remote: it stops the fast mode. */
    static boolean isOk(int keyCode) {
        return keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER
                || keyCode == KeyEvent.KEYCODE_NUMPAD_ENTER || keyCode == KeyEvent.KEYCODE_BUTTON_A;
    }
}
