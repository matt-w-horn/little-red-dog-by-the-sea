package io.matthorn.littlereddog;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;

/**
 * The tile: the same scene as the screensaver, full screen until Back. Hidden in it, and in the screensaver, is a fast
 * mode: Up, Up, Down, Down, Left, Right, Left, Right on the remote (Secret) runs the clock through a day and a night
 * in about 40 seconds, starting just before dawn. OK, or the same keys again, puts the real time back.
 */
public class DogActivity extends Activity {

    private final Secret secret = new Secret();
    private SceneView view;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        view = new SceneView(this);
        setContentView(view);
        hideSystemUi();

        // For screenshots and checks: a fixed minute of the day, date, weather (0 clear, 1 cloudy, 2 rain) and
        // lighting state (0 dawn, 1 day, 2 dusk, 3 night, 4 cloudy, 5 rain):
        //   am start -n io.matthorn.littlereddog/.DogActivity --ei minute 1260 --es date 2026-11-24 --ei weather 0 --ei state 3
        // a pose of scene.json instead of the schedule (an unknown name keeps the schedule):
        //   am start -n io.matthorn.littlereddog/.DogActivity --es pose curl
        // and the fast mode without the remote:
        //   am start -n io.matthorn.littlereddog/.DogActivity --ez fast true
        Intent intent = getIntent();
        if (intent.getBooleanExtra("fast", false)) view.setFast(true);
        view.setPose(intent.getStringExtra("pose"));
        if (intent.hasExtra("minute")) view.setFixedMinute(intent.getIntExtra("minute", 720));
        if (intent.hasExtra("weather")) view.setFixedWeather(intent.getIntExtra("weather", 0));
        if (intent.hasExtra("state")) view.setFixedState(intent.getIntExtra("state", 1));
        String date = intent.getStringExtra("date");
        if (date != null && date.matches("\\d{4}-\\d{2}-\\d{2}")) {
            view.setFixedDate(Integer.parseInt(date.substring(0, 4)), Integer.parseInt(date.substring(5, 7)),
                    Integer.parseInt(date.substring(8, 10)));
        }
    }

    @SuppressWarnings("deprecation")
    private void hideSystemUi() {
        // The systemUiVisibility flags still work on API 26..34; WindowInsetsController needs API 30.
        view.setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemUi();
    }

    @Override
    protected void onResume() {
        super.onResume();
        view.start();
    }

    @Override
    protected void onPause() {
        view.stop();
        super.onPause();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        view.interacted();
        if (event.getRepeatCount() == 0) {
            if (Secret.isOk(keyCode) && view.isFast()) {
                secret.reset();
                view.setFast(false);
                return true;
            }
            int step = secret.press(keyCode);
            if (step == Secret.DONE) view.setFast(!view.isFast());
            if (step != Secret.MISS) return true;
        }
        return super.onKeyDown(keyCode, event);
    }
}
