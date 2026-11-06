package pl.franek.passwordgenerator

import java.text.Normalizer
import java.util.Locale
import java.util.UUID
import org.json.JSONArray
import org.json.JSONObject

data class Preset(val id: String, val name: String, val config: Map<String, Any?>, val builtin: Boolean = false)

object Presets {
    private val customId = Regex("custom-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
    private val reserved = setOf("STANDARD", "STRONG", "MOCNE", "PHRASE", "FRAZA")
    fun name(raw: String): String {
        val value = Normalizer.normalize(raw, Normalizer.Form.NFKC).trim()
        require(value.codePointCount(0,value.length) in 1..64 && value.codePoints().noneMatch {
            Character.getType(it) in listOf(Character.CONTROL.toInt(),Character.FORMAT.toInt(),Character.SURROGATE.toInt(),Character.PRIVATE_USE.toInt(),Character.UNASSIGNED.toInt())
        }) { "preset_invalid" }
        return value
    }
    private fun key(value: String) = value.uppercase(Locale.ROOT)
    internal fun effectiveRules(rules:AdvancedRules):AdvancedRules = if(rules.enabled) rules
        else try { rules.validateStructure();rules } catch(_:GenerationException) { AdvancedRules() }
    fun parameters(state: UiState): Map<String, Any?> = if(state.mode==PasswordMode.MANAGER) mapOf(
        "mode" to "manager", "length" to state.length, "uppercase" to state.uppercase, "lowercase" to state.lowercase,
        "numbers" to state.managerNumbers,"special" to state.managerSpecial,"exclude_similar" to state.excludeSimilar,
        "advanced" to effectiveRules(state.advanced).toData(),
    ) else mapOf("mode" to "human","words" to state.words,"separator" to state.separator,"numbers" to state.humanNumbers,
        "special" to state.humanSpecial,"wordlist" to state.wordlist)

    fun validate(data: Map<String,Any?>,version: Int=2): Map<String,Any?> {
        require(version in 1..2) { "preset_version" }
        val manager=data["mode"]=="manager"
        require(manager || data["mode"]=="human") { "preset_invalid" }
        val keys=if(manager) setOf("mode","length","uppercase","lowercase","numbers","special","exclude_similar") + if(version==2)setOf("advanced") else emptySet()
            else setOf("mode","words","separator","numbers","special","wordlist")
        require(data.keys==keys) { "preset_invalid" }
        val bools=if(manager)listOf("uppercase","lowercase","numbers","special","exclude_similar") else listOf("numbers","special")
        require(bools.all { data[it] is Boolean }) { "preset_invalid" }
        val result=data.toMutableMap()
        if(manager) {
            require(data["length"] is Int && data["length"] as Int in 8..64) { "preset_invalid" }
            require(listOf("uppercase","lowercase","numbers","special").any { data[it]==true }) { "preset_invalid" }
            @Suppress("UNCHECKED_CAST")
            val rules=if(version==1) AdvancedRules() else AdvancedRules.fromData(data["advanced"] as? Map<String,Any?> ?: throw IllegalArgumentException("preset_invalid"))
            if(rules.enabled) compileRules(PasswordConfig(length=data["length"] as Int,uppercase=data["uppercase"] as Boolean,
                lowercase=data["lowercase"] as Boolean,numbers=data["numbers"] as Boolean,special=data["special"] as Boolean,
                excludeSimilar=data["exclude_similar"] as Boolean,advanced=rules))
            result["advanced"]=rules.toData()
        } else {
            require(data["words"] is Int && data["words"] as Int in 2..8) { "preset_invalid" }
            require(data["separator"] in PasswordGenerator.SEPARATORS+"Random") { "preset_invalid" }
            require(data["wordlist"] is String && '\u0000' !in data["wordlist"] as String) { "preset_invalid" }
        }
        return result.toMap()
    }
    fun builtins() = listOf(
        Preset("standard","preset_standard",parameters(UiState(length=16)),true),
        Preset("strong","preset_strong",parameters(UiState(length=24)),true),
        Preset("phrase","preset_phrase",parameters(UiState(mode=PasswordMode.HUMAN,words=5,humanNumbers=false,humanSpecial=false)),true),
    )
    fun create(raw:String,state:UiState,existing:List<Preset>):Preset {
        val name=name(raw)
        require(key(name) !in reserved && existing.none { key(it.name)==key(name) }) { "preset_duplicate" }
        return Preset("custom-${UUID.randomUUID()}",name,validate(parameters(state)))
    }
    fun update(id:String,state:UiState,existing:List<Preset>):Preset {
        val preset=existing.singleOrNull { it.id==id && !it.builtin }
            ?: throw IllegalArgumentException("preset_invalid")
        return preset.copy(config=validate(parameters(state)))
    }
    fun rename(id:String,raw:String,existing:List<Preset>):Preset {
        val preset=existing.singleOrNull { it.id==id && !it.builtin }
            ?: throw IllegalArgumentException("preset_invalid")
        val name=name(raw)
        require(key(name) !in reserved && existing.none { it.id!=id && key(it.name)==key(name) }) { "preset_duplicate" }
        return preset.copy(name=name)
    }
    fun apply(state:UiState,preset:Preset):UiState {
        val data=validate(preset.config)
        @Suppress("UNCHECKED_CAST")
        return if(data["mode"]=="manager")state.copy(mode=PasswordMode.MANAGER,length=data["length"] as Int,uppercase=data["uppercase"] as Boolean,
            lowercase=data["lowercase"] as Boolean,managerNumbers=data["numbers"] as Boolean,managerSpecial=data["special"] as Boolean,
            excludeSimilar=data["exclude_similar"] as Boolean,advanced=AdvancedRules.fromData(data["advanced"] as Map<String,Any?>),password="")
        else state.copy(mode=PasswordMode.HUMAN,words=data["words"] as Int,separator=data["separator"] as String,
            humanNumbers=data["numbers"] as Boolean,humanSpecial=data["special"] as Boolean,wordlist=data["wordlist"] as String,
            wordlistName=(data["wordlist"] as String).substringAfterLast('/'),password="")
    }
    internal fun jsonObject(data: Map<String,Any?>):JSONObject = JSONObject().apply {
        data.forEach { (key,value) ->
            @Suppress("UNCHECKED_CAST")
            put(key,when(value) {
                null -> JSONObject.NULL
                is Map<*,*> -> jsonObject(value as Map<String,Any?>)
                else -> value
            })
        }
    }
    fun encode(presets:List<Preset>):String=JSONObject().put("version",2).put("presets",JSONArray().apply {
        presets.filterNot { it.builtin }.forEach { put(JSONObject().put("id",it.id).put("name",it.name).put("config",jsonObject(validate(it.config)))) }
    }).toString()

    private fun native(value:Any?):Any? = when(value) {
        JSONObject.NULL -> null
        is JSONObject -> value.keys().asSequence().associateWith { native(value.get(it)) }
        else -> value
    }
    internal fun readObject(raw:String):JSONObject {
        var depth=0;var quoted=false;var escaped=false
        for(char in raw) {
            if(quoted) {
                if(escaped) escaped=false
                else if(char=='\\') escaped=true
                else if(char=='"') quoted=false
            } else when(char) {
                '"' -> quoted=true
                '{','[' -> { depth++;require(depth<=16) { "preset_invalid" } }
                '}',']' -> depth--
            }
        }
        return JSONObject(raw)
    }
    internal fun decodeRules(raw:String):AdvancedRules {
        @Suppress("UNCHECKED_CAST")
        val data=native(readObject(raw)) as Map<String,Any?>
        return AdvancedRules.fromData(data)
    }
    fun unsupportedVersion(raw:String):Boolean=try {
        val version=readObject(raw).opt("version")
        version is Number && (version.toDouble() < 1 || version.toDouble() > 2)
    } catch(_:Exception) { false }
    fun decode(raw:String,version:Int=2):Pair<List<Preset>,Boolean> {
        if(raw.isEmpty() && version==1)return emptyList<Preset>() to false
        val result=mutableListOf<Preset>()
        var invalid=false
        try {
            val root=readObject(raw)
            require(root.keys().asSequence().toSet()==setOf("version","presets") && root.get("version") is Int && root.getInt("version")==version)
            val array=root.getJSONArray("presets")
            for(i in 0 until array.length()) {
                try {
                    val item = array.getJSONObject(i)
                    require(item.keys().asSequence().toSet() == setOf("id", "name", "config"))
                    val id = item.get("id") as String
                    val normalizedName = name(item.get("name") as String)
                    require(customId.matches(id) && result.none { it.id == id })
                    require(key(normalizedName) !in reserved && result.none { key(it.name) == key(normalizedName) })
                    @Suppress("UNCHECKED_CAST")
                    val config=native(item.getJSONObject("config")) as Map<String,Any?>
                    result += Preset(id, normalizedName, validate(config, version))
                } catch(_:Exception) { invalid=true }
            }
        } catch(_:Exception) { invalid=true }
        return result to invalid
    }
}
