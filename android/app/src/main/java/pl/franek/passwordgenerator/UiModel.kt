package pl.franek.passwordgenerator

import android.app.Application
import android.content.ClipData
import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.PersistableBundle
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.io.InputStreamReader
import java.nio.charset.CodingErrorAction
import java.util.Locale
import java.security.SecureRandom
import org.json.JSONObject

class SharedUi(context: Context) {
    private val data = JSONObject(context.assets.open("ui.json").bufferedReader().use { it.readText() })
    fun resolvedLanguage(value: String): String = if (value == "system") {
        if (Locale.getDefault().language == "pl") "pl" else "en"
    } else value
    fun text(language: String, key: String): String = data.getJSONObject("strings")
        .getJSONObject(resolvedLanguage(language)).optString(key, data.getJSONObject("strings").getJSONObject("en").getString("unknown_error"))
    fun palette(dark: Boolean): JSONObject = data.getJSONObject("palettes").getJSONObject(if (dark) "dark" else "light")
    fun path(name: String): String = data.getJSONObject("icons").getString(name)
}

data class UiState(
    val excludeSimilar: Boolean = false, val transcription: Boolean = false,
    val advanced: AdvancedRules = AdvancedRules(),
    val mode: PasswordMode = PasswordMode.MANAGER,
    val length: Int = 20, val words: Int = 3, val separator: String = "-",
    val uppercase: Boolean = true, val lowercase: Boolean = true,
    val managerNumbers: Boolean = true, val managerSpecial: Boolean = true,
    val humanNumbers: Boolean = true, val humanSpecial: Boolean = true,
    val language: String = "system", val theme: String = "system", val autoCopy: Boolean = false,
    val wordlist: String = "", val wordlistName: String = "", val password: String = "",
)

class GeneratorViewModel(application: Application) : AndroidViewModel(application) {
    private val preferences = application.getSharedPreferences("generator", Context.MODE_PRIVATE)
    private val generator = PasswordGenerator()
    private val settingsWriteLock=Mutex()
    @Volatile private var revision = 0L
    private val presetVersion = if(preferences.contains("presets_v2")) 2 else 1
    private val storedPresets = preferences.all[if(presetVersion==2) "presets_v2" else "presets"]
    private val decodedPresets = when (val raw = storedPresets) {
        null -> emptyList<Preset>() to false
        is String -> Presets.decode(raw,presetVersion)
        else -> emptyList<Preset>() to true
    }
    var customPresets by mutableStateOf(decodedPresets.first)
        private set
    var selectedPreset by mutableStateOf("")
        private set
    val presets get() = Presets.builtins() + customPresets
    val presetModified: Boolean get() {
        val preset=customPresets.find { it.id==selectedPreset } ?: return false
        return runCatching { Presets.parameters(state)!=preset.config }.getOrDefault(true)
    }
    private var advancedReadError = false
    var state by mutableStateOf(readPreferences())
        private set
    var message by mutableStateOf<String?>(null)
        private set
    var validationMessage by mutableStateOf<String?>(null)
        private set
    var working by mutableStateOf(false)
        private set

    init {
        if (decodedPresets.second) message = "preset_invalid"
        else if(advancedReadError) message="settings_read"
    }

    private val presetWriteBlocked = storedPresets is String && Presets.unsupportedVersion(storedPresets)

    private fun configFor(value: UiState): PasswordConfig = if(value.mode==PasswordMode.MANAGER)
        PasswordConfig(length=value.length,uppercase=value.uppercase,lowercase=value.lowercase,numbers=value.managerNumbers,
            special=value.managerSpecial,excludeSimilar=value.excludeSimilar,advanced=Presets.effectiveRules(value.advanced))
        else PasswordConfig(mode=PasswordMode.HUMAN,words=value.words,separator=value.separator,numbers=value.humanNumbers,special=value.humanSpecial)

    private suspend fun validateFeasibility(value: UiState, request: Long) {
        if(value.mode==PasswordMode.MANAGER && value.advanced.enabled) withContext(Dispatchers.Default) {
            CompletionCounter(compileRules(configFor(value))) { request!=revision }.use { counter ->
                ruleCheck(counter.total().signum()>0,"no_valid_password")
            }
        }
    }

