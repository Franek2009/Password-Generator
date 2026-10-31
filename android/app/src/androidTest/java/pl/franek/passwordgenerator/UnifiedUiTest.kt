package pl.franek.passwordgenerator

import android.app.Application
import android.graphics.Bitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class UnifiedUiTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val model get() = ViewModelProvider(rule.activity)[GeneratorViewModel::class.java]

    private fun update(transform: (UiState) -> UiState) {
        rule.runOnIdle { model.update(transform) }
        rule.waitForIdle()
    }

    @Test fun languageThemeModeAndRotationPreserveTheCurrentPassword() {
        update { UiState(language = "en", theme = "light", length = 32, password = "Public-test-example") }
        rule.onNodeWithText("Random password").assertExists()
        rule.onNodeWithText("Passphrase").performClick()
        rule.onNodeWithText("Word separator").assertExists()
        update { it.copy(language = "pl", theme = "dark", humanNumbers = false) }
        rule.onNodeWithText("Fraza słowna").assertExists()
        rule.activityRule.scenario.onActivity { it.requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE }
        rule.waitForIdle()
        rule.activityRule.scenario.recreate()
        rule.waitForIdle()
        rule.runOnIdle {
            assertEquals("Public-test-example", model.state.password)
            assertEquals(32, model.state.length)
            assertFalse(model.state.humanNumbers)
            assertTrue(model.state.managerNumbers)
            val restarted = GeneratorViewModel(rule.activity.application as Application)
            assertEquals("", restarted.state.password)
            assertEquals(32, restarted.state.length)
            assertEquals("pl", restarted.state.language)
        }
    }

    @Test fun copyingAndSettingsUseTheCurrentLanguage() {
        update { UiState(language = "en", theme = "light", password = "Public-test-example") }
        rule.onNodeWithContentDescription("Copy password").performClick()
        rule.onNodeWithText("Password copied").assertExists()
        rule.onNodeWithContentDescription("More options").performClick()
        rule.onNodeWithText("Settings").performClick()
        rule.onNodeWithText("Application theme").assertExists()
        rule.onNodeWithText("Automatically copy passwords").assertExists()
        rule.onNodeWithContentDescription("Back").performClick()
        rule.onNodeWithText("Public-test-example").assertExists()
    }

    @Test fun captureReviewScreenshots() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val output = File(instrumentation.targetContext.getExternalFilesDir(null), "ui-preview").apply { mkdirs() }
        fun screenshot(name: String) {
            rule.waitForIdle()
            instrumentation.waitForIdleSync()
            Thread.sleep(250)
            instrumentation.uiAutomation.takeScreenshot().also { bitmap ->
                File(output, name).outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
                bitmap.recycle()
            }
        }
        for (theme in listOf("dark", "light")) {
            update { UiState(theme = theme, language = "pl", password = "k8Z!rQ4#mP9vL2@tX") }
            screenshot("android-$theme-random.png")
            update { it.copy(mode = PasswordMode.HUMAN, password = "Rower-Las-Zamek-42-!") }
            screenshot("android-$theme-phrase.png")
            rule.onNodeWithContentDescription("Więcej opcji").performClick()
            rule.onNodeWithText("Ustawienia").performClick()
            screenshot("android-$theme-settings.png")
            rule.onNodeWithContentDescription("Wstecz").performClick()
        }
        update { it.copy(language = "en") }
        screenshot("android-english.png")
        fun fontScale(value: String) {
            android.os.ParcelFileDescriptor.AutoCloseInputStream(
                instrumentation.uiAutomation.executeShellCommand("settings put system font_scale $value")
            ).use { it.readBytes() }
            Thread.sleep(500)
            rule.waitForIdle()
        }
        try {
            fontScale("1.3")
            rule.onNodeWithText("Generate password").performScrollTo()
            screenshot("android-english-large-font.png")
        } finally { fontScale("1.0") }
    }
}
