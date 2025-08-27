package nethical.digipaws.utils

import android.location.Location

object GeoTools {
    fun isInsidePoi(currentLat: Double, currentLon: Double, poi: PointOfInterest): Boolean {
        val results = FloatArray(1)
        Location.distanceBetween(currentLat, currentLon, poi.latitude, poi.longitude, results)
        return results[0] <= poi.radiusMeters
    }
}