    private suspend fun persistPresets(proposed: List<Preset>): Boolean = withContext(Dispatchers.IO) {
        val previous=preferences.all["presets_v2"]
        val saved=try { preferences.edit().putString("presets_v2",Presets.encode(proposed)).commit() }
            catch(_:RuntimeException) { false }
        if(!saved) {
            // commit() updates the process cache even when the disk write fails.
            runCatching {
                preferences.edit().apply {
                    if(previous is String) putString("presets_v2",previous) else remove("presets_v2")
                }.commit()
            }
        }
        saved
    }

    fun savePreset(name: String) {
        if(working)return
        if(presetWriteBlocked) { message="preset_version";return }
        val snapshot=state
        val request=revision
        val preset=try { Presets.create(name,snapshot,customPresets) }
            catch(error:IllegalArgumentException) { message=error.message?:"preset_invalid";return }
        working=true
        viewModelScope.launch {
            try {
                validateFeasibility(snapshot,request)
                if(request==revision) {
                    val proposed=customPresets+preset
                    if(persistPresets(proposed)) {
                        customPresets=proposed
                        if(request==revision)selectedPreset=preset.id
                    } else message="settings_write"
                }
            } catch(_:GenerationCancelled) { /* Explicit config change, not invalid rules. */ }
              catch(error:GenerationException) { message=error.code }
            finally { working=false }
        }
    }

    fun updatePreset(id: String) {
        if(working)return
        if(presetWriteBlocked) { message="preset_version";return }
        val snapshot=state
        val request=revision
        val replacement=try { Presets.update(id,snapshot,customPresets) }
            catch(error:Exception) { message=errorCode(error);return }
        working=true
        viewModelScope.launch {
            try {
                validateFeasibility(snapshot,request)
                if(snapshot.mode==PasswordMode.HUMAN && snapshot.wordlist.isNotEmpty()) {
                    withContext(Dispatchers.IO) { readWords(Uri.parse(snapshot.wordlist)) }
                }
                if(request==revision) {
                    val proposed=customPresets.map { if(it.id==id) replacement else it }
                    if(persistPresets(proposed)) customPresets=proposed else message="settings_write"
                }
            } catch(error:Exception) {
                if(error is CancellationException)throw error
                if(error !is GenerationCancelled && request==revision)message=errorCode(error)
            } finally { working=false }
        }
    }

    fun renamePreset(id: String, name: String) {
        if(working)return
        if(presetWriteBlocked) { message="preset_version";return }
        val replacement=try { Presets.rename(id,name,customPresets) }
            catch(error:IllegalArgumentException) { message=error.message?:"preset_invalid";return }
        val proposed=customPresets.map { if(it.id==id) replacement else it }
        working=true
        viewModelScope.launch {
            try {
                if(persistPresets(proposed)) customPresets=proposed else message="settings_write"
            } finally { working=false }
        }
    }

    fun deletePreset(id: String) {
        if(working || customPresets.none { it.id==id })return
        if(presetWriteBlocked) { message="preset_version";return }
        val proposed=customPresets.filterNot { it.id==id }
        working=true
        viewModelScope.launch {
            try {
                if(persistPresets(proposed)) {
                    customPresets=proposed
                    if(selectedPreset==id)selectedPreset=""
                } else message="settings_write"
            } finally { working=false }
        }
    }

    fun applyPreset(id: String) {
        if (working) return
        val preset = presets.find { it.id == id } ?: return
        val snapshot = state
        val requestRevision = revision
        working = true
        viewModelScope.launch {
            try {
                val next = Presets.apply(snapshot, preset)
                validateFeasibility(next,requestRevision)
                if (next.mode == PasswordMode.HUMAN && next.wordlist.isNotEmpty()) {
                    withContext(Dispatchers.IO) { readWords(Uri.parse(next.wordlist)) }
                }
                if (requestRevision == revision) {
                    update { next.copy(language = it.language, theme = it.theme, autoCopy = it.autoCopy, transcription = it.transcription) }
                    revision++ // Also invalidate pending work when reapplying an identical preset.
                    selectedPreset = id
                }
            } catch (error: Exception) {
                if (error is CancellationException) throw error
                if (error !is GenerationCancelled && requestRevision == revision) {
                    if(snapshot.mode==PasswordMode.MANAGER && snapshot.advanced.enabled) validationMessage=errorCode(error)
                    else message=errorCode(error)
                }
            } finally { working = false }
        }
    }

