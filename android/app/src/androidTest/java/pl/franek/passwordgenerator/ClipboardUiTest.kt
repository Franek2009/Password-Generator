package pl.franek.passwordgenerator

import android.app.Application
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.os.Build
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import java.io.File

class ClipboardUiTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val model get() = ViewModelProvider(rule.activity)[GeneratorViewModel::class.java]
    private val clipboard get() = rule.activity.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    private val raw = "Public-Żółw\u00a0Las"

    @Test fun scheduledForegroundExpiryNeedsNoFocusChange() {
        var now = 0L
        lateinit var controller: AndroidClipboardController
        rule.runOnIdle {
            controller = AndroidClipboardController(rule.activity) { now }
            controller.focusChanged(true)
            controller.setPolicy(30)
            assertTrue(controller.copy(raw))
            assertEquals(raw, clipboard.primaryClip!!.getItemAt(0).text.toString())
            now = 30000
        }
        try {
            rule.waitUntil(5000) { clipboard.primaryClip == null || clipboard.primaryClip!!.getItemAt(0).text.isNullOrEmpty() }
        } finally { rule.runOnIdle { controller.dispose() } }
    }

    @Test fun realClipboardExpiryBackgroundDeferralForeignCopyAndRotation() {
        var now = 0L
        lateinit var controller: AndroidClipboardController
        rule.runOnIdle {
            controller = AndroidClipboardController(rule.activity) { now }
            controller.focusChanged(true)
            controller.setPolicy(30)
            assertTrue(controller.copy(raw))
            assertEquals(raw, clipboard.primaryClip!!.getItemAt(0).text.toString())
            controller.focusChanged(false)
            now = 30000
            controller.setPolicy(30) // Expired, but no focused clipboard access.
        }
        rule.runOnIdle {
            controller.focusChanged(true)
            assertTrue(clipboard.primaryClip == null || clipboard.primaryClip!!.getItemAt(0).text.isNullOrEmpty())
            assertTrue(controller.copy(raw))
            controller.focusChanged(false)
        }
        val probe = Intent().setComponent(ComponentName(
            "pl.franek.passwordgenerator.test", "pl.franek.passwordgenerator.ClipboardProbeActivity"
        )).putExtra("text", "Foreign-public-text").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        rule.activity.startActivity(probe)
        rule.waitUntil(10000) { rule.activity.hasWindowFocus() }
        // Wait for the probe to actually complete (not just the pre-launch focus).
        rule.waitUntil(10000) {
            rule.activity.hasWindowFocus() && clipboard.primaryClipDescription?.extras?.getString(CLIPBOARD_TOKEN) == null
        }
        rule.runOnIdle {
            now = 60000
            controller.focusChanged(true)
            assertEquals("Foreign-public-text", clipboard.primaryClip!!.getItemAt(0).text.toString())
            controller.dispose()
            model.update { UiState(language="en",clipboardClearSeconds=30,password=raw) }
            model.copy()
        }
        val token = clipboard.primaryClipDescription!!.extras!!.getString(CLIPBOARD_TOKEN)
        rule.activityRule.scenario.recreate()
        rule.runOnIdle {
            assertEquals(raw, clipboard.primaryClip!!.getItemAt(0).text.toString())
            assertEquals(token, clipboard.primaryClipDescription!!.extras!!.getString(CLIPBOARD_TOKEN))
            model.update { it.copy(clipboardClearSeconds=0) }
        }
    }

    @Test fun settingsCopyRoutesPersistenceAndPublicPreviews() {
        rule.runOnIdle { model.update { UiState(language="en",theme="light",password=raw) } }
        rule.onNodeWithContentDescription("More options").performClick()
        rule.onNodeWithText("Settings").performClick()
        rule.onNodeWithText("Clear copied password").performScrollTo().assertExists()
        rule.onNodeWithContentDescription("Clear copied password").assertExists()
        rule.onNodeWithText("Off").performClick()
        rule.onNodeWithText("30 seconds").performClick()
        rule.runOnIdle {
            assertEquals(30, model.state.clipboardClearSeconds)
            model.copy()
            assertEquals(raw, clipboard.primaryClip!!.getItemAt(0).text.toString())
            assertNotNull(clipboard.primaryClipDescription!!.extras!!.getString(CLIPBOARD_TOKEN))
            if (Build.VERSION.SDK_INT >= 33) assertTrue(clipboard.primaryClipDescription!!.extras!!.getBoolean("android.content.extra.IS_SENSITIVE"))
            val restarted = GeneratorViewModel(rule.activity.application as Application)
            assertEquals(30, restarted.state.clipboardClearSeconds)
            val prefs = rule.activity.getSharedPreferences("generator", Context.MODE_PRIVATE).all
            assertFalse(prefs.toString().contains(raw))
            assertFalse(prefs.keys.any { it.contains("token",true) || it.contains("digest",true) || it.contains("deadline",true) })
            assertFalse(model.presets.any { it.config.containsKey("clipboard_clear_seconds") })
        }
        // Let System UI's clipboard confirmation disappear before capturing settings.
        android.os.SystemClock.sleep(7000)
        for (theme in listOf("light","dark")) {
            rule.runOnIdle { model.update { it.copy(theme=theme) } }
            rule.onNodeWithText("Clear copied password").performScrollTo().assertExists()
            val file = File(rule.activity.getExternalFilesDir(null), "v150-preview/android-$theme-clipboard.png")
            file.parentFile!!.mkdirs()
            file.outputStream().use { output -> InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot().compress(Bitmap.CompressFormat.PNG,100,output) }
        }
        rule.runOnIdle {
            model.update { it.copy(clipboardClearSeconds=0) }
            model.copy()
            assertNull(clipboard.primaryClipDescription!!.extras?.getString(CLIPBOARD_TOKEN))
        }
    }
}
