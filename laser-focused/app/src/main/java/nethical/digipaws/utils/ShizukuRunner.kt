package nethical.digipaws.utils
import moe.shizuku.server.IShizukuService
import rikka.shizuku.Shizuku
import java.io.BufferedReader
import java.io.FileInputStream
import java.io.InputStreamReader

/**
 * Utility class for executing shell commands using Shizuku
 */
class ShizukuRunner {

    interface CommandResultListener {
        /**
         * Called when the command produces output.
         * @param output The output from the command execution
         * @param done True if the command execution is complete, false otherwise
         */
        fun onCommandResult(output: String, done: Boolean) {}

        /**
         * Called when an error occurs during command execution.
         * @param error The error message
         */
        fun onCommandError(error: String) {}
    }

    companion object {

        /**
         * Executes a shell command using Shizuku.
         * @param command The shell command to execute
         * @param listener Listener for command results and errors
         * @param lineBundle Number of lines to batch before invoking the listener
         */
        fun executeCommand(command: String, listener: CommandResultListener, lineBundle: Int = 50) {
            Thread {
                try {
                    // Initialize the Shizuku process
                    val process = IShizukuService.Stub.asInterface(Shizuku.getBinder())
                        .newProcess(arrayOf("sh", "-c", command), null, null)

                    // Readers for command output and error streams
                    val outputReader = BufferedReader(InputStreamReader(FileInputStream(process.inputStream.fileDescriptor)))
                    val errorReader = BufferedReader(InputStreamReader(FileInputStream(process.errorStream.fileDescriptor)))

                    // StringBuilders for capturing output and errors
                    val outputBuffer = StringBuilder()
                    val errorBuffer = StringBuilder()

                    var line: String?
                    var lineCount = 0

                    // Read output stream
                    while (outputReader.readLine().also { line = it } != null) {
                        lineCount++
                        outputBuffer.append(line).append("\n")

                        // Send partial results if lineBundle is reached
                        if (lineCount == lineBundle) {
                            lineCount = 0
                            listener.onCommandResult(outputBuffer.toString(), false)
                            outputBuffer.clear()
                        }
                    }

                    // Read error stream
                    while (errorReader.readLine().also { line = it } != null) {
                        errorBuffer.append(line).append("\n")
                    }

                    // Notify listener of results or errors
                    if (errorBuffer.isNotBlank()) {
                        listener.onCommandError(errorBuffer.toString())
                    } else {
                        listener.onCommandResult(outputBuffer.toString(), true)
                    }

                    // Wait for process to complete
                    process.waitFor()

                } catch (e: Exception) {
                    // Notify listener of exceptions
                    listener.onCommandError(e.message ?: "An unexpected error occurred while executing the command.")
                }
            }.start()
        }
    }
}