    private fun readAdvanced():AdvancedRules {
        if(!preferences.contains("advanced_rules_v1"))return AdvancedRules()
        return try {
            val raw=preferences.all["advanced_rules_v1"] as? String ?: throw IllegalArgumentException()
            Presets.decodeRules(raw)
        } catch(_:Exception) { advancedReadError=true;AdvancedRules() }
    }

    private fun readPreferences(): UiState {
        val values = preferences.all
        fun number(key: String, default: Int, range: IntRange) = (values[key] as? Int)?.takeIf { it in range } ?: default
        fun bool(key: String, default: Boolean = true) = values[key] as? Boolean ?: default
        fun choice(key: String, default: String, options: List<String>) = (values[key] as? String)?.takeIf { it in options } ?: default
        return UiState(
            advanced = readAdvanced(),
            excludeSimilar = bool("excludeSimilar", false), transcription = bool("transcription", false),
            mode = if (values["mode"] == "human") PasswordMode.HUMAN else PasswordMode.MANAGER,
            length = number("length", 20, 8..64), words = number("words", 3, 2..8),
            separator = choice("separator", "-", PasswordGenerator.SEPARATORS + "Random"),
            uppercase = bool("uppercase"), lowercase = bool("lowercase"),
            managerNumbers = bool("managerNumbers"), managerSpecial = bool("managerSpecial"),
            humanNumbers = bool("humanNumbers"), humanSpecial = bool("humanSpecial"),
            language = choice("language", "system", listOf("system", "en", "pl")),
            theme = choice("theme", "system", listOf("system", "dark", "light")),
            autoCopy = bool("autoCopy", false), wordlist = values["wordlist"] as? String ?: "",
            wordlistName = values["wordlistName"] as? String ?: "",
        )
    }

    fun update(transform: (UiState) -> UiState) {
        val next = transform(state)
        if (configFor(next) != configFor(state) || next.advanced != state.advanced || next.wordlist != state.wordlist) {
            revision++
            if(customPresets.none { it.id==selectedPreset }) selectedPreset = ""
            validationMessage = null
        }
        state = if (next.mode != state.mode) next.copy(password = "") else next
        preferences.edit().apply {
            putBoolean("excludeSimilar", state.excludeSimilar); putBoolean("transcription", state.transcription)
            val storedRules=runCatching { Presets.jsonObject(state.advanced.toData()).toString() }.getOrElse {
                if(!state.advanced.enabled) runCatching {
                    val previous=(preferences.all["advanced_rules_v1"] as? String)?.let(Presets::decodeRules) ?: AdvancedRules()
                    Presets.jsonObject(previous.copy(enabled=false).toData()).toString()
                }.getOrNull() else null
            }
            storedRules?.let { putString("advanced_rules_v1",it) }
            putString("mode", if (state.mode == PasswordMode.HUMAN) "human" else "manager")
            putInt("length", state.length); putInt("words", state.words); putString("separator", state.separator)
            putBoolean("uppercase", state.uppercase); putBoolean("lowercase", state.lowercase)
            putBoolean("managerNumbers", state.managerNumbers); putBoolean("managerSpecial", state.managerSpecial)
            putBoolean("humanNumbers", state.humanNumbers); putBoolean("humanSpecial", state.humanSpecial)
            putString("language", state.language); putString("theme", state.theme); putBoolean("autoCopy", state.autoCopy)
            putString("wordlist", state.wordlist); putString("wordlistName", state.wordlistName)
        }.apply()
        // apply updates the in-memory preferences immediately. A serialized disk
        // barrier checks the actual write result without blocking the UI thread.
        viewModelScope.launch {
            settingsWriteLock.withLock {
                val saved=withContext(Dispatchers.IO) {
                    try { preferences.edit().commit() } catch(_:RuntimeException) { false }
                }
                if(!saved) message="settings_write"
            }
        }
        if(state.mode==PasswordMode.MANAGER && state.advanced.enabled) {
            try { compileRules(configFor(state)) }
            catch(error:GenerationException) { validationMessage=error.code }
        }
    }

