package pl.franek.passwordgenerator

import java.math.BigInteger
import java.security.SecureRandom

enum class CharacterType(val wire: String, val mask: Int) {
    ANY("any", 15), LETTER("letter", 3), UPPER("upper", 1), LOWER("lower", 2), DIGIT("digit", 4), SYMBOL("symbol", 8);
}

data class AdvancedRules(
    val enabled: Boolean = false,
    val minUppercase: Int = 0, val minLowercase: Int = 0,
    val minDigits: Int = 0, val minSymbols: Int = 0,
    val customAlphabetEnabled: Boolean = false, val customAlphabet: String = "",
    val forbiddenCharacters: String = "",
    val firstType: CharacterType = CharacterType.ANY, val lastType: CharacterType = CharacterType.ANY,
    val maxIdenticalRun: Int? = null,
) {
    val minima get() = intArrayOf(minUppercase, minLowercase, minDigits, minSymbols)
    fun validateStructure() {
        ruleCheck(minima.all { it in 0..64 } && (maxIdenticalRun == null || maxIdenticalRun in 1..64), "rules_invalid")
        ruleCheck((customAlphabet + forbiddenCharacters).all { it.code in 33..126 }, "rules_ascii")
    }
    fun toData(): Map<String, Any?> {
        validateStructure()
        return mapOf("enabled" to enabled, "min_uppercase" to minUppercase, "min_lowercase" to minLowercase,
            "min_digits" to minDigits, "min_symbols" to minSymbols, "custom_alphabet_enabled" to customAlphabetEnabled,
            "custom_alphabet" to customAlphabet.toSet().sorted().joinToString(""),
            "forbidden_characters" to forbiddenCharacters.toSet().sorted().joinToString(""),
            "first_type" to firstType.wire, "last_type" to lastType.wire, "max_identical_run" to maxIdenticalRun)
    }
    companion object {
        fun fromData(data: Map<String, Any?>): AdvancedRules {
            ruleCheck(data.keys == AdvancedRules().toData().keys, "rules_invalid")
            fun number(key: String): Int { ruleCheck(data[key] is Int, "rules_invalid"); return data[key] as Int }
            fun flag(key: String): Boolean { ruleCheck(data[key] is Boolean, "rules_invalid"); return data[key] as Boolean }
            fun text(key: String): String { ruleCheck(data[key] is String, "rules_invalid"); return data[key] as String }
            fun type(key: String) = CharacterType.entries.find { it.wire == text(key) } ?: throw GenerationException("rules_invalid", "Unknown position type")
            ruleCheck(data["max_identical_run"] == null || data["max_identical_run"] is Int, "rules_invalid")
            return AdvancedRules(flag("enabled"), number("min_uppercase"), number("min_lowercase"), number("min_digits"), number("min_symbols"),
                flag("custom_alphabet_enabled"), text("custom_alphabet"), text("forbidden_characters"), type("first_type"), type("last_type"), data["max_identical_run"] as Int?).also { it.validateStructure() }
        }
    }
}

internal fun ruleCheck(condition: Boolean, code: String) {
    if (!condition) throw GenerationException(code, code)
}

class GenerationCancelled : RuntimeException()

data class CompiledRules(val length: Int, val pools: List<String>, val minima: IntArray, val masks: IntArray, val runLimit: Int)

