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
    @Test fun editPresetFromMainViewRenameAndRestart() {
        reset()
        idle { model.savePreset("Editable") }
        val id=model.selectedPreset
        val original=model.state.length
        idle { model.update { it.copy(length=32,password="memory-only-result") } }
        idle { assertEquals(id,model.selectedPreset);assertTrue(model.presetModified) }
        rule.onNodeWithText("Editable (modified)").performScrollTo().performClick()
        rule.onNodeWithText("Update preset…").performClick()
        rule.onNodeWithText("Close").performClick()
        idle { assertEquals(original,model.customPresets.single().config["length"]) }
        rule.onNodeWithText("Editable (modified)").performClick()
        rule.onNodeWithText("Update preset…").performClick()
        // Confirmation retains the exact target name.
        rule.onNodeWithText("Replace the saved settings of preset “Editable” with the current generator settings?").assertExists()
        rule.onAllNodesWithText("Update preset…").onLast().performClick()
        rule.waitUntil(15000) { !model.working && !model.presetModified }
        idle {
            assertEquals(32,model.customPresets.single().config["length"])
            assertEquals("memory-only-result",model.state.password)
            model.update { it.copy(length=24) }
        }
        rule.onNodeWithText("Editable (modified)").performClick()
        rule.onNodeWithText("Rename preset…").performClick()
        rule.onNodeWithText("Preset name").performTextReplacement("Renamed")
        rule.onAllNodesWithText("Rename preset…").onLast().performClick()
        rule.waitUntil(15000) { !model.working && model.customPresets.single().name=="Renamed" }
        idle {
            assertEquals(24,model.state.length)
            assertTrue(model.presetModified)
            assertEquals(32,model.customPresets.single().config["length"])
            val restarted=GeneratorViewModel(rule.activity.application as Application)
            assertEquals(model.customPresets,restarted.customPresets)
            assertEquals("",restarted.selectedPreset)
            assertEquals("",restarted.state.password)
            assertFalse(rule.activity.getSharedPreferences("generator",Context.MODE_PRIVATE).all.toString().contains("memory-only-result"))
            model.update { it.copy(mode=PasswordMode.HUMAN) }
            assertEquals("",model.state.password)
            model.updatePreset(id)
        }
        idle { assertEquals("human",model.customPresets.single().config["mode"]) }
    }

    @Test fun invalidPresetEditsPreserveSavedDataAndCancelPendingUpdate() {
        reset()
        idle { model.savePreset("Editable") }
        val id=model.selectedPreset
        val saved=model.customPresets.single()
        idle { model.update { it.copy(length=8,advanced=unique.copy(customAlphabet="a")) };model.updatePreset(id) }
        idle {
            assertEquals(saved,model.customPresets.single())
            assertEquals(id,model.selectedPreset)
            assertTrue(model.presetModified)
            assertEquals("no_valid_password",model.message)
            model.renamePreset(id,"Standard")
            assertEquals(saved,model.customPresets.single())
            model.update { it.copy(mode=PasswordMode.HUMAN,wordlist="content://missing-provider/list") }
            model.updatePreset(id)
        }
        idle {
            assertEquals(saved,model.customPresets.single())
            model.update { it.copy(mode=PasswordMode.MANAGER,length=64,advanced=AdvancedRules(enabled=true,
                minUppercase=13,minLowercase=13,minDigits=13,minSymbols=13,maxIdenticalRun=1)) }
            model.updatePreset(id)
            model.update { it.copy(length=32) }
        }
        idle {
            assertEquals(saved,model.customPresets.single())
            assertEquals(id,model.selectedPreset)
        }
    }

    @Test fun failedPresetWritesRestoreSavedCollectionAndPreferenceCache() {
        val real=rule.activity.getSharedPreferences("preset-edit-failure-test",Context.MODE_PRIVATE)
        val saved=Presets.create("Saved",UiState(),emptyList())
        val original=Presets.encode(listOf(saved))
        real.edit().clear().putString("presets_v2",original).commit()
        var failNext=true
        val failing=object:android.content.SharedPreferences by real {
            override fun edit():android.content.SharedPreferences.Editor {
                val editor=real.edit()
                return object:android.content.SharedPreferences.Editor by editor {
                    override fun putString(key:String?,value:String?):android.content.SharedPreferences.Editor {
                        editor.putString(key,value);return this
                    }
                    override fun commit():Boolean {
                        val result=editor.commit()
                        if(failNext) { failNext=false;return false }
                        return result
                    }
                }
            }
        }
        val app=object:Application() {
            override fun getSharedPreferences(name:String?,mode:Int)=failing
        }
        lateinit var edited:GeneratorViewModel
        rule.runOnIdle { edited=GeneratorViewModel(app);edited.renamePreset(saved.id,"Other") }
        rule.waitUntil(15000) { !edited.working }
        rule.runOnIdle {
            assertEquals("settings_write",edited.message)
            assertEquals(listOf(saved),edited.customPresets)
            assertEquals(original,real.getString("presets_v2",null))
            assertEquals(listOf(saved),GeneratorViewModel(app).customPresets)
            failNext=true
            edited.updatePreset(saved.id)
        }
        rule.waitUntil(15000) { !edited.working }
        rule.runOnIdle {
            assertEquals(listOf(saved),edited.customPresets)
            assertEquals(original,real.getString("presets_v2",null))
        }
        real.edit().clear().commit()
    }

    @Test fun capturePresetEditingInBothThemes() {
        reset()
        idle { model.update { it.copy(length=8,advanced=unique) };model.generate() }
        idle { model.savePreset("Example") }
        idle { model.update { it.copy(length=10) } }
        // System UI clipboard overlays from earlier copy tests must finish before capture.
        android.os.SystemClock.sleep(7000)
        for(theme in listOf("light","dark")) {
            idle { model.update { it.copy(theme=theme) } }
            rule.onNodeWithText("Example (modified)").performScrollTo().performClick()
            rule.onNodeWithText("Update preset…").assertExists()
            screenshotEditing("android-$theme-preset-menu.png")
            rule.onNodeWithText("Update preset…").performClick()
            rule.onNodeWithText("Replace the saved settings of preset “Example” with the current generator settings?").assertExists()
            screenshotEditing("android-$theme-preset-confirm.png")
            rule.onNodeWithText("Close").performClick()
        }
    }

    private fun screenshotEditing(name:String) {
        val file=File(rule.activity.getExternalFilesDir(null),"v140-preview/$name")
        file.parentFile!!.mkdirs()
        file.outputStream().use { output ->
            androidx.test.platform.app.InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
                .compress(Bitmap.CompressFormat.PNG,100,output)
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
