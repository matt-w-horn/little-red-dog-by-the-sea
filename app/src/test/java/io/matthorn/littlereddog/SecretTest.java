package io.matthorn.littlereddog;

import static org.junit.Assert.assertEquals;

import android.view.KeyEvent;
import org.junit.Test;

/** The hidden key sequence, key by key. KeyEvent's key codes are constants, so this runs without a television. */
public class SecretTest {

    private static final int UP = KeyEvent.KEYCODE_DPAD_UP, DOWN = KeyEvent.KEYCODE_DPAD_DOWN,
            LEFT = KeyEvent.KEYCODE_DPAD_LEFT, RIGHT = KeyEvent.KEYCODE_DPAD_RIGHT, OK = KeyEvent.KEYCODE_DPAD_CENTER;

    /** What each key did, as one letter a key: m for a miss, p for a part of the sequence, D when it is done. */
    private static String press(Secret secret, int... keys) {
        StringBuilder out = new StringBuilder();
        for (int key : keys) out.append("mpD".charAt(secret.press(key)));
        return out.toString();
    }

    @Test
    public void theSequenceCompletesAndStartsOver() {
        Secret s = new Secret();
        assertEquals("pppppppD", press(s, UP, UP, DOWN, DOWN, LEFT, RIGHT, LEFT, RIGHT));
        assertEquals("pppppppD", press(s, UP, UP, DOWN, DOWN, LEFT, RIGHT, LEFT, RIGHT));
    }

    @Test
    public void aThirdUpKeepsTheTwoUpsBeforeIt() {
        assertEquals("ppmpppppD", press(new Secret(), UP, UP, UP, DOWN, DOWN, LEFT, RIGHT, LEFT, RIGHT));
        assertEquals("ppmmpppppD", press(new Secret(), UP, UP, UP, UP, DOWN, DOWN, LEFT, RIGHT, LEFT, RIGHT));
    }

    @Test
    public void aWrongKeyStartsOver() {
        Secret s = new Secret();
        assertEquals("pppm", press(s, UP, UP, DOWN, OK));
        assertEquals("m", press(s, DOWN));                       // the Down no longer continues anything
        assertEquals("pppppppD", press(s, UP, UP, DOWN, DOWN, LEFT, RIGHT, LEFT, RIGHT));
    }

    @Test
    public void anUpAfterAWrongTurnCountsAsTheFirstUp() {
        Secret s = new Secret();
        assertEquals("pppm", press(s, UP, UP, DOWN, UP));        // this Up is the first Up of a new try
        assertEquals("ppppppD", press(s, UP, DOWN, DOWN, LEFT, RIGHT, LEFT, RIGHT));
    }

    @Test
    public void resetForgetsThePart() {
        Secret s = new Secret();
        assertEquals("ppp", press(s, UP, UP, DOWN));
        s.reset();
        assertEquals("m", press(s, DOWN));
    }
}
