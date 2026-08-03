package com.qode.roadsafety.utils

import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object ZipUtils {

    suspend fun zipVideoFile(context: Context, videoFile: File): File = withContext(Dispatchers.IO) {
        val zipFile = File(videoFile.parentFile, "qode_recording_${System.currentTimeMillis()}.zip")
        
        ZipOutputStream(FileOutputStream(zipFile)).use { zos ->
            FileInputStream(videoFile).use { fis ->
                val entry = ZipEntry("video.mp4")
                zos.putNextEntry(entry)
                fis.copyTo(zos)
                zos.closeEntry()
            }
        }
        zipFile
    }

    fun shareFileViaLifebox(context: Context, file: File) {
        val authority = "${context.packageName}.fileprovider"
        val contentUri = FileProvider.getUriForFile(context, authority, file)

        val mimeType = if (file.extension == "zip") "application/zip" else "video/mp4"

        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = mimeType
            putExtra(Intent.EXTRA_STREAM, contentUri)
            putExtra(Intent.EXTRA_SUBJECT, "QoDe Recorded Video Stream")
            putExtra(Intent.EXTRA_TEXT, "TEKNOFEST 2026 Smart Road Safety Video Stream Recording")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }

        val chooser = Intent.createChooser(shareIntent, "Share with Lifebox / Hakem...")
        chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(chooser)
    }
}
