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
    private var customWords: List<String>? = null
    var state by mutableStateOf(readPreferences())
        private set
    var message by mutableStateOf<String?>(null)
        private set
    var working by mutableStateOf(false)
        private set

    init {
        if (state.wordlist.isNotEmpty()) {
            working = true
            viewModelScope.launch {
                try {
                    customWords = withContext(Dispatchers.IO) { readWords(Uri.parse(state.wordlist)) }
                } catch (error: Exception) {
                    if (error is CancellationException) throw error
                    update { it.copy(wordlist = "", wordlistName = "") }
                    message = "wordlist_restored"
                } finally { working = false }
            }
        }
    }

    private fun readPreferences(): UiState {
        val values = preferences.all
        fun number(key: String, default: Int, range: IntRange) = (values[key] as? Int)?.takeIf { it in range } ?: default
        fun bool(key: String, default: Boolean = true) = values[key] as? Boolean ?: default
        fun choice(key: String, default: String, options: List<String>) = (values[key] as? String)?.takeIf { it in options } ?: default
        return UiState(
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
        state = transform(state)
        preferences.edit().apply {
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
    fun useBuiltIn() { customWords = null; update { it.copy(wordlist = "", wordlistName = "") } }

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
                customWords = result.first
                update { it.copy(wordlist = uri.toString(), wordlistName = result.second) }
            } catch (error: Exception) {
                if (error is CancellationException) throw error
                message = errorCode(error)
            }
            finally { working = false }
        }
    }

    fun generate() {
        val snapshot = state
        working = true
        viewModelScope.launch {
            try {
                val password = withContext(Dispatchers.IO) {
                    val words = if (snapshot.mode == PasswordMode.HUMAN) customWords ?: getApplication<Application>().assets.open("words.txt")
                        .bufferedReader(Charsets.UTF_8).use { it.lineSequence().map(String::trim).filter(String::isNotEmpty).toList() } else emptyList()
                    generator.generate(PasswordConfig(snapshot.mode, snapshot.length, snapshot.uppercase, snapshot.lowercase,
                        if (snapshot.mode == PasswordMode.HUMAN) snapshot.humanNumbers else snapshot.managerNumbers,
                        if (snapshot.mode == PasswordMode.HUMAN) snapshot.humanSpecial else snapshot.managerSpecial,
                        snapshot.words, snapshot.separator), words)
                }
                state = state.copy(password = password)
                if (state.autoCopy) copy()
            } catch (error: Exception) {
                if (error is CancellationException) throw error
                message = errorCode(error)
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
