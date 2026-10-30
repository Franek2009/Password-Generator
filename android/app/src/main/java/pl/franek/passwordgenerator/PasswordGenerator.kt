package pl.franek.passwordgenerator

import java.security.SecureRandom

enum class PasswordMode { MANAGER, HUMAN }

data class PasswordConfig(
    val mode: PasswordMode = PasswordMode.MANAGER,
    val length: Int = 20,
    val uppercase: Boolean = true,
    val lowercase: Boolean = true,
    val numbers: Boolean = true,
    val special: Boolean = true,
    val words: Int = 3,
    val separator: String = "-",
)

class PasswordGenerator(private val random: SecureRandom = SecureRandom()) {
    companion object {
        const val LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
        const val UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        const val DIGITS = "0123456789"
        const val SPECIAL = "!\"#\$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        val SEPARATORS = listOf("-", "_", ".", " ", "/", "|")
    }

    fun generate(config: PasswordConfig, wordList: List<String> = emptyList()): String =
        when (config.mode) {
            PasswordMode.MANAGER -> generateManager(config)
            PasswordMode.HUMAN -> generateHuman(config, wordList)
        }

    fun generateManager(config: PasswordConfig): String {
        require(config.length >= 1) { "Długość hasła musi wynosić co najmniej 1." }
        val sets = buildList {
            if (config.lowercase) add(LOWERCASE)
            if (config.uppercase) add(UPPERCASE)
            if (config.numbers) add(DIGITS)
            if (config.special) add(SPECIAL)
        }
        require(sets.isNotEmpty()) { "Wybierz co najmniej jeden zestaw znaków." }
        require(config.length >= sets.size) {
            "Hasło jest za krótkie dla wybranych zestawów znaków."
        }

        val characters = sets.map { it.randomCharacter() }.toMutableList()
        val allCharacters = sets.joinToString("")
        repeat(config.length - characters.size) {
            characters += allCharacters.randomCharacter()
        }
        characters.secureShuffle()
        return characters.joinToString("")
    }

    fun generateHuman(config: PasswordConfig, wordList: List<String>): String {
        require(config.words >= 1) { "Liczba słów musi wynosić co najmniej 1." }
        require(wordList.isNotEmpty()) { "Lista słów nie może być pusta." }
        require(config.separator == "Random" || config.separator in SEPARATORS) {
            "Nieobsługiwany separator."
        }

        val separator = if (config.separator == "Random") {
            SEPARATORS[random.nextInt(SEPARATORS.size)]
        } else {
            config.separator
        }
        val selected = selectWords(wordList, config.words)
            .map { word -> word.replaceFirstChar { it.uppercase() } }
            .toMutableList()
        if (config.numbers) selected += random.nextInt(100).toString()
        if (config.special) {
            val available = SPECIAL.filterNot { separator.contains(it) }
            require(available.isNotEmpty()) { "Brak dostępnych znaków specjalnych." }
            selected += available.randomCharacter().toString()
        }
        selected.secureShuffle()
        return selected.joinToString(separator)
    }

    private fun selectWords(words: List<String>, count: Int): MutableList<String> {
        val selected = words.toMutableList().also { it.secureShuffle() }.take(count).toMutableList()
        repeat(count - selected.size) { selected += words[random.nextInt(words.size)] }
        selected.secureShuffle()
        return selected
    }

    private fun String.randomCharacter(): Char = this[random.nextInt(length)]

    private fun <T> MutableList<T>.secureShuffle() {
        for (index in lastIndex downTo 1) {
            val target = random.nextInt(index + 1)
            val temporary = this[index]
            this[index] = this[target]
            this[target] = temporary
        }
    }
}
