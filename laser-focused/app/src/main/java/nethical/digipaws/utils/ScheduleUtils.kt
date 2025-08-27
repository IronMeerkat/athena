package nethical.digipaws.utils

import android.content.Context
import java.util.Calendar

object ScheduleUtils {
    fun isWithinScheduleNow(context: Context): Boolean {
        val items = SavedPreferencesLoader(context).loadAutoFocusHoursList()
        if (items.isEmpty()) return false
        val cal = Calendar.getInstance()
        val currentMinutes = cal.get(Calendar.HOUR_OF_DAY) * 60 + cal.get(Calendar.MINUTE)
        items.forEach { item ->
            val start = item.startTimeInMins
            val end = item.endTimeInMins
            val inWindow = if (start <= end) {
                currentMinutes in start..end
            } else {
                currentMinutes >= start || currentMinutes <= end
            }
            if (inWindow) return true
        }
        return false
    }
}


