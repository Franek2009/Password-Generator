package pl.franek.passwordgenerator

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.json.JSONArray
import java.util.Locale

class PasswordGeneratorTest {
    private val generator = PasswordGenerator()

    @Test
    fun managerPasswordHasRequestedLengthAndEverySelectedSet() {
        val password = generator.generateManager(PasswordConfig(length = 32))
        assertEquals(32, password.length)
        assertTrue(password.any { it in PasswordGenerator.LOWERCASE })
        assertTrue(password.any { it in PasswordGenerator.UPPERCASE })
        assertTrue(password.any { it in PasswordGenerator.DIGITS })
        assertTrue(password.any { it in PasswordGenerator.SPECIAL })
    }

    @Test(expected = IllegalArgumentException::class)
    fun managerRejectsNoCharacterSets() {
        generator.generateManager(PasswordConfig(uppercase = false, lowercase = false, numbers = false, special = false))
    }

    @Test
    fun humanPasswordUsesWordsAndSeparator() {
        val password = generator.generateHuman(
            PasswordConfig(mode = PasswordMode.HUMAN, words = 3, separator = "_", numbers = false, special = false),
            listOf("kot", "pies", "zamek"),
        )
        assertEquals(3, password.split("_").size)
    }

    @Test(expected = IllegalArgumentException::class)
    fun managerRejectsLengthTooShortForSelectedSets() {
        generator.generateManager(PasswordConfig(length = 3))
    }

    @Test(expected = IllegalArgumentException::class)
    fun humanRejectsEmptyWordList() {
        generator.generateHuman(PasswordConfig(mode = PasswordMode.HUMAN), emptyList())
    }

    @Test
    fun humanUsesEveryWordBeforeRepeatingWhenListIsShort() {
        val password = generator.generateHuman(
            PasswordConfig(mode = PasswordMode.HUMAN, words = 5, separator = "_", numbers = false, special = false),
            listOf("kot", "pies"),
        )
        val words = password.split("_")
        assertEquals(5, words.size)
        assertTrue(words.containsAll(listOf("Kot", "Pies")))
        assertTrue(words.all { it in listOf("Kot", "Pies") })
    }

    @Test
    fun validationUsesStableTranslationIdentifiers() {
        try {
            generator.generateManager(PasswordConfig(uppercase = false, lowercase = false, numbers = false, special = false))
            throw AssertionError("Expected validation failure")
        } catch (error: GenerationException) {
            assertEquals("no_sets", error.code)
        }
    }
    @Test
    fun customWordCaseMatchesDesktopRegardlessOfLocaleAndExclusion() {
        val cases = JSONArray(javaClass.getResource("/word_case_contract.json")!!.readText())
        val previous = Locale.getDefault()
        try {
            Locale.setDefault(Locale.forLanguageTag("tr-TR"))
            for (excluded in listOf(false, true)) for (i in 0 until cases.length()) {
                val case = cases.getJSONObject(i)
                val result = generator.generateHuman(
                    PasswordConfig(mode = PasswordMode.HUMAN, words = 2, separator = "-",
                        numbers = false, special = false, excludeSimilar = excluded),
                    listOf(case.getString("input")),
                )
                assertEquals(List(2) { case.getString("expected") }.joinToString("-"), result)
            }
        } finally { Locale.setDefault(previous) }
    }

}