    fun clearMessage() { message = null }
    fun useBuiltIn() { update { it.copy(wordlist = "", wordlistName = "") } }

    private fun readWords(uri: Uri): List<String> {
        val decoder = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
        val stream = getApplication<Application>().contentResolver.openInputStream(uri)
            ?: throw GenerationException("wordlist_read", "Cannot read word list")
        val words = InputStreamReader(stream, decoder).buffered().use { reader ->
            reader.lineSequence().map { it.trim() }.filter { it.isNotEmpty() }.toList()
        }
        if (words.isEmpty()) throw GenerationException("empty_words", "Word list is empty")
        return words
    }

    fun chooseWordlist(uri: Uri) {
        if (working) return
        val requestRevision = revision
        working = true
        viewModelScope.launch {
            try {
                val resolver = getApplication<Application>().contentResolver
                val result = withContext(Dispatchers.IO) {
                    val words = readWords(uri)
                    val name = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
                        if (it.moveToFirst()) it.getString(0) else null
                    } ?: uri.lastPathSegment.orEmpty()
                    words to name
                }
                resolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                if (requestRevision == revision) update { it.copy(wordlist = uri.toString(), wordlistName = result.second) }
            } catch (error: Exception) {
                if (error is CancellationException) throw error
                if (error !is GenerationCancelled && requestRevision == revision) {
                    message=errorCode(error)
                }
            }
            finally { working = false }
        }
    }

    fun generate() {
        if (working) return
        val requestRevision = revision
        val snapshot = state
        working = true
        viewModelScope.launch {
            try {
                var single=false
                val password = withContext(Dispatchers.Default) {
                    val words = if (snapshot.mode == PasswordMode.HUMAN) if (snapshot.wordlist.isNotEmpty()) readWords(Uri.parse(snapshot.wordlist)) else getApplication<Application>().assets.open("words.txt")
                        .bufferedReader(Charsets.UTF_8).use { it.lineSequence().map(String::trim).filter(String::isNotEmpty).toList() } else emptyList()
                    if(snapshot.mode==PasswordMode.MANAGER && snapshot.advanced.enabled) {
                        CompletionCounter(compileRules(configFor(snapshot))) { requestRevision!=revision }.use { counter ->
                            val total=counter.total()
                            ruleCheck(total.signum()>0,"no_valid_password")
                            single=total==java.math.BigInteger.ONE
                            counter.unrank(secureBelow(total,SecureRandom()))
                        }
                    } else generator.generate(PasswordConfig(snapshot.mode, snapshot.length, snapshot.uppercase, snapshot.lowercase,
                        if (snapshot.mode == PasswordMode.HUMAN) snapshot.humanNumbers else snapshot.managerNumbers,
                        if (snapshot.mode == PasswordMode.HUMAN) snapshot.humanSpecial else snapshot.managerSpecial,
                        snapshot.words, snapshot.separator, snapshot.excludeSimilar), words)
                }
                if (requestRevision == revision) {
                    state = state.copy(password = password)
                    if (state.autoCopy) copy()
                    validationMessage=if(single) "single_result" else null
                }
            } catch (error: Exception) {
                if (error is CancellationException) throw error
                if (error !is GenerationCancelled && requestRevision == revision) {
                    if(snapshot.mode==PasswordMode.MANAGER && snapshot.advanced.enabled) validationMessage=errorCode(error)
                    else message=errorCode(error)
                }
            }
            finally { working = false }
        }
    }

    override fun onCleared() { revision++; super.onCleared() }

    fun copy() {
        if (state.password.isEmpty()) return
        val clip = ClipData.newPlainText("Password Generator", state.password)
        if (Build.VERSION.SDK_INT >= 33) clip.description.extras = PersistableBundle().apply {
            putBoolean(ClipDescription.EXTRA_IS_SENSITIVE, true)
        }
        (getApplication<Application>().getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(clip)
        message = "copied"
    }

    private fun errorCode(error: Exception) = when (error) {
        is GenerationException -> error.code
        is java.nio.charset.CharacterCodingException -> "wordlist_encoding"
        is java.io.FileNotFoundException -> "wordlist_missing"
        is java.io.IOException, is SecurityException -> "wordlist_read"
        else -> "unknown_error"
    }
}
