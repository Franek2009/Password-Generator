package pl.franek.passwordgenerator

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.security.MessageDigest

class ClipboardGuardTest {
    private class Port : ClipboardPort {
        var text: String? = null
        var token: String? = null
        var available = true
        var failClear = false
        var failWrite = false
        var clears = 0
        var onMatch: (() -> Unit)? = null
        var onClear: (() -> Unit)? = null
        override fun write(text: String, token: String?): Boolean {
            if (failWrite) return false
            this.text = text; this.token = token
            return true
        }
        override fun matches(pending: PendingCopy, content: Boolean): Boolean? {
            if (!available) return null
            val match = token == pending.token && (!content || MessageDigest.isEqual(ClipboardGuard.digest(text!!), pending.digest))
            val callback = onMatch; onMatch = null; callback?.invoke()
            return match
        }
        override fun clear(): Boolean {
            if (failClear) return false
            text = null; token = null; clears++
            onClear?.invoke()
            return true
        }
    }

    @Test fun sharedContractMatchesPython() {
        val cases = JSONObject(javaClass.getResource("/clipboard_contract.json")!!.readText()).getJSONArray("cases")
        for (index in 0 until cases.length()) {
            val case = cases.getJSONObject(index)
            val port = Port()
            var now = 0L
            val guard = ClipboardGuard(port, { now })
            val steps = case.getJSONArray("steps")
            for (stepIndex in 0 until steps.length()) {
                val step = steps.getJSONObject(stepIndex)
                when (step.getString("action")) {
                    "policy" -> guard.setPolicy(step.getInt("value"))
                    "copy" -> guard.copy(step.getString("value"))
                    "advance" -> now += step.getLong("value")
                    "tick" -> guard.tick()
                    "changed" -> guard.changed()
                    "foreign" -> { port.text = step.getString("value"); port.token = null }
                    "mutate" -> port.text = step.getString("value")
                    "unavailable" -> port.available = !step.getBoolean("value")
                    "fail_clear" -> port.failClear = step.getBoolean("value")
                    else -> fail("Unknown contract action")
                }
            }
            val name = case.getString("name")
            assertEquals(name, if (case.isNull("text")) null else case.getString("text"), port.text)
            assertEquals(name, case.getBoolean("pending"), guard.pending != null)
            assertEquals(name, case.getInt("clears"), port.clears)
        }
    }

    @Test fun reentrantClearAndStaleReadCannotCancelNewCopy() {
        val port = Port(); var now = 0L
        val guard = ClipboardGuard(port, { now })
        guard.setPolicy(30); guard.copy("Alpha"); now = 30000
        port.onClear = { guard.changed(); guard.tick() }
        guard.tick()
        assertEquals(1, port.clears); assertNull(guard.pending)
        guard.copy("Alpha"); now += 30000
        port.onMatch = { guard.copy("Beta") }
        guard.tick()
        assertEquals("Beta", port.text); assertNotNull(guard.pending)
        assertEquals(1, port.clears)
        now += 30000; port.onClear = { guard.copy("Gamma") }; guard.tick()
        assertEquals("Gamma", port.text); assertNotNull(guard.pending)
    }

    @Test fun failedCopyAndDisposalLeaveNoPendingSecret() {
        val port = Port(); val guard = ClipboardGuard(port, { 0 })
        guard.setPolicy(30); guard.copy("Alpha")
        assertFalse(guard.pending.toString().contains("Alpha"))
        port.failWrite = true
        assertFalse(guard.copy("Beta")); assertNull(guard.pending)
        port.failWrite = false; guard.copy("Gamma"); guard.cancel()
        assertNull(guard.pending)
    }
}
