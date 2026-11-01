package pl.franek.passwordgenerator

import java.text.Normalizer
import java.util.Locale
import java.util.UUID
import org.json.JSONArray
import org.json.JSONObject

/** Active-mode generator parameters only; never serialize UiState. */
data class Preset(val id: String, val name: String, val config: Map<String, Any>, val builtin: Boolean = false)

object Presets {
    private val customId = Regex("custom-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
    private val reserved = setOf("STANDARD", "STRONG", "MOCNE", "PHRASE", "FRAZA")
    fun name(raw: String): String {
        val value = Normalizer.normalize(raw, Normalizer.Form.NFKC).trim()
        require(value.codePointCount(0, value.length) in 1..64 && value.codePoints().noneMatch {
            Character.getType(it) in listOf(Character.CONTROL.toInt(), Character.FORMAT.toInt(), Character.SURROGATE.toInt(), Character.PRIVATE_USE.toInt(), Character.UNASSIGNED.toInt())
        }) { "preset_invalid" }
        return value
    }
    private fun key(value: String) = value.uppercase(Locale.ROOT)
    fun parameters(state: UiState): Map<String, Any> = if (state.mode == PasswordMode.MANAGER) mapOf(
        "mode" to "manager", "length" to state.length, "uppercase" to state.uppercase,
        "lowercase" to state.lowercase, "numbers" to state.managerNumbers, "special" to state.managerSpecial,
        "exclude_similar" to state.excludeSimilar,
    ) else mapOf("mode" to "human", "words" to state.words, "separator" to state.separator,
        "numbers" to state.humanNumbers, "special" to state.humanSpecial, "wordlist" to state.wordlist)

    fun validate(data: Map<String, Any>): Map<String, Any> {
        val manager = data["mode"] == "manager"
        require(manager || data["mode"] == "human") { "preset_invalid" }
        val keys = if (manager) setOf("mode", "length", "uppercase", "lowercase", "numbers", "special", "exclude_similar")
            else setOf("mode", "words", "separator", "numbers", "special", "wordlist")
        require(data.keys == keys) { "preset_invalid" }
        val bools = if (manager) listOf("uppercase", "lowercase", "numbers", "special", "exclude_similar") else listOf("numbers", "special")
        require(bools.all { data[it] is Boolean }) { "preset_invalid" }
        if (manager) {
            require(data["length"] is Int && data["length"] as Int in 8..64) { "preset_invalid" }
            require(listOf("uppercase", "lowercase", "numbers", "special").any { data[it] == true }) { "preset_invalid" }
        } else {
            require(data["words"] is Int && data["words"] as Int in 2..8) { "preset_invalid" }
            require(data["separator"] in PasswordGenerator.SEPARATORS + "Random") { "preset_invalid" }
            require(data["wordlist"] is String && '\u0000' !in data["wordlist"] as String) { "preset_invalid" }
        }
        return data.toMap()
    }
    fun builtins() = listOf(
        Preset("standard", "preset_standard", parameters(UiState(length = 16)), true),
        Preset("strong", "preset_strong", parameters(UiState(length = 24)), true),
        Preset("phrase", "preset_phrase", parameters(UiState(mode = PasswordMode.HUMAN, words = 5, humanNumbers = false, humanSpecial = false)), true),
    )
    fun create(raw: String, state: UiState, existing: List<Preset>): Preset {
        val name = name(raw)
        require(key(name) !in reserved && existing.none { key(it.name) == key(name) }) { "preset_duplicate" }
        return Preset("custom-${UUID.randomUUID()}", name, validate(parameters(state)))
    }
    fun apply(state: UiState, preset: Preset): UiState {
        val data = validate(preset.config)
        return if (data["mode"] == "manager") state.copy(mode = PasswordMode.MANAGER, length = data["length"] as Int,
            uppercase = data["uppercase"] as Boolean, lowercase = data["lowercase"] as Boolean,
            managerNumbers = data["numbers"] as Boolean, managerSpecial = data["special"] as Boolean,
            excludeSimilar = data["exclude_similar"] as Boolean, password = "")
        else state.copy(mode = PasswordMode.HUMAN, words = data["words"] as Int, separator = data["separator"] as String,
            humanNumbers = data["numbers"] as Boolean, humanSpecial = data["special"] as Boolean,
            wordlist = data["wordlist"] as String, wordlistName = (data["wordlist"] as String).substringAfterLast('/'), password = "")
    }
    fun encode(presets: List<Preset>): String = JSONObject().put("version", 1).put("presets", JSONArray().apply {
        presets.filterNot { it.builtin }.forEach { p -> put(JSONObject().put("id", p.id).put("name", p.name).put("config", JSONObject(validate(p.config)))) }
    }).toString()
    fun decode(raw: String): Pair<List<Preset>, Boolean> {
        if (raw.isEmpty()) return emptyList<Preset>() to false
        val result = mutableListOf<Preset>()
        var invalid = false
        try {
            val root = JSONObject(raw)
            require(root.keys().asSequence().toSet() == setOf("version", "presets") && root.get("version") is Int && root.getInt("version") == 1)
            val array = root.getJSONArray("presets")
            for (i in 0 until array.length()) {
                try {
                    val item = array.getJSONObject(i)
                    require(item.keys().asSequence().toSet() == setOf("id", "name", "config"))
                    val id = item.get("id") as String
                    val name = name(item.get("name") as String)
                    require(customId.matches(id) && result.none { it.id == id })
                    require(key(name) !in reserved && result.none { key(it.name) == key(name) })
                    val config = item.getJSONObject("config")
                    result += Preset(id, name, validate(config.keys().asSequence().associateWith { config.get(it) }))
                } catch (_: Exception) { invalid = true }
            }
        } catch (_: Exception) { invalid = true }
        return result to invalid
    }
}
