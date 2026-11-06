package pl.franek.passwordgenerator;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;

/** Test-only foreign application; public example strings, never production data. */
public class ClipboardProbeActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        // Wait for this test-package activity to acquire input focus.
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            String text = getIntent().getStringExtra("text");
            if (text != null) {
                ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                clipboard.setPrimaryClip(ClipData.newPlainText("Public test", text));
            }
            finish();
        }, 500);
    }
}
