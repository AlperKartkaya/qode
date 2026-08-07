package com.qode.roadsafety.utils

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream

object HlsDownloader {

    private val client = OkHttpClient.Builder().build()

    suspend fun downloadHlsToMp4(
        context: Context,
        m3u8Url: String,
        isHighQuality: Boolean = false,
        onProgress: (Float, String) -> Unit
    ): File = withContext(Dispatchers.IO) {
        val outputDir = File(context.cacheDir, "recordings").apply { mkdirs() }
        val outputFile = File(outputDir, "recorded_stream_${System.currentTimeMillis()}.mp4")

        onProgress(0.05f, "Fetching HLS master playlist...")
        
        // 1. Fetch playlist content
        val request = Request.Builder().url(m3u8Url).build()
        val playlistText = client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw Exception("Failed to download playlist: HTTP ${response.code}")
            response.body?.string() ?: throw Exception("Empty playlist response")
        }

        var mediaPlaylistUrl = m3u8Url
        var baseUrl = m3u8Url.substringBeforeLast("/") + "/"

        // 2. Check if master playlist contains sub-playlists (.m3u8)
        if (playlistText.contains("#EXT-X-STREAM-INF")) {
            val lines = playlistText.lines()
            val variants = mutableListOf<String>()
            for (i in lines.indices) {
                if (lines[i].startsWith("#EXT-X-STREAM-INF")) {
                    if (i + 1 < lines.size && lines[i + 1].trim().isNotEmpty()) {
                        variants.add(lines[i + 1].trim())
                    }
                }
            }

            if (variants.isNotEmpty()) {
                val selectedVariant = if (isHighQuality) {
                    variants.first() // Usually top resolution in master playlist
                } else {
                    variants.last()  // Lowest resolution
                }
                
                mediaPlaylistUrl = if (selectedVariant.startsWith("http")) {
                    selectedVariant
                } else {
                    baseUrl + selectedVariant
                }
                baseUrl = mediaPlaylistUrl.substringBeforeLast("/") + "/"

                onProgress(0.10f, "Selected variant: ${if (isHighQuality) "1080p (High)" else "240p (Low)"}")
                
                // Fetch the selected media playlist
                val mediaReq = Request.Builder().url(mediaPlaylistUrl).build()
                val subPlaylistText = client.newCall(mediaReq).execute().use { res ->
                    res.body?.string() ?: throw Exception("Empty media playlist")
                }
                parseAndDownloadSegments(subPlaylistText, baseUrl, outputFile, onProgress)
            } else {
                parseAndDownloadSegments(playlistText, baseUrl, outputFile, onProgress)
            }
        } else {
            parseAndDownloadSegments(playlistText, baseUrl, outputFile, onProgress)
        }

        outputFile
    }

    private fun parseAndDownloadSegments(
        playlistText: String,
        baseUrl: String,
        outputFile: File,
        onProgress: (Float, String) -> Unit
    ) {
        val segmentUrls = mutableListOf<String>()
        val lines = playlistText.lines()
        for (line in lines) {
            val trimmed = line.trim()
            if (trimmed.isNotEmpty() && !trimmed.startsWith("#")) {
                val fullUrl = if (trimmed.startsWith("http")) trimmed else baseUrl + trimmed
                segmentUrls.add(fullUrl)
            }
        }

        if (segmentUrls.isEmpty()) {
            throw Exception("No video segments found in HLS playlist.")
        }

        val total = segmentUrls.size
        FileOutputStream(outputFile).use { fos ->
            segmentUrls.forEachIndexed { index, segmentUrl ->
                val progress = 0.15f + (0.80f * (index + 1) / total)
                onProgress(progress, "Downloading segment ${index + 1}/$total...")

                val req = Request.Builder().url(segmentUrl).build()
                client.newCall(req).execute().use { resp ->
                    if (!resp.isSuccessful) throw Exception("Segment download failed: ${resp.code}")
                    val bytes = resp.body?.bytes() ?: byteArrayOf()
                    fos.write(bytes)
                }
                
                // Add a small delay to prevent starving ExoPlayer's network requests
                Thread.sleep(100)
            }
        }

        onProgress(1.0f, "HLS video recorded successfully: ${outputFile.name} (${outputFile.length() / 1024 / 1024} MB)")
    }
}
