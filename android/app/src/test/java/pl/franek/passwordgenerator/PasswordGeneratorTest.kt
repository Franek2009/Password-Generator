package pl.franek.passwordgenerator

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

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
}
