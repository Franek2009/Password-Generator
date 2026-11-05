package pl.franek.passwordgenerator

import android.app.Application
import android.content.Context
import android.content.ClipboardManager
import android.graphics.Bitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.lifecycle.ViewModelProvider
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import java.io.File

class AdvancedUiTest {
    @get:Rule val rule=createAndroidComposeRule<MainActivity>()
    private val model get()=ViewModelProvider(rule.activity)[GeneratorViewModel::class.java]
    private fun idle(action:()->Unit) { rule.runOnIdle(action);rule.waitUntil(15000) { !model.working };rule.waitForIdle() }
    private fun reset() {
        model.customPresets.map { it.id }.forEach { id -> idle { model.deletePreset(id) } }
        idle { model.update { UiState(language="en",theme="light") } }
    }
    private val unique=AdvancedRules(enabled=true,customAlphabetEnabled=true,customAlphabet="a1",
        firstType=CharacterType.LOWER,maxIdenticalRun=1)

    @Test fun nativeControlsRestoreRulesCopyRawAndNeverPersistResult() {
        reset()
        rule.onNodeWithText("Advanced rules").performScrollTo().performClick()
        rule.onNodeWithText("Use advanced rules").performScrollTo().assertIsOff().performClick().assertIsOn()
        rule.onNodeWithContentDescription("Minimum digits").performScrollTo().performTextReplacement("3")
        idle { assertEquals(3,model.state.advanced.minDigits) }
        rule.onNodeWithText("Use custom alphabet").performScrollTo().performClick()
        rule.onNodeWithText("Allowed characters (ASCII, no spaces)").performScrollTo().performTextInput("a1")
        idle {
            assertEquals("a1",model.state.advanced.customAlphabet)
            model.update { it.copy(length=8,advanced=unique) }
            model.generate()
        }
        idle {
            assertEquals("a1a1a1a1",model.state.password)
            assertEquals("single_result",model.validationMessage)
            model.update { it.copy(transcription=true) };model.copy()
            val clip=rule.activity.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            assertEquals("a1a1a1a1",clip.primaryClip!!.getItemAt(0).text.toString())
            model.savePreset("Advanced instrumented")
        }
        val id=model.selectedPreset
        idle {
            val restarted=GeneratorViewModel(rule.activity.application as Application)
            assertEquals(unique.toData(),restarted.state.advanced.toData())
            assertEquals("",restarted.state.password)
            val prefs=rule.activity.getSharedPreferences("generator",Context.MODE_PRIVATE).all.toString()
            assertFalse(prefs.contains("a1a1a1a1"))
            model.update { it.copy(advanced=AdvancedRules(),length=24) }
            model.applyPreset(id)
        }
        idle {
            assertEquals(unique.toData(),model.state.advanced.toData())
            assertEquals(8,model.state.length)
            assertEquals("",model.state.password)
            model.deletePreset(id)
        }
    }

    @Test fun invalidDraftCanBeDisabledAndImpossiblePresetIsAtomic() {
        reset()
        idle { model.update { it.copy(advanced=unique.copy(customAlphabet="ą ")) };model.generate() }
        idle {
            assertEquals("",model.state.password)
            assertEquals("rules_ascii",model.validationMessage)
            model.update { it.copy(advanced=it.advanced.copy(enabled=false)) }
            model.generate()
        }
        idle { assertEquals(20,model.state.password.length) }
        val impossible=Preset("test-invalid","Impossible",Presets.parameters(UiState(length=8,advanced=unique.copy(customAlphabet="a"))))
        idle {
            // Store-level validation stays cheap; application must check exact feasibility.
            val app=rule.activity.application as Application
            app.getSharedPreferences("generator",Context.MODE_PRIVATE).edit().putString("presets_v2",Presets.encode(listOf(impossible.copy(id="custom-00000000-0000-4000-8000-000000000099")))) .commit()
            val restarted=GeneratorViewModel(app)
            assertEquals(1,restarted.customPresets.size)
            restarted.applyPreset(restarted.customPresets.single().id)
            pending=restarted
        }
        rule.waitUntil(15000) { pending?.working==false }
        idle {
            assertEquals(20,pending!!.state.length)
            assertFalse(pending!!.state.advanced.enabled)
            assertNotNull(pending!!.message)
        }
    }
    private var pending:GeneratorViewModel?=null

    @Test fun configurationEditCancelsPendingResultAndPassphraseIgnoresRules() {
        reset()
        idle {
            model.update { it.copy(length=64,advanced=AdvancedRules(enabled=true,minUppercase=13,minLowercase=13,minDigits=13,minSymbols=13,maxIdenticalRun=1)) }
            model.generate()
            model.update { it.copy(mode=PasswordMode.HUMAN) }
        }
        idle { assertEquals("",model.state.password);model.generate() }
        idle { assertTrue(model.state.password.isNotEmpty()) }
    }

    @Test fun captureVerifiedPublicExamplesInBothThemes() {
        reset()
        // This deliberately forced public example cannot serve as a real password.
        idle { model.update { it.copy(length=8,advanced=unique,transcription=true) };model.generate() }
        for(theme in listOf("light","dark")) {
            idle { model.update { it.copy(theme=theme) } }
            rule.onNodeWithContentDescription("Your password will appear here").performScrollTo().assertExists()
            screenshot("android-$theme-result.png")
            rule.onNodeWithText("Advanced rules").performScrollTo().performClick()
            rule.onNodeWithContentDescription("Minimum uppercase letters").performScrollTo().assertExists()
            screenshot("android-$theme-rules.png")
            rule.onNodeWithText("Allowed characters (ASCII, no spaces)").performScrollTo().assertExists()
            screenshot("android-$theme-alphabet.png")
            rule.onNodeWithText("Maximum consecutive repeats").performScrollTo().assertExists()
            screenshot("android-$theme-endpoints.png")
            rule.onNodeWithText("Advanced rules").performScrollTo().performClick()
        }
    }
    private fun screenshot(name:String) {
        val file=File(rule.activity.getExternalFilesDir(null),"v130-preview/$name")
        file.parentFile!!.mkdirs()
        file.outputStream().use { output -> rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG,100,output) }
    }
}
