package pl.franek.passwordgenerator

import android.content.ClipData
import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.PersistableBundle
import android.os.SystemClock
import java.security.MessageDigest

internal const val CLIPBOARD_TOKEN = "pl.franek.passwordgenerator.copyToken"

internal class AndroidClipboardPort(private val clipboard: ClipboardManager) : ClipboardPort {
    var focused = false
    override fun write(text: String, token: String?): Boolean = try {
        val clip = ClipData.newPlainText("Password Generator", text)
        clip.description.extras = PersistableBundle().apply {
            if (Build.VERSION.SDK_INT >= 33) putBoolean(ClipDescription.EXTRA_IS_SENSITIVE, true)
            if (token != null) putString(CLIPBOARD_TOKEN, token)
        }
        clipboard.setPrimaryClip(clip)
        true
    } catch (_: RuntimeException) { false }

    override fun matches(pending: PendingCopy, content: Boolean): Boolean? {
        if (!focused) return null
        return try {
            val description = clipboard.primaryClipDescription ?: return null
            if (description.extras?.getString(CLIPBOARD_TOKEN) != pending.token) return false
            if (!content) return true
            val clip = clipboard.primaryClip ?: return null
            if (clip.description.extras?.getString(CLIPBOARD_TOKEN) != pending.token || clip.itemCount != 1) return false
            val item = clip.getItemAt(0)
            val text = item.text ?: return false
            item.uri == null && item.intent == null &&
                MessageDigest.isEqual(ClipboardGuard.digest(text.toString()), pending.digest)
        } catch (_: RuntimeException) { null }
    }

    override fun clear(): Boolean = try {
        if (!focused) false else {
            if (Build.VERSION.SDK_INT >= 28) clipboard.clearPrimaryClip()
            else clipboard.setPrimaryClip(ClipData.newPlainText("", ""))
            true
        }
    } catch (_: RuntimeException) { false }
}

internal class AndroidClipboardController(context: Context, clock: () -> Long = SystemClock::elapsedRealtime) {
    private val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    private val port = AndroidClipboardPort(clipboard)
    private val guard = ClipboardGuard(port, clock)
    private val handler = Handler(Looper.getMainLooper())
    private val timeout = Runnable { check() }
    private val listener = ClipboardManager.OnPrimaryClipChangedListener { guard.changed(); check() }
    private var alive = true

    init { clipboard.addPrimaryClipChangedListener(listener) }
    fun setPolicy(seconds: Int) { guard.setPolicy(seconds); check() }
    fun copy(text: String): Boolean { val copied = guard.copy(text); check(); return copied }
    fun focusChanged(focused: Boolean) { port.focused = focused; if (focused) check() }
    private fun check() {
        handler.removeCallbacks(timeout)
        if (alive) guard.tick()?.let { handler.postDelayed(timeout, it.coerceIn(1L, 1000L)) }
    }
    fun dispose() {
        if (!alive) return
        alive = false
        handler.removeCallbacks(timeout)
        clipboard.removePrimaryClipChangedListener(listener)
        guard.cancel()
    }
}
