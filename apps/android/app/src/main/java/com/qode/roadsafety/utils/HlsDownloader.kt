package com.qode.roadsafety.utils

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import okhttp3.ConnectionPool
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

object HlsDownloader {

    private val client = OkHttpClient.Builder()
        .connectionPool(ConnectionPool(8, 30, TimeUnit.SECONDS))
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private const val PARALLEL_DOWNLOADS = 8

    suspend fun downloadHlsToMp4(
        context: Context,
        m3u8Url: String,
        isHighQuality: Boolean = false,
        onProgress: (Float, String) -> Unit
    ): File = withContext(Dispatchers.IO) {
        val dir = android.os.Environment.getExternalStoragePublicDirectory(android.os.Environment.DIRECTORY_DOWNLOADS)
        val outputDir = File(dir, "QoDe/recordings").apply { mkdirs() }
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
                downloadSegmentsParallel(subPlaylistText, baseUrl, outputFile, onProgress)
            } else {
                downloadSegmentsParallel(playlistText, baseUrl, outputFile, onProgress)
            }
        } else {
            downloadSegmentsParallel(playlistText, baseUrl, outputFile, onProgress)
        }

        outputFile
    }

    private suspend fun downloadSegmentsParallel(
        playlistText: String,
        baseUrl: String,
        outputFile: File,
        onProgress: (Float, String) -> Unit
    ) = coroutineScope {
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
        val completedCount = AtomicInteger(0)
        val tempDir = outputFile.parentFile?.let { File(it, "segments_${System.currentTimeMillis()}") }
            ?: throw Exception("Cannot create temp directory")
        tempDir.mkdirs()

        try {
            // Download all segments in parallel batches
            onProgress(0.15f, "Downloading $total segments (parallel)...")

            val segmentFiles = segmentUrls.mapIndexed { index, segmentUrl ->
                async(Dispatchers.IO) {
                    val segmentFile = File(tempDir, "seg_${String.format("%05d", index)}.ts")
                    val req = Request.Builder().url(segmentUrl).build()
                    client.newCall(req).execute().use { resp ->
                        if (!resp.isSuccessful) throw Exception("Segment download failed: ${resp.code}")
                        val bytes = resp.body?.bytes() ?: byteArrayOf()
                        segmentFile.writeBytes(bytes)
                    }
                    val done = completedCount.incrementAndGet()
                    val progress = 0.15f + (0.75f * done / total)
                    onProgress(progress, "Downloaded $done/$total segments...")
                    segmentFile
                }
                
                // Add a small delay to prevent starving ExoPlayer's network requests
                Thread.sleep(100)
            }

            // Wait for all downloads to complete
            val downloadedFiles = segmentFiles.awaitAll()

            // Merge segments in order into the final file
            onProgress(0.92f, "Merging $total segments...")
            FileOutputStream(outputFile).use { fos ->
                for (segFile in downloadedFiles.sortedBy { it.name }) {
                    fos.write(segFile.readBytes())
                }
            }

            onProgress(1.0f, "HLS video recorded successfully: ${outputFile.name} (${outputFile.length() / 1024 / 1024} MB)")
        } finally {
            // Clean up temp segment files
            tempDir.deleteRecursively()
        }
    }
}
