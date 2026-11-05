package pl.franek.passwordgenerator

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.math.BigInteger
import java.security.SecureRandom

class AdvancedGenerationTest {
    private fun data(obj: JSONObject): Map<String, Any?> = obj.keys().asSequence().associateWith { key -> obj.get(key).let { if (it == JSONObject.NULL) null else it } }
    @Test fun sharedIndependentRankContract() {
        val cases=JSONArray(javaClass.getResource("/advanced_contract.json")!!.readText())
        for (i in 0 until cases.length()) {
            val case=cases.getJSONObject(i)
            val rules=AdvancedRules.fromData(data(case.getJSONObject("rules")))
            val expected=BigInteger(case.getString("count"))
            val compiled=try { compileRules(PasswordConfig(length=case.getInt("length"),advanced=rules)) }
                catch (error: GenerationException) { assertEquals(BigInteger.ZERO,expected);continue }
            CompletionCounter(compiled).use { counter ->
                assertEquals(expected,counter.total())
                val ranks=case.getJSONArray("ranks")
                for (j in 0 until ranks.length()) {
                    val example=ranks.getJSONObject(j)
                    assertEquals(example.getString("result"),counter.unrank(BigInteger(example.getString("rank"))))
                }
            }
        }
    }
    private fun category(c: Char): Int = when(c) { in 'A'..'Z' -> 0; in 'a'..'z' -> 1; in '0'..'9' -> 2; else -> 3 }
    private fun matches(c: Char,t: CharacterType): Boolean = t==CharacterType.ANY || when(t) {
        CharacterType.LETTER -> category(c) in 0..1; CharacterType.UPPER -> category(c)==0
        CharacterType.LOWER -> category(c)==1; CharacterType.DIGIT -> category(c)==2; CharacterType.SYMBOL -> category(c)==3; else -> true
    }
    private fun accepts(s: String,r: AdvancedRules): Boolean {
        if ((0..3).any { i -> s.count { category(it)==i }<r.minima[i] }) return false
        if (!matches(s.first(),r.firstType) || !matches(s.last(),r.lastType)) return false
        var run=0;var previous: Char?=null
        for (c in s) { run=if(c==previous)run+1 else 1;previous=c;if(r.maxIdenticalRun!=null && run>r.maxIdenticalRun)return false }
        return true
    }
    private fun strings(alphabet: String,n: Int): List<String> = if(n==0)listOf("") else strings(alphabet,n-1).flatMap { prefix -> alphabet.map { prefix+it } }
    @Test fun exhaustiveSmallLanguagesAndEveryRank() {
        for (alphabet in listOf("a","ab","a1","aA1!")) for (n in 1..4) {
            val candidates=strings(alphabet,n)
            for (first in CharacterType.entries) for (last in CharacterType.entries) for(limit in listOf(null,1,2)) {
                val r=AdvancedRules(enabled=true,customAlphabetEnabled=true,customAlphabet=alphabet,firstType=first,lastType=last,maxIdenticalRun=limit)
                val expected=candidates.filter { accepts(it,r) }.sorted()
                val compiled=try { compileRules(PasswordConfig(length=n,advanced=r)) }
                    catch(error:GenerationException) { assertTrue(expected.isEmpty());continue }
                CompletionCounter(compiled).use { counter ->
                    assertEquals(BigInteger.valueOf(expected.size.toLong()),counter.total())
                    assertEquals(expected,expected.indices.map { counter.unrank(BigInteger.valueOf(it.toLong())) })
                }
            }
        }
    }
    @Test fun secureIntegerRangeAndCanonicalSerialization() {
        val random=SecureRandom()
        for(bound in listOf(BigInteger.ONE,BigInteger.TWO,BigInteger.ONE.shiftLeft(65).subtract(BigInteger.ONE),BigInteger.valueOf(94).pow(64))) repeat(100) {
            val value=secureBelow(bound,random);assertTrue(value.signum()>=0 && value<bound)
        }
        val r=AdvancedRules(enabled=true,customAlphabetEnabled=true,customAlphabet="bbaA",forbiddenCharacters="!!")
        assertEquals("Aab",r.toData()["custom_alphabet"])
        assertEquals(r.toData(),AdvancedRules.fromData(r.toData()).toData())
        try { AdvancedRules.fromData(r.toData()+mapOf("password" to "secret"));fail() } catch(_:GenerationException) {}
    }
    @Test fun impossibleRunAndCancellationAreDistinct() {
        val config=PasswordConfig(length=8,advanced=AdvancedRules(enabled=true,customAlphabetEnabled=true,customAlphabet="a",maxIdenticalRun=1))
        try { PasswordGenerator().generate(config);fail() } catch(error:GenerationException) { assertEquals("no_valid_password",error.code) }
        CompletionCounter(compileRules(config)) { true }.use { c -> try { c.total();fail() } catch(_:GenerationCancelled) {} }
    }
    @Test fun benchmarkHardCasesWithoutRandomTimingAssertions() {
        for(cap in listOf(1,2,8,24)) {
            val r=AdvancedRules(enabled=true,minUppercase=13,minLowercase=13,minDigits=13,minSymbols=13,maxIdenticalRun=cap)
            val begin=System.nanoTime()
            CompletionCounter(compileRules(PasswordConfig(length=64,advanced=r))).use { c ->
                assertTrue(c.total().signum()>0)
                println("advanced benchmark: R=$cap time_ms=${(System.nanoTime()-begin)/1000000} states=${c.states}")
            }
        }
    }
    @Test fun primitiveStateMemoPreservesKeysAcrossGrowthAndClear() {
        val memo=LongMemo<BigInteger>()
        for(i in 0..12000) memo[i.toLong().shl(28) or (i%128).toLong()]=BigInteger.valueOf(i.toLong())
        for(i in 0..12000) assertEquals(BigInteger.valueOf(i.toLong()),memo[i.toLong().shl(28) or (i%128).toLong()])
        assertEquals(BigInteger.ZERO,memo.getOrPut(0) { throw AssertionError("Zero must be a cached value") })
        memo.clear();assertNull(memo[0]);assertNull(memo[12000L.shl(28) or (12000%128).toLong()])
    }

