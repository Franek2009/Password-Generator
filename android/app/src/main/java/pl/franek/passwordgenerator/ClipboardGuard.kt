package pl.franek.passwordgenerator

import java.security.MessageDigest
import java.util.UUID

internal val CLIPBOARD_CLEAR_SECONDS = listOf(0, 30, 60, 120)
internal data class PendingCopy(val token: String, val digest: ByteArray, val deadline: Long)

internal interface ClipboardPort {
    fun write(text: String, token: String?): Boolean
    // null means unavailable; metadata checks must not retrieve foreign text.
    fun matches(pending: PendingCopy, content: Boolean): Boolean?
    fun clear(): Boolean
}

internal class ClipboardGuard(
    private val port: ClipboardPort,
    private val clock: () -> Long,
    private val tokenFactory: () -> String = { UUID.randomUUID().toString() },
) {
    var pending: PendingCopy? = null
        private set
    private var seconds = 0
    private var generation = 0L

    fun setPolicy(value: Int) {
        seconds = value.takeIf { it in CLIPBOARD_CLEAR_SECONDS } ?: 0
        if (seconds == 0) cancel()
    }
    fun cancel() { generation++; pending = null }
    fun copy(text: String): Boolean {
        if (text.isEmpty()) return false
        cancel()
        val token = if (seconds > 0) tokenFactory() else null
        val request = generation
        if (!port.write(text, token)) return false
        if (token != null && generation == request) pending = PendingCopy(token, digest(text), clock() + seconds * 1000L)
        return true
    }
    fun changed() {
        val entry = pending ?: return
        if (port.matches(entry, false) == false && pending === entry) cancel()
    }
    fun tick(): Long? {
        val entry = pending ?: return null
        val remaining = entry.deadline - clock()
        if (remaining > 0) return remaining
        val match = port.matches(entry, true)
        if (pending !== entry) return null
        if (match == false) cancel()
        else if (match == true) {
            val request = generation
            pending = null // clear() can emit a reentrant change notification.
            if (!port.clear() && generation == request) pending = entry
        }
        return null
    }
    companion object {
        fun digest(text: String): ByteArray = MessageDigest.getInstance("SHA-256").digest(text.toByteArray(Charsets.UTF_8))
    }
}
