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
import java.io.InputStreamReader
import java.nio.charset.CodingErrorAction
import java.util.Locale
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
    private var revision = 0L
    private val storedPresets = preferences.all["presets"]
    private val decodedPresets = when (val raw = storedPresets) {
        null -> emptyList<Preset>() to false
        is String -> Presets.decode(raw)
        else -> emptyList<Preset>() to true
    }
    var customPresets by mutableStateOf(decodedPresets.first)
        private set
    var selectedPreset by mutableStateOf("")
        private set
    val presets get() = Presets.builtins() + customPresets
    var state by mutableStateOf(readPreferences())
        private set
    var message by mutableStateOf<String?>(null)
        private set
    var working by mutableStateOf(false)
        private set

    init {
        if (decodedPresets.second) message = "preset_invalid"
    }

    fun savePreset(name: String) {
        try {
            val preset = Presets.create(name, state, customPresets)
            customPresets = customPresets + preset
            selectedPreset = preset.id
            writePresets()
        } catch (error: IllegalArgumentException) { message = error.message ?: "preset_invalid" }
    }

    fun deletePreset(id: String) {
        if (customPresets.none { it.id == id }) return
        customPresets = customPresets.filterNot { it.id == id }
        if (selectedPreset == id) selectedPreset = ""
        writePresets()
    }

    private fun writePresets() { preferences.edit().putString("presets", Presets.encode(customPresets)).apply() }

    fun applyPreset(id: String) {
        if (working) return
        val preset = presets.find { it.id == id } ?: return
        val snapshot = state
        val requestRevision = revision
        working = true
        viewModelScope.launch {
            try {
                val next = Presets.apply(snapshot, preset)
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
                if (requestRevision == revision) message = errorCode(error)
            } finally { working = false }
        }
    }

    private fun readPreferences(): UiState {
        val values = preferences.all
        fun number(key: String, default: Int, range: IntRange) = (values[key] as? Int)?.takeIf { it in range } ?: default
        fun bool(key: String, default: Boolean = true) = values[key] as? Boolean ?: default
        fun choice(key: String, default: String, options: List<String>) = (values[key] as? String)?.takeIf { it in options } ?: default
        return UiState(
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
        if (Presets.parameters(next) != Presets.parameters(state)) {
            revision++
            selectedPreset = ""
        }
        state = if (next.mode != state.mode) next.copy(password = "") else next
        preferences.edit().apply {
            putBoolean("excludeSimilar", state.excludeSimilar); putBoolean("transcription", state.transcription)
            putString("mode", if (state.mode == PasswordMode.HUMAN) "human" else "manager")
            putInt("length", state.length); putInt("words", state.words); putString("separator", state.separator)
            putBoolean("uppercase", state.uppercase); putBoolean("lowercase", state.lowercase)
            putBoolean("managerNumbers", state.managerNumbers); putBoolean("managerSpecial", state.managerSpecial)
            putBoolean("humanNumbers", state.humanNumbers); putBoolean("humanSpecial", state.humanSpecial)
            putString("language", state.language); putString("theme", state.theme); putBoolean("autoCopy", state.autoCopy)
            putString("wordlist", state.wordlist); putString("wordlistName", state.wordlistName)
        }.apply()
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
                if (requestRevision == revision) message = errorCode(error)
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
                val password = withContext(Dispatchers.IO) {
                    val words = if (snapshot.mode == PasswordMode.HUMAN) if (snapshot.wordlist.isNotEmpty()) readWords(Uri.parse(snapshot.wordlist)) else getApplication<Application>().assets.open("words.txt")
                        .bufferedReader(Charsets.UTF_8).use { it.lineSequence().map(String::trim).filter(String::isNotEmpty).toList() } else emptyList()
                    generator.generate(PasswordConfig(snapshot.mode, snapshot.length, snapshot.uppercase, snapshot.lowercase,
                        if (snapshot.mode == PasswordMode.HUMAN) snapshot.humanNumbers else snapshot.managerNumbers,
                        if (snapshot.mode == PasswordMode.HUMAN) snapshot.humanSpecial else snapshot.managerSpecial,
                        snapshot.words, snapshot.separator, snapshot.excludeSimilar), words)
                }
                if (requestRevision == revision) {
                    state = state.copy(password = password)
                    if (state.autoCopy) copy()
                }
            } catch (error: Exception) {
                if (error is CancellationException) throw error
                if (requestRevision == revision) message = errorCode(error)
            }
            finally { working = false }
        }
    }

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