fun compileRules(config: PasswordConfig): CompiledRules {
    val rules = config.advanced
    rules.validateStructure()
    val n = config.length
    ruleCheck(n in 1..64, "invalid_length")
    val flags = listOf(config.uppercase, config.lowercase, config.numbers, config.special)
    ruleCheck(flags.any { it }, "no_sets")
    ruleCheck(rules.minima.withIndex().none { (i, m) -> m > 0 && !flags[i] }, "minimum_disabled")
    val original = listOf(PasswordGenerator.UPPERCASE, PasswordGenerator.LOWERCASE, PasswordGenerator.DIGITS, PasswordGenerator.SPECIAL)
    val allowed = if (rules.customAlphabetEnabled) rules.customAlphabet.toSet() else original.joinToString("").toSet()
    val forbidden = rules.forbiddenCharacters.toSet() + if (config.excludeSimilar) PasswordGenerator.SIMILAR_CHARACTERS.toSet() else emptySet()
    val pools = original.mapIndexed { i, pool -> if (flags[i]) pool.filter { it in allowed && it !in forbidden } else "" }
    ruleCheck(pools.any { it.isNotEmpty() }, "empty_alphabet")
    ruleCheck(rules.minima.withIndex().none { (i, m) -> m > 0 && pools[i].isEmpty() }, "minimum_unavailable")
    ruleCheck(rules.minima.sum() <= n, "minimum_sum")
    val available = pools.withIndex().fold(0) { mask, (i, p) -> mask or if (p.isNotEmpty()) 1.shl(i) else 0 }
    val first = available and rules.firstType.mask
    val last = available and rules.lastType.mask
    ruleCheck(first != 0, "first_unavailable"); ruleCheck(last != 0, "last_unavailable")
    val masks = IntArray(n) { available }
    masks[0] = masks[0] and first; masks[n-1] = masks[n-1] and last
    ruleCheck(masks[0] != 0, "no_valid_password")
    return CompiledRules(n, pools, rules.minima, masks, rules.maxIdenticalRun ?: n)
}

/** Primitive-key memo table. State keys are structured bit fields; mixing all
 * bits avoids pathological buckets and boxing of every lookup on Android. */
internal class LongMemo<T : Any> {
    private var keys=LongArray(1024)
    private var values=arrayOfNulls<Any>(1024)
    private var size=0
    private fun slot(key: Long): Int {
        var mixed=key
        mixed=(mixed xor (mixed ushr 33)) * -49064778989728563L
        mixed=(mixed xor (mixed ushr 33)) * -4265267296055464877L
        mixed=mixed xor (mixed ushr 33)
        var position=mixed.toInt() and (keys.size-1)
        while(values[position]!=null && keys[position]!=key) position=(position+1) and (keys.size-1)
        return position
    }
    @Suppress("UNCHECKED_CAST")
    operator fun get(key: Long): T? = values[slot(key)] as T?
    operator fun set(key: Long,value: T) {
        if ((size+1)*10>=keys.size*7) {
            val oldKeys=keys;val oldValues=values
            keys=LongArray(oldKeys.size*2);values=arrayOfNulls(oldValues.size*2);size=0
            for(i in oldKeys.indices) {
                @Suppress("UNCHECKED_CAST")
                val old=oldValues[i] as T?
                if(old!=null) this[oldKeys[i]]=old
            }
        }
        val position=slot(key)
        if(values[position]==null) size++
        keys[position]=key;values[position]=value
    }
    inline fun getOrPut(key: Long,create: () -> T): T {
        val old=this[key]
        if(old!=null)return old
        return create().also { this[key]=it }
    }
    fun clear() { values.fill(null);size=0 }
}

/** Exact completion counts. The run-series identity and boundary correction
 * match app/advanced.py; exhaustive shared rank fixtures verify both engines. */
