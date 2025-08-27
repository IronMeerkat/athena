package nethical.digipaws.blockers

import android.os.SystemClock


abstract class BaseBlocker{
    fun isDelayOver(lastTimeStamp: Float): Boolean {
        val currentTime = SystemClock.uptimeMillis().toFloat()
        return currentTime - lastTimeStamp > 30000
    }

    fun isDelayOver(lastTimeStamp: Float, delay: Int): Boolean {
        val currentTime = SystemClock.uptimeMillis().toFloat()
        return currentTime - lastTimeStamp > delay
    }
}