package pl.franek.passwordgenerator

import android.os.SystemClock
import android.os.Debug
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.security.SecureRandom
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Engine-only measurement: no Activity, clipboard, presets or device settings. */
@RunWith(AndroidJUnit4::class)
class AdvancedEngineBenchmarkTest {
    @Test fun measureExactCountsOnDevice() {
        val runtime=Runtime.getRuntime()
        for ((cap,forbidden) in listOf(1 to "",2 to "",8 to "",24 to "",1 to "A",2 to "A")) {
            runtime.gc()
            val baseline=runtime.totalMemory()-runtime.freeMemory()
            val baselinePss=Debug.getPss()
            val peak=AtomicLong(baseline)
            val running=AtomicBoolean(true)
            val monitor=Thread {
                while(running.get()) {
                    val used=runtime.totalMemory()-runtime.freeMemory()
                    peak.updateAndGet { maxOf(it,used) }
                    Thread.sleep(5)
                }
            }
            val rules=AdvancedRules(enabled=true,minUppercase=13,minLowercase=13,minDigits=13,minSymbols=13,maxIdenticalRun=cap,forbiddenCharacters=forbidden)
            val random=SecureRandom()
            val begin=SystemClock.elapsedRealtimeNanos()
            monitor.start()
            try {
                CompletionCounter(compileRules(PasswordConfig(length=64,advanced=rules))).use { counter ->
                    val count=counter.total()
                    val generated=counter.unrank(secureBelow(count,random))
                    assertTrue(generated.length==64)
                    val elapsed=(SystemClock.elapsedRealtimeNanos()-begin)/1000000
                    val extra=(peak.get()-baseline)/1048576
                    val extraPss=maxOf(0,Debug.getPss()-baselinePss)/1024
                    assertTrue(count.signum()>0)
                    println("ADVANCED_ENGINE_BENCHMARK cap=$cap forbidden=$forbidden time_ms=$elapsed extra_heap_mib=$extra extra_pss_mib=$extraPss states=${counter.states} budget_met=${elapsed<=2000 && extra<=128 && extraPss<=128}")
                }
            } finally { running.set(false);monitor.join() }
        }
    }
}