    @Test fun exhaustiveMinimumGridAndFilters() {
        val alphabet="aA1!"
        val n=4
        val candidates=strings(alphabet,n)
        for(u in 0..n) for(l in 0..n-u) for(d in 0..n-u-l) for(s in 0..n-u-l-d) {
            val rules=AdvancedRules(enabled=true,customAlphabetEnabled=true,customAlphabet=alphabet,
                minUppercase=u,minLowercase=l,minDigits=d,minSymbols=s,maxIdenticalRun=1,
                firstType=CharacterType.LETTER,lastType=CharacterType.SYMBOL)
            val expected=candidates.filter { accepts(it,rules) }.sorted()
            CompletionCounter(compileRules(PasswordConfig(length=n,advanced=rules))).use { counter ->
                assertEquals(BigInteger.valueOf(expected.size.toLong()),counter.total())
                assertEquals(expected,expected.indices.map { counter.unrank(BigInteger.valueOf(it.toLong())) })
            }
        }
        val filtered=PasswordConfig(length=20,uppercase=false,excludeSimilar=true,
            advanced=AdvancedRules(enabled=true,customAlphabetEnabled=true,customAlphabet="aabBO01l!2",forbiddenCharacters="!B"))
        repeat(20) { assertTrue(PasswordGenerator().generate(filtered).all { it in "ab2" }) }
    }
    @Test fun validationDistinguishesContradictionsFromEmptyAlphabet() {
        val base=AdvancedRules(enabled=true)
        val cases=listOf(
            PasswordConfig(length=12,advanced=base.copy(minDigits=13)) to "minimum_sum",
            PasswordConfig(numbers=false,advanced=base.copy(minDigits=2)) to "minimum_disabled",
            PasswordConfig(advanced=base.copy(minDigits=2,forbiddenCharacters="0123456789")) to "minimum_unavailable",
            PasswordConfig(advanced=base.copy(customAlphabetEnabled=true)) to "empty_alphabet",
            PasswordConfig(advanced=base.copy(customAlphabetEnabled=true,customAlphabet="12",firstType=CharacterType.LETTER)) to "first_unavailable",
            PasswordConfig(advanced=base.copy(forbiddenCharacters=" ")) to "rules_ascii",
        )
        for((config,code) in cases) {
            try { compileRules(config);fail("Must reject $code") } catch(error:GenerationException) { assertEquals(code,error.code) }
        }
        for(value in listOf(true,"2",-1,65)) {
            try { AdvancedRules.fromData(base.toData()+("min_digits" to value));fail() } catch(_:GenerationException) {}
        }
    }

}
