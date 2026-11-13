package io.matthorn.littlereddog;

import android.service.dreams.DreamService;
import android.view.KeyEvent;
import android.view.MotionEvent;

/**
 * The screensaver: the beach, the dog, the clock and a quote that changes every hour, until a key wakes the TV.
 *
 * It takes the keys itself (an interactive dream), so that the hidden sequence works here as it does in the tile:
 * Up, Up, Down, Down, Left, Right, Left, Right starts the fast mode, and OK or the same keys stop it. Every other key
 * wakes the TV at once, as it does in any screensaver. A key that fits the sequence cannot wake the TV at once,
 * because the next key may continue the sequence: it wakes the TV when no key follows within PAUSE_MS.
 */
public class DogDream extends DreamService {

    /** How long a key of the sequence waits for the next one before it counts as an ordinary key and wakes the TV. */
    private static final long PAUSE_MS = 1500;

    private final Secret secret = new Secret();
    private final Runnable wake = this::wakeUp;
    private SceneView view;

    @Override
    public void onAttachedToWindow() {
        super.onAttachedToWindow();
        setInteractive(true);
        setFullscreen(true);
        setScreenBright(true);
        view = new SceneView(this);
        setContentView(view);
    }

    @Override
    public void onDreamingStarted() {
        super.onDreamingStarted();
        view.start();
    }

    @Override
    public void onDreamingStopped() {
        view.removeCallbacks(wake);
        view.stop();
        super.onDreamingStopped();
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() != KeyEvent.ACTION_DOWN || event.getRepeatCount() != 0) return true;
        int key = event.getKeyCode();
        view.removeCallbacks(wake);
        view.interacted();
        if (Secret.isOk(key) && view.isFast()) {
            secret.reset();
            view.setFast(false);
            return true;
        }
        switch (secret.press(key)) {
            case Secret.DONE:
                view.setFast(!view.isFast());
                break;
            case Secret.PART:
                view.postDelayed(wake, PAUSE_MS);
                break;
            default:
                wakeUp();
        }
        return true;
    }

    // An interactive dream is not woken by the system on input, so every input that is not a key wakes it here,
    // as DreamService does for a dream that is not interactive.

    @Override
    public boolean dispatchKeyShortcutEvent(KeyEvent event) {
        wakeUp();
        return true;
    }

    @Override
    public boolean dispatchTouchEvent(MotionEvent event) {
        wakeUp();
        return true;
    }

    @Override
    public boolean dispatchTrackballEvent(MotionEvent event) {
        wakeUp();
        return true;
    }

    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent event) {
        wakeUp();
        return true;
    }
}
