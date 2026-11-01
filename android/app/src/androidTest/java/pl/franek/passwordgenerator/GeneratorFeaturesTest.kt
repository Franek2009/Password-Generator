package pl.franek.passwordgenerator

import android.app.Application
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.input.key.Key
import androidx.lifecycle.ViewModelProvider
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalTestApi::class)
class GeneratorFeaturesTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val model get() = ViewModelProvider(rule.activity)[GeneratorViewModel::class.java]
    private fun idle(action: () -> Unit) { rule.runOnIdle(action); rule.waitForIdle() }
    private fun waitWork() { rule.waitUntil(5000) { !model.working }; rule.waitForIdle() }
    private fun reset() { idle {
        model.customPresets.toList().forEach { model.deletePreset(it.id) }
        model.update { UiState(language = "en", theme = "light") }
    } }

    @Test fun builtinAndCustomPresetsRestoreAndDeleteWithoutSecrets() {
        reset()
        idle { model.applyPreset("strong") }; waitWork()
        idle {
            assertEquals(24, model.state.length)
            assertTrue(model.state.uppercase && model.state.lowercase && model.state.managerNumbers && model.state.managerSpecial)
            model.update { it.copy(excludeSimilar = true, password = "PUBLIC-NOT-PERSISTED-5849") }
            model.savePreset("Instrumented custom")
        }
        val id = model.selectedPreset
        idle { model.update { it.copy(length = 8, excludeSimilar = false) }; model.applyPreset(id) }; waitWork()
        idle {
            assertEquals(24, model.state.length)
            assertTrue(model.state.excludeSimilar)
            assertEquals("", model.state.password)
        }
        rule.onAllNodesWithContentDescription("Length").assertCountEquals(2)
        rule.onNodeWithText("Exclude similar characters").performScrollTo().assertIsOn()
        idle {
            val app = rule.activity.application as Application
            val restarted = GeneratorViewModel(app)
            assertTrue(restarted.customPresets.any { it.id == id })
            val persisted = app.getSharedPreferences("generator", Context.MODE_PRIVATE).all.toString()
            assertFalse(persisted.contains("PUBLIC-NOT-PERSISTED"))
            assertFalse(persisted.contains("5849"))
            model.deletePreset("strong")
            assertTrue(model.presets.any { it.id == "strong" })
            model.deletePreset(id)
            assertFalse(GeneratorViewModel(app).customPresets.any { it.id == id })
        }
        idle { model.applyPreset("phrase") }; waitWork()
        idle {
            assertEquals(PasswordMode.HUMAN, model.state.mode)
            assertEquals(5, model.state.words)
            assertFalse(model.state.humanNumbers || model.state.humanSpecial)
            assertEquals("-", model.state.separator)
            assertEquals("", model.state.wordlist)
            assertEquals(24, model.state.length)
        }
    }

    @Test fun transcriptionCopiesRawLongResultAndModeClearsIt() {
        reset()
        val raw = "kR7!mP4#zQ9@".repeat(6)
        idle { model.update { it.copy(password = raw) } }
        rule.onNodeWithText("Transcription view").performScrollTo().performClick()
        idle {
            assertEquals(raw, model.state.password)
            model.copy()
            val clipboard = rule.activity.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            assertEquals(raw, clipboard.primaryClip!!.getItemAt(0).text.toString())
        }
        // The accessibility result exposes the original, not visual separators.
        val result = rule.onNodeWithContentDescription("Your password will appear here")
        result.performScrollTo().performTouchInput { click(center) }
        result.performKeyInput {
            keyDown(Key.CtrlLeft); pressKey(Key.A); pressKey(Key.C); keyUp(Key.CtrlLeft)
        }
        idle {
            val clipboard = rule.activity.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            assertEquals(raw, clipboard.primaryClip!!.getItemAt(0).text.toString())
        }
        rule.onNodeWithText("Passphrase").performScrollTo().performClick()
        idle { assertEquals("", model.state.password) }
        val phrase = "An exceptionally long word / ".repeat(20)
        idle { model.update { it.copy(password = phrase) }; model.copy() }
        idle {
            val clipboard = rule.activity.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            assertEquals(phrase, clipboard.primaryClip!!.getItemAt(0).text.toString())
        }
    }

    @Test fun missingOrUnpermittedDictionaryDoesNotFallback() {
        reset()
        idle { model.update { it.copy(mode = PasswordMode.HUMAN, wordlist = "content://com.android.contacts/contacts", wordlistName = "Unavailable") } }
        idle { model.savePreset("Unavailable words") }
        val id = model.selectedPreset
        idle { model.update { it.copy(mode = PasswordMode.MANAGER) } }
        idle { model.update { it.copy(password = "Public old result") }; model.applyPreset(id) }; waitWork()
        idle {
            assertEquals(PasswordMode.MANAGER, model.state.mode)
            assertEquals("Public old result", model.state.password)
            assertNotNull(model.message)
            model.deletePreset(id)
            model.update { it.copy(mode = PasswordMode.HUMAN) }
            model.generate()
        }; waitWork()
        idle { assertEquals("", model.state.password); assertNotNull(model.message) }
    }

    @Test fun lateGenerationCannotRestorePreviousModeResult() {
        reset()
        idle {
            model.generate()
            model.update { it.copy(mode = PasswordMode.HUMAN) }
        }; waitWork()
        idle { assertEquals("", model.state.password) }
    }

    @Test fun invalidStoredPresetTypesAreReportedWithoutRewriting() {
        reset()
        idle {
            val app = rule.activity.application as Application
            val preferences = app.getSharedPreferences("generator", Context.MODE_PRIVATE)
            val previous = preferences.getString("presets", "") ?: ""
            try {
                preferences.edit().putBoolean("presets", true).commit()
                val restarted = GeneratorViewModel(app)
                assertEquals("preset_invalid", restarted.message)
                assertTrue(restarted.customPresets.isEmpty())
                assertEquals(3, restarted.presets.size)
                assertEquals(true, preferences.all["presets"])
            } finally { preferences.edit().putString("presets", previous).commit() }
        }
    }

    @Test fun phraseWrappingKeepsWordsAndOriginalOffsets() {
        val raw = "Rower-Las-Zamek-Polana-Dom"
        val transformed = PhraseTransformation.filter(AnnotatedString(raw))
        assertEquals(raw, transformed.text.text.replace("\u200B", ""))
        assertEquals(raw.split("-").size - 1, transformed.text.text.count { it == '\u200B' })
        for (i in 0..raw.length) {
            assertEquals(i, transformed.offsetMapping.transformedToOriginal(transformed.offsetMapping.originalToTransformed(i)))
        }
        for (i in 0..transformed.text.length) assertTrue(transformed.offsetMapping.transformedToOriginal(i) in 0..raw.length)
        val spaces = "A word  Another word"
        assertEquals(spaces, PhraseTransformation.filter(AnnotatedString(spaces)).text.text)
    }

    @Test fun transformationOffsetsAndOriginalAreConsistent() {
        for (size in 0..65) {
            val raw = "a".repeat(size)
            val result = TranscriptionTransformation.filter(AnnotatedString(raw))
            assertEquals(raw.chunked(4).joinToString("  "), result.text.text)
            for (offset in 0..size) {
                val mapped = result.offsetMapping.originalToTransformed(offset)
                assertTrue(mapped in 0..result.text.length)
                assertEquals(offset, result.offsetMapping.transformedToOriginal(mapped))
            }
            for (offset in 0..result.text.length) assertTrue(result.offsetMapping.transformedToOriginal(offset) in 0..size)
        }
    }
}
