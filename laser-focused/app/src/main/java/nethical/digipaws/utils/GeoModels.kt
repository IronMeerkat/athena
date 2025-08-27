package nethical.digipaws.utils

/**
 * Geofencing models for AppBlocker policies.
 */
data class PointOfInterest(
    val id: String,
    val name: String,
    val latitude: Double,
    val longitude: Double,
    val radiusMeters: Float
)

/**
 * Policy to block apps at specific POIs between start and end minutes (0..1439)
 */
data class GeoBlockPolicy(
    val poiId: String,
    val startMinutes: Int,
    val endMinutes: Int,
    val apps: Set<String>
)