class CompletionCounter(val rules: CompiledRules, private val cancelled: () -> Boolean = { false }) : AutoCloseable {
    private val zero = BigInteger.ZERO
    private val one = BigInteger.ONE
    private val sizes = rules.pools.map { it.length }
    private val factors = sizes.map { BigInteger.valueOf(it.toLong()) }
    private val alphabet = rules.pools.flatMapIndexed { i, pool -> pool.map { it to i } }.sortedBy { it.first }
    private val initial = rules.minima.withIndex().fold(0) { p, (i, m) -> p or m.shl(7*i) }
    private val available = sizes.withIndex().fold(0) { p, (i, a) -> p or if (a > 0) 1.shl(i) else 0 }
    private val groups = sizes.filter { it > 0 }.distinct().map { size -> (0..3).filter { sizes[it] == size } }.filter { it.size > 1 }
    private val nodes = LongMemo<Array<BigInteger>>()
    private val plainCache = LongMemo<BigInteger>()
    private val endCache = LongMemo<BigInteger>()
    private val countCache = LongMemo<BigInteger>()
    private val canonicalCache = LongMemo<Pair<Int, IntArray>>()
    private val deficitCache = LongMemo<IntArray>()
    private val free = Array(rules.length+1) { one }
    private val emptyNode = Array(5) { zero }
    var states: Int = 0
        private set
    init {
        for (r in 1..rules.length) {
            val mask = rules.masks[rules.length-r]
            val amount = (0..3).filter { mask and 1.shl(it) != 0 }.sumOf { sizes[it] }
            free[r] = free[r-1].multiply(BigInteger.valueOf(amount.toLong()))
        }
    }
    private fun checkpoint() { states++; if (states and 1023 == 0 && cancelled()) throw GenerationCancelled() }
    private fun key(r: Int, p: Int) = r.toLong().shl(28) or p.toLong()
    private fun deficits(p: Int): IntArray = deficitCache.getOrPut(p.toLong()) {
        IntArray(5).also { a -> for (i in 0..3) { a[i] = p.ushr(7*i) and 127; a[4] += a[i] } }
    }
    private fun subtract(p: Int, c: Int, amount: Int): Int = p - minOf(p.ushr(7*c) and 127, amount).shl(7*c)
    private fun canonical(p: Int): Pair<Int, IntArray> = canonicalCache.getOrPut(p.toLong()) {
        var normalized = p
        val mapping = IntArray(4) { it }
        for (group in groups) {
            val values = group.map { p.ushr(7*it) and 127 }
            val ordered = values.sortedDescending()
            group.forEachIndexed { j, i ->
                normalized = (normalized and 127.shl(7*i).inv()) or ordered[j].shl(7*i)
                mapping[i] = group[ordered.indexOf(values[j])]
            }
        }
        normalized to mapping
    }
    private fun plain(r: Int, p: Int): BigInteger {
        if (p == 0) return free[r]
        val k = key(r,p)
        plainCache[k]?.let { return it }
        checkpoint()
        val ds = deficits(p)
        if (ds[4] > r || r == 0) return zero
        var value = zero
        for (j in 0..3) if (rules.masks[rules.length-r] and 1.shl(j) != 0) {
            value = value.add(plain(r-1, subtract(p,j,1)).multiply(factors[j]))
        }
        plainCache[k] = value
        return value
    }
    private fun words(r: Int, p: Int): BigInteger = node(r, if (groups.isEmpty()) p else canonical(p).first)[0]
    private fun ending(r: Int, p: Int, c: Int): BigInteger {
        if (groups.isEmpty()) return node(r,p)[c+1]
        val (normalized, mapping) = canonical(p)
        return node(r,normalized)[mapping[c]+1]
    }
    private fun node(r: Int, p: Int): Array<BigInteger> {
        if (r < 0 || deficits(p)[4] > r) return emptyNode
        if (r == 0) return arrayOf(one,zero,zero,zero,zero)
        val k = key(r,p)
        nodes[k]?.let { return it }
        checkpoint()
        val ds = deficits(p)
        val result = Array(5) { zero }
        val q = rules.runLimit+1
        for (c in 0..3) {
            if (sizes[c] == 0) continue
            var equivalent = -1
            for (j in 0 until c) if (sizes[j] == sizes[c] && ds[j] == ds[c]) { equivalent=j;break }
            if (equivalent >= 0) result[c+1] = result[equivalent+1]
            else {
                var value = words(r-1,subtract(p,c,1))
                if (r >= q) {
                    var shifted = subtract(p,c,q)
                    var marked = c
                    if (groups.isNotEmpty()) { val normalized = canonical(shifted); shifted = normalized.first; marked = normalized.second[c] }
                    val previous = node(r-q,shifted)
                    value = value.add(previous[marked+1]).subtract(previous[0])
                }
                result[c+1] = value
            }
            result[0] = result[0].add(result[c+1].multiply(factors[c]))
        }
        nodes[k] = result
        return result
    }
    private fun withEnd(r: Int, p: Int): BigInteger {
        if (r == 0) return zero
        val end = rules.masks.last()
        if (end == available) return words(r,p)
        val k=key(r,p)
        endCache[k]?.let { return it }
        var value=zero
        for (c in 0..3) if (end and 1.shl(c) != 0) value=value.add(ending(r,p,c).multiply(factors[c]))
        endCache[k]=value
        return value
    }
    private fun count(r: Int,p: Int,previous: Int,run: Int): BigInteger {
        val ds=deficits(p)
        if (ds[4]>r) return zero
        if (r==0) return if (p==0) one else zero
        val limit=rules.runLimit
        val maxDef=(0..3).filter { sizes[it]>0 }.maxOf { ds[it] }
        if (limit>=r-ds[4]+maxDef && (previous==4 || limit>=run+r-ds[4]+ds[previous])) return plain(r,p)
        val k=key(r,p) or previous.toLong().shl(35) or run.toLong().shl(38)
        countCache[k]?.let { return it }
        checkpoint()
        var value=zero
        if (previous==4) {
            if (rules.masks[0]==available) return withEnd(r,p)
            for (c in 0..3) if (rules.masks[0] and 1.shl(c)!=0) value=value.add(count(r-1,subtract(p,c,1),c,1).multiply(factors[c]))
        } else {
            val q=limit+1
            val offset=q-run
            for (i in 0..r step q) {
                value=value.add(withEnd(r-i,subtract(p,previous,i)))
                if (i+offset<=r) value=value.subtract(withEnd(r-i-offset,subtract(p,previous,i+offset)))
            }
            if (rules.masks.last() and 1.shl(previous)!=0 && (0..3).all { it==previous || ds[it]==0 }) {
                if (r>=q && r%q==0) value=value.add(one)
                if (r>=offset && r%q==offset) value=value.subtract(one)
            }
        }
        countCache[k]=value
        return value
    }
    fun total(): BigInteger { if (cancelled()) throw GenerationCancelled(); return count(rules.length,initial,4,0) }
    fun unrank(input: BigInteger): String {
        require(input.signum()>=0 && input<total()) { "Rank outside valid range" }
        var rank=input; var p=initial; var previous: Char?=null; var run=0
        return buildString {
            for (position in 0 until rules.length) {
                if (cancelled()) throw GenerationCancelled()
                var found=false
                for ((char,c) in alphabet) {
                    if (rules.masks[position] and 1.shl(c)==0) continue
                    val nextRun=if (char==previous) run+1 else 1
                    if (nextRun>rules.runLimit) continue
                    val next=subtract(p,c,1)
                    val width=count(rules.length-position-1,next,c,nextRun)
                    if (rank<width) { append(char);p=next;previous=char;run=nextRun;found=true;break }
                    rank=rank.subtract(width)
                }
                check(found) { "Completion-count invariant violated" }
            }
        }
    }
    override fun close() { nodes.clear();plainCache.clear();endCache.clear();countCache.clear();canonicalCache.clear();deficitCache.clear() }
}

fun secureBelow(bound: BigInteger, random: SecureRandom): BigInteger {
    require(bound.signum()>0)
    if (bound==BigInteger.ONE) return BigInteger.ZERO
    val bits=bound.subtract(BigInteger.ONE).bitLength()
    val bytes=ByteArray((bits+7)/8)
    while (true) {
        random.nextBytes(bytes)
        bytes[0]=(bytes[0].toInt() and (255 ushr (bytes.size*8-bits))).toByte()
        val value=BigInteger(1,bytes)
        if (value<bound) return value
    }
}

fun generateAdvanced(config: PasswordConfig, random: SecureRandom, cancelled: () -> Boolean = { false }): String =
    CompletionCounter(compileRules(config),cancelled).use { counter ->
        val total=counter.total()
        ruleCheck(total.signum()>0,"no_valid_password")
        counter.unrank(secureBelow(total,random))
    }
