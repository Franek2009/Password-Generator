package pl.franek.passwordgenerator

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class PresetsTest {
    @Test fun editsOfMigratedPresetsRetainVersionTwoAndIdentity() {
        val raw=javaClass.getResource("/legacy_presets_v1.json")!!.readText()
        val presets=Presets.decode(raw,1).first
        val first=presets.first()
        val updated=Presets.update(first.id,UiState(length=32),presets)
        val renamed=Presets.rename(first.id,"Renamed legacy",listOf(updated)+presets.drop(1))
        val encoded=Presets.encode(listOf(renamed)+presets.drop(1))
        assertEquals(2,JSONObject(encoded).getInt("version"))
        assertEquals(renamed,Presets.decode(encoded).first.first())
        assertEquals(first.id,renamed.id)
        assertEquals(32,renamed.config["length"])
    }

    @Test fun editsPreserveIdentityOrderAndOnlyWhitelistedSettings() {
        val first=Presets.create("First",UiState(),emptyList())
        val second=Presets.create("Second",UiState(),listOf(first))
        val existing=listOf(first,second)
        val updated=Presets.update(first.id,UiState(length=32,excludeSimilar=true,password="memory-only"),existing)
        val renamed=Presets.rename(first.id,"  FIRST renamed  ",listOf(updated,second))
        assertEquals(first.id,renamed.id)
        assertEquals("FIRST renamed",renamed.name)
        assertEquals(updated.config,renamed.config)
        assertEquals(32,renamed.config["length"])
        assertEquals(listOf(renamed,second) to false,Presets.decode(Presets.encode(listOf(renamed,second))))
        assertFalse(Presets.encode(listOf(renamed)).contains("memory-only"))
        assertEquals(renamed,Presets.rename(renamed.id,renamed.name,listOf(renamed,second)))
        for(id in listOf("missing","standard","strong","phrase")) {
            try { Presets.update(id,UiState(),existing+Presets.builtins());fail() } catch(_:IllegalArgumentException) { }
            try { Presets.rename(id,"Other",existing+Presets.builtins());fail() } catch(_:IllegalArgumentException) { }
        }
        for(name in listOf("SECOND","Standard","","bad\nname")) {
            try { Presets.rename(first.id,name,existing);fail() } catch(_:IllegalArgumentException) { }
        }
        try { Presets.update(first.id,UiState(length=65),existing);fail() } catch(_:IllegalArgumentException) { }
        assertEquals(first,existing[0])
    }

    @Test fun sharedContractAndActiveModeRestoration() {
        val root = JSONObject(javaClass.getResource("/preset_contract.json")!!.readText())
        assertEquals(root.getString("similar_characters"), PasswordGenerator.SIMILAR_CHARACTERS)
        val fixture = root.getJSONArray("builtins")
        Presets.builtins().forEachIndexed { index, p ->
            val expected = fixture.getJSONObject(index)
            assertEquals(expected.getString("id"), p.id)
            val config = expected.getJSONObject("config")
            assertTrue(config.similar(Presets.jsonObject(p.config)))
        }
        val restored = Presets.apply(UiState(length = 48, password = "memory-only", autoCopy = false), Presets.builtins()[2])
        assertEquals(PasswordMode.HUMAN, restored.mode)
        assertEquals(5, restored.words)
        assertEquals(48, restored.length)
        assertEquals("", restored.password)
        assertFalse(restored.humanNumbers)
        assertFalse(restored.humanSpecial)
    }
    @Test fun roundtripValidationAndNames() {
        val p = Presets.create(" Travel ", UiState(excludeSimilar = true, password = "memory-only"), emptyList())
        val raw = Presets.encode(listOf(p))
        assertFalse(raw.contains("memory-only"))
        assertFalse(raw.contains("password"))
        assertEquals(listOf(p) to false, Presets.decode(raw))
        for (name in listOf("TRAVEL", "Standard", " ", "bad\nname")) {
            try { Presets.create(name, UiState(), listOf(p)); fail("Must reject name") } catch (_: IllegalArgumentException) { }
        }
        assertEquals(emptyList<Preset>() to false, Presets.decode(Presets.encode(emptyList())))
    }
    @Test fun corruptedRecordsDoNotHideValidNeighbors() {
        for (raw in listOf("null", "[]", "{", "{\"version\":true,\"presets\":[]}")) {
            assertTrue(Presets.decode(raw).second)
        }
        val p = Presets.create("Valid", UiState(), emptyList())
        val root = JSONObject(Presets.encode(listOf(p)))
        root.getJSONArray("presets").put(JSONObject().put("id", "custom-00000000-0000-4000-8000-000000000000").put("name", "Bad").put("config", Presets.jsonObject(p.config).put("password", "secret")))
        assertEquals(listOf(p) to true, Presets.decode(root.toString()))
        for (bad in listOf(p.config + ("length" to true), p.config + ("length" to 65), p.config + ("numbers" to "true"))) {
            try { Presets.validate(bad); fail("Must reject invalid types") } catch (_: IllegalArgumentException) { }
        }
    }
    @Test fun exclusionPreservesAllSelectedGroups() {
        val generator = PasswordGenerator()
        val groups = listOf(PasswordGenerator.UPPERCASE, PasswordGenerator.LOWERCASE, PasswordGenerator.DIGITS, PasswordGenerator.SPECIAL)
        for (mask in 1..15) repeat(20) {
            val flags = (0..3).map { mask and (1 shl it) != 0 }
            val result = generator.generate(PasswordConfig(length = 64, uppercase = flags[0], lowercase = flags[1], numbers = flags[2], special = flags[3], excludeSimilar = true))
            assertEquals(64, result.length)
            assertFalse(result.any { it in PasswordGenerator.SIMILAR_CHARACTERS })
            groups.forEachIndexed { index, group -> if (flags[index]) assertTrue(result.any { it in group }) }
            assertTrue(result.all { char -> groups.withIndex().any { (i, group) -> flags[i] && char in group } })
        }
        assertEquals("Olive-Olive-Olive", generator.generate(PasswordConfig(mode = PasswordMode.HUMAN, numbers = false, special = false, excludeSimilar = true), listOf("olive")))
    }
    @Test fun legacyMigrationUsesDisabledRulesAndNewFormat() {
        val raw=javaClass.getResource("/legacy_presets_v1.json")!!.readText()
        val (presets,invalid)=Presets.decode(raw,1)
        assertFalse(invalid);assertEquals(2,presets.size)
        val restored=Presets.apply(UiState(),presets[0])
        assertFalse(restored.advanced.enabled)
        assertEquals(16,restored.length)
        val encoded=Presets.encode(presets)
        assertEquals(2,JSONObject(encoded).getInt("version"))
        assertEquals(presets to false,Presets.decode(encoded))
        assertTrue(Presets.decode(raw,2).second)
    }

    @Test fun schemaAndNestingGuardsPreserveLiteralAscii() {
        try { Presets.validate(Presets.builtins()[0].config,3);fail() }
        catch(error:IllegalArgumentException) { assertEquals("preset_version",error.message) }
        val future=JSONObject(Presets.encode(emptyList())).put("version",2147483648L).toString()
        assertTrue(Presets.unsupportedVersion(future))
        assertTrue(Presets.decode(future).second)
        val deep="{\"version\":2,\"presets\":"+"[".repeat(30)+"]".repeat(30)+"}"
        assertTrue(Presets.decode(deep).second)
        val rules=AdvancedRules(customAlphabet="{}[]".repeat(30))
        val raw=Presets.jsonObject(rules.toData()).toString()
        assertEquals(rules.toData(),Presets.decodeRules(raw).toData())
    }

}
