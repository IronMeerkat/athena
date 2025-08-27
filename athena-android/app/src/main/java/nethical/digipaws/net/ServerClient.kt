package nethical.digipaws.net

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

class ServerClient(private val context: Context) {

    companion object {
        private const val TAG = "ServerClient"
        private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000" // Android emulator to host
    }

    data class Classification(val shouldBlock: Boolean, val classification: String)

    private fun baseUrl(): String {
        val sp = context.getSharedPreferences("server_config", Context.MODE_PRIVATE)
        return sp.getString("base_url", DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
    }

    fun classifyUrl(urlString: String, title: String = ""): Classification? {
        return try {
            val endpoint = baseUrl().trimEnd('/') + "/agents/classifier/invoke"
            val payload = JSONObject().apply {
                put("input", JSONObject().apply {
                    put("url", urlString)
                    put("title", title)
                })
            }
            val conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 5000
                readTimeout = 8000
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
            conn.outputStream.use { os ->
                os.write(payload.toString().toByteArray())
            }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val body = BufferedReader(InputStreamReader(stream)).use { it.readText() }
            if (code !in 200..299) {
                Log.e(TAG, "HTTP $code: $body")
                return null
            }
            val json = JSONObject(body)
            val out = when {
                json.has("output") -> json.getJSONObject("output")
                json.has("data") && json.getJSONObject("data").has("output") ->
                    json.getJSONObject("data").getJSONObject("output")
                else -> json
            }
            val shouldBlock = out.optBoolean("should_block", false)
            val classification = out.optString("classification", "neutral")
            Classification(shouldBlock = shouldBlock, classification = classification)
        } catch (e: Exception) {
            Log.e(TAG, "classifyUrl error", e)
            null
        }
    }

    fun classifyApp(packageName: String, activity: String? = null, title: String = ""): Classification? {
        val act = activity?.let { "/$it" } ?: ""
        return classifyUrl("app://$packageName$act", title)
    }
}


