package nethical.digipaws.utils

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

object ZipUtils {
    // Register this in your activity
    fun registerDirectoryPicker(
        activity: AppCompatActivity,
        onDirectoryPicked: (Uri) -> Unit
    ): ActivityResultLauncher<Intent> {
        return activity.registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            result.data?.data?.let { uri ->
                // Persist permission for future access
                val takeFlags =
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                activity.contentResolver.takePersistableUriPermission(uri, takeFlags)
                onDirectoryPicked(uri)
            }
        }
    }


    // Function to show directory picker
    fun showDirectoryPicker(launcher: ActivityResultLauncher<Intent>) {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
        launcher.launch(intent)
    }

    // Save zip to user selected location
    fun zipSharedPreferencesToUri(context: Context, outputUri: Uri) {
        try {
            context.contentResolver.openOutputStream(outputUri)?.use { outputStream ->
                ZipOutputStream(BufferedOutputStream(outputStream)).use { zos ->
                    // Get list of shared preferences files
                    val sharedPrefsDir = File(context.filesDir.parent, "shared_prefs")

                    for (file in sharedPrefsDir.listFiles() ?: emptyArray()) {
                        FileInputStream(file).use { fis ->
                            val entry = ZipEntry(file.name)
                            zos.putNextEntry(entry)
                            fis.copyTo(zos)
                            zos.closeEntry()
                        }
                    }

                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // Load zip from user selected location
    fun unzipSharedPreferencesFromUri(context: Context, inputUri: Uri) {
        try {
            context.contentResolver.openInputStream(inputUri)?.use { inputStream ->
                ZipInputStream(BufferedInputStream(inputStream)).use { zis ->
                    val sharedPrefsDir = File(context.filesDir.parent, "shared_prefs")

//                    sharedPrefsDir.deleteRecursively()
                    if (!sharedPrefsDir.exists()) {
                        sharedPrefsDir.mkdir() // Ensure the directory exists
                    }

                    var entry = zis.nextEntry

                    while (entry != null) {
                        val outputFile = File(sharedPrefsDir, entry.name)

                        Log.d("Unzipping", entry.name + " to ${outputFile.path}")
                        // Ensure the file is deleted if it already exists
                        if (outputFile.exists()) {
                            outputFile.delete()
                        }
                        Log.d(
                            "Permissions",
                            "Can read: ${sharedPrefsDir.canRead()}, Can write: ${sharedPrefsDir.canWrite()}"
                        )

                        FileOutputStream(outputFile).use { outputStream ->
                            zis.copyTo(outputStream) // Efficiently copy data
                        }

                        zis.closeEntry()
                        // Reload the SharedPreferences for this file
                        if (entry.name.endsWith(".xml")) {
                            val prefsName = entry.name.removeSuffix(".xml")
                            val sharedPreferences =
                                context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)

                            // Force a reload by accessing the preferences
                            sharedPreferences.all // This forces a read from disk
                            Log.d("ReloadSharedPreferences", "Reloaded preferences: $prefsName")

                        }
                        entry = zis.nextEntry
                    }
                }
            }


        } catch (e: Exception) {
            Log.e("error", e.toString())
        }
    }

    // Utility function to create a zip file name with timestamp
    fun createZipFileName(): String {
        val timestamp = System.currentTimeMillis()
        return "backup_$timestamp.zip"
    }

    fun showRestorePicker(launcher: ActivityResultLauncher<Intent>) {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "application/zip"
        }
        launcher.launch(intent)
    }
}