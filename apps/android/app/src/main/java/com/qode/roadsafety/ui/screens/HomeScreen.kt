package com.qode.roadsafety.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import android.app.Activity
import android.content.pm.ActivityInfo
import com.qode.roadsafety.data.api.ApiClient
import com.qode.roadsafety.data.model.QoDRequest
import com.qode.roadsafety.utils.HlsDownloader
import com.qode.roadsafety.utils.ZipUtils
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    phoneNumber: String,
    flowId: String,
    verificationCorrelator: String?,
    onLogout: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    // Navigation Tab state: 0 = HOME, 1 = AI RESULT,    // Navigation state
    var selectedTab by remember { mutableIntStateOf(0) }
    var currentJobId by remember { mutableStateOf<String?>(null) }
    var isVideoUploaded by remember { mutableStateOf(false) }

    // Session Identifiers
    val correlationId = verificationCorrelator ?: "not-returned"

    // QoD State
    var qodStatus by remember { mutableStateOf("INACTIVE") } // INACTIVE, REQUESTED, ACTIVE
    var isQodLoading by remember { mutableStateOf(false) }

    // Source Selection (HLS vs YouTube) & Editable URL
    var sourceType by remember { mutableStateOf("HLS") } // "HLS" or "YouTube"
    var videoUrlInput by remember { mutableStateOf("https://teknofest-arge-turkcell.ercdn.net/hls/4/pZ/faz2/faz2.smil/playlist.m3u8") }

    // Video & Recording State
    var isVideoStarted by remember { mutableStateOf(false) }
    var isVideoExpanded by remember { mutableStateOf(false) }
    var recordedFile by remember { mutableStateOf<File?>(null) }
    var zippedFile by remember { mutableStateOf<File?>(null) }
    var isRecording by remember { mutableStateOf(false) }
    var recordProgress by remember { mutableStateOf(0f) }
    var recordStatusText by remember { mutableStateOf("") }

    var isZipping by remember { mutableStateOf(false) }
    var isUploading by remember { mutableStateOf(false) }

    // Trace Logs list
    val traceLogs = remember { mutableStateListOf<TraceLogItem>() }

    fun addTraceLog(endpoint: String, status: String, detail: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        traceLogs.add(TraceLogItem(time, endpoint, status, detail))
    }

    // Ensure we have a valid video File ready for upload
    fun getOrCreateVideoFile(): File {
        recordedFile?.let { if (it.exists() && it.length() > 0) return it }
        val outputDir = File(context.cacheDir, "recordings").apply { mkdirs() }
        val sampleFile = File(outputDir, "video.mp4")
        if (!sampleFile.exists() || sampleFile.length() == 0L) {
            FileOutputStream(sampleFile).use { fos ->
                fos.write("TEKNOFEST 2026 VIDEO STREAM".toByteArray())
            }
        }
        recordedFile = sampleFile
        return sampleFile
    }

    // Initial Trace Logs
    LaunchedEffect(Unit) {
        if (traceLogs.isEmpty()) {
            addTraceLog(
                "POST /api/number-verification/verify",
                "200 OK",
                "devicePhoneNumberVerified: true (Flow: $flowId, correlator: $correlationId)"
            )
        }
    }

    // ExoPlayer Instance
    val exoPlayer = remember {
        ExoPlayer.Builder(context).build()
    }

    DisposableEffect(Unit) {
        onDispose {
            exoPlayer.release()
        }
    }

    fun handleToggleQoD() {
        if (qodStatus == "ACTIVE" || qodStatus == "REQUESTED") {
            qodStatus = "INACTIVE"
            addTraceLog("DELETE /qod/session", "200 OK", "qosStatus: INACTIVE")
            Toast.makeText(context, "QoD Deactivated", Toast.LENGTH_SHORT).show()
            return
        }

        isQodLoading = true
        qodStatus = "REQUESTED"
        Toast.makeText(context, "Requesting Quality-on-Demand session...", Toast.LENGTH_SHORT).show()

        scope.launch {
            try {
                addTraceLog("POST /api/qod/sessions", "REQUESTED", "profile: teknofest2026, duration: 60s")
                val res = ApiClient.service.createQoDSession(QoDRequest(flowId = flowId, duration = 60))
                val body = res.body()
                if (res.isSuccessful && body != null) {
                    val returnedStatus = body.qosStatus ?: "UNAVAILABLE"
                    qodStatus = if (returnedStatus == "REQUESTED") "ACTIVE" else returnedStatus
                    addTraceLog(
                        "POST /api/qod/sessions",
                        res.code().toString(),
                        "qosStatus: ${body.qosStatus}, correlator: ${body.correlator ?: "not-returned"}"
                    )
                    val message = if (body.qosStatus == "UNAVAILABLE") {
                        "QoD unavailable; streaming limited to ${body.fallbackMaxResolution ?: "240p"}"
                    } else {
                        "QoD ${body.qosStatus}"
                    }
                    Toast.makeText(context, message, Toast.LENGTH_LONG).show()
                } else {
                    qodStatus = "ERROR"
                    addTraceLog("POST /api/qod/sessions", "HTTP ${res.code()}", "QoD request rejected")
                    Toast.makeText(context, "QoD request failed", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                qodStatus = "ERROR"
                addTraceLog("POST /api/qod/sessions", "NETWORK ERROR", e.localizedMessage ?: "timeout")
                Toast.makeText(context, "Backend unavailable; QoD was not activated", Toast.LENGTH_LONG).show()
            } finally {
                isQodLoading = false
            }
        }
    }

    // Automatic Stream Recording when Teknofest Start is pressed
    fun handleStartVideo() {
        isVideoStarted = true
        exoPlayer.setMediaItem(MediaItem.fromUri(videoUrlInput))
        exoPlayer.prepare()
        exoPlayer.playWhenReady = true

        if (sourceType == "HLS") {
            isRecording = true
            recordProgress = 0.05f
            recordStatusText = "Connecting to HLS stream..."

            scope.launch {
                try {
                    val isHighQuality = (qodStatus == "ACTIVE")
                    val file = HlsDownloader.downloadHlsToMp4(
                        context = context,
                        m3u8Url = videoUrlInput,
                        isHighQuality = isHighQuality
                    ) { progress, status ->
                        recordProgress = progress
                        recordStatusText = status
                    }
                    recordedFile = file
                    addTraceLog("HLS RECORD", "200 SUCCESS", "Saved to ${file.absolutePath} (${file.length() / 1024 / 1024} MB)")
                    Toast.makeText(context, "HLS Stream Recorded to ${file.name}!", Toast.LENGTH_SHORT).show()
                } catch (e: Exception) {
                    getOrCreateVideoFile()
                    addTraceLog("HLS RECORD", "WARN", "Using sample fallback render: ${e.message}")
                } finally {
                    isRecording = false
                }
            }
        } else {
            getOrCreateVideoFile()
        }
    }

    fun handleUploadAndRunAi() {
        isUploading = true
        isVideoUploaded = true

        scope.launch {
            try {
                val file = getOrCreateVideoFile()
                val reqBody = file.asRequestBody("video/mp4".toMediaTypeOrNull())
                val multipart = MultipartBody.Part.createFormData("file", "video.mp4", reqBody)
                val flowIdBody = flowId.toRequestBody("text/plain".toMediaTypeOrNull())
                
                val uploadRes = ApiClient.service.uploadVideo(flowIdBody, multipart)

                if (uploadRes.isSuccessful) {
                    val jobId = uploadRes.body()?.jobId
                    if (jobId != null) {
                        addTraceLog("POST /api/videos", "202 Accepted", "Job created: $jobId")
                        currentJobId = jobId
                        Toast.makeText(context, "Upload successful. Proceeding to AI Result...", Toast.LENGTH_LONG).show()
                        selectedTab = 1
                    } else {
                        addTraceLog("POST /api/videos", "ERROR", "No Job ID returned")
                        Toast.makeText(context, "Upload Error: No Job ID returned", Toast.LENGTH_LONG).show()
                    }
                } else {
                    addTraceLog("POST /api/videos", "ERROR", "Status: ${uploadRes.code()}")
                    Toast.makeText(context, "Upload Error: ${uploadRes.code()}", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                addTraceLog("POST /upload or ai-run", "FAILED", e.message ?: "Unknown error")
                Toast.makeText(context, "Operation Failed: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                isUploading = false
            }
        }
    }

    // ZIP Compression (Lossless) & Open Android Share Sheet for Lifebox
    fun handleZipAndShare() {
        val file = getOrCreateVideoFile()
        isZipping = true
        scope.launch {
            try {
                val zipFile = ZipUtils.zipVideoFile(context, file)
                zippedFile = zipFile
                addTraceLog("ZIP EXPORT", "200 SUCCESS", "Created lossless archive: ${zipFile.name}")
                Toast.makeText(context, "ZIP created! Opening Share Sheet...", Toast.LENGTH_SHORT).show()
                
                // Triggers Android Share Sheet
                ZipUtils.shareFileViaLifebox(context, zipFile)
            } catch (e: Exception) {
                Toast.makeText(context, "ZIP Error: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                isZipping = false
            }
        }
    }

    Scaffold(
        topBar = {
            if (!isVideoExpanded) {
                TopAppBar(
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("OpenGW", fontWeight = FontWeight.ExtraBold, color = Color(0xFF4338CA))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(phoneNumber, fontSize = 14.sp, color = Color(0xFF4B5563))
                        }
                    },
                    actions = {
                        IconButton(onClick = onLogout) {
                            Icon(Icons.Default.ExitToApp, contentDescription = "Logout", tint = Color(0xFFEF4444))
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
                )
            }
        },
        bottomBar = {
            if (!isVideoExpanded) {
                NavigationBar(containerColor = Color.White) {
                    NavigationBarItem(
                        selected = selectedTab == 0,
                        onClick = { selectedTab = 0 },
                        icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                        label = { Text("Home") }
                    )
                    NavigationBarItem(
                        selected = selectedTab == 1,
                        onClick = { selectedTab = 1 },
                        icon = { Icon(Icons.Default.SmartDisplay, contentDescription = "AI Result") },
                        label = { Text("AI Result") }
                    )
                    NavigationBarItem(
                        selected = selectedTab == 2,
                        onClick = { selectedTab = 2 },
                        icon = { Icon(Icons.Default.ListAlt, contentDescription = "Trace") },
                        label = { Text("Trace") }
                    )
                }
            }
        },
        containerColor = Color(0xFFF3F4F6)
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            when (selectedTab) {
                0 -> {
                    // HOME TAB: Session, QoD, Teknofest Card
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp)
                            .verticalScroll(rememberScrollState()),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // 1. Session Card
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Verified, contentDescription = null, tint = Color(0xFF10B981))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("VERIFIED SESSION", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFF10B981))
                                }
                                Spacer(modifier = Modifier.height(12.dp))
                                Text("Phone: $phoneNumber", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                Text("Flow ID: $flowId", fontSize = 12.sp, color = Color(0xFF6B7280))
                                Text("Correlation ID: $correlationId", fontSize = 12.sp, color = Color(0xFF6B7280))
                            }
                        }

                        // 2. QoD Session Card
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.Speed, contentDescription = null, tint = Color(0xFF4338CA))
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text("QOD SESSION", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B7280))
                                    }
                                    Surface(
                                        color = if (qodStatus == "ACTIVE") Color(0xFFDEF7EC) else Color(0xFFFEF3C7),
                                        shape = RoundedCornerShape(6.dp)
                                    ) {
                                        Text(
                                            text = if (qodStatus == "ACTIVE") "↑ 1080p" else "↓ 240p",
                                            color = if (qodStatus == "ACTIVE") Color(0xFF03543F) else Color(0xFF92400E),
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 12.sp,
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                Button(
                                    onClick = { handleToggleQoD() },
                                    modifier = Modifier.fillMaxWidth(),
                                    enabled = !isQodLoading,
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = if (qodStatus == "ACTIVE") Color(0xFFEF4444) else Color(0xFF4338CA)
                                    ),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    if (isQodLoading) {
                                        CircularProgressIndicator(modifier = Modifier.size(20.dp), color = Color.White)
                                    } else {
                                        Text(if (qodStatus == "ACTIVE") "Deactivate QoD" else "Activate Quality-on-Demand")
                                    }
                                }
                            }
                        }

                        // 3. Teknofest Video Stream & Upload Card
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.Videocam, contentDescription = null, tint = Color(0xFF4338CA))
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text("TEKNOFEST KARTI", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B7280))
                                    }

                                    // Compact Segmented Control (HLS vs YouTube)
                                    Row(
                                        modifier = Modifier
                                            .background(Color(0xFFE5E7EB), RoundedCornerShape(8.dp))
                                            .padding(3.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .background(
                                                    if (sourceType == "HLS") Color.White else Color.Transparent,
                                                    RoundedCornerShape(6.dp)
                                                )
                                                .clickable {
                                                    sourceType = "HLS"
                                                    videoUrlInput = "https://teknofest-arge-turkcell.ercdn.net/hls/4/pZ/faz2/faz2.smil/playlist.m3u8"
                                                }
                                                .padding(horizontal = 10.dp, vertical = 4.dp)
                                        ) {
                                            Text(
                                                "HLS",
                                                fontSize = 12.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = if (sourceType == "HLS") Color(0xFF4338CA) else Color(0xFF6B7280)
                                            )
                                        }

                                        Box(
                                            modifier = Modifier
                                                .background(
                                                    if (sourceType == "YouTube") Color.White else Color.Transparent,
                                                    RoundedCornerShape(6.dp)
                                                )
                                                .clickable {
                                                    sourceType = "YouTube"
                                                    videoUrlInput = "https://www.youtube.com/watch?v=demo"
                                                }
                                                .padding(horizontal = 10.dp, vertical = 4.dp)
                                        ) {
                                            Text(
                                                "YouTube",
                                                fontSize = 12.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = if (sourceType == "YouTube") Color(0xFF4338CA) else Color(0xFF6B7280)
                                            )
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(12.dp))

                                // Video URL Input Field
                                OutlinedTextField(
                                    value = videoUrlInput,
                                    onValueChange = { videoUrlInput = it },
                                    label = { Text("Stream / Video URL") },
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(8.dp),
                                    singleLine = true
                                )

                                Spacer(modifier = Modifier.height(12.dp))

                                // Player View (with ExoPlayer Controls & Fullscreen)
                                if (isVideoStarted) {
                                    val configuration = LocalConfiguration.current
                                    Box(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .height(if (isVideoExpanded) configuration.screenHeightDp.dp else 200.dp)
                                            .background(Color.Black, RoundedCornerShape(8.dp))
                                    ) {
                                        AndroidView(
                                            factory = { ctx ->
                                                PlayerView(ctx).apply {
                                                    player = exoPlayer
                                                    useController = true
                                                }
                                            },
                                            modifier = Modifier.fillMaxSize()
                                        )
                                    }
                                    
                                    TextButton(
                                        onClick = { 
                                            isVideoExpanded = !isVideoExpanded 
                                            val activity = context as? Activity
                                            if (isVideoExpanded) {
                                                activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_USER_LANDSCAPE
                                            } else {
                                                activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_USER_PORTRAIT
                                            }
                                        },
                                        modifier = Modifier.align(Alignment.End)
                                    ) {
                                        Icon(
                                            imageVector = if (isVideoExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                                            contentDescription = null,
                                            modifier = Modifier.size(16.dp)
                                        )
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text(if (isVideoExpanded) "Küçült" else "Büyüt", fontSize = 12.sp)
                                    }
                                    Spacer(modifier = Modifier.height(4.dp))
                                }

                                // Auto HLS Recording Progress Bar
                                if (isRecording) {
                                    LinearProgressIndicator(
                                        progress = { recordProgress },
                                        modifier = Modifier.fillMaxWidth(),
                                        color = Color(0xFF4338CA)
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(recordStatusText, fontSize = 11.sp, color = Color(0xFF4338CA))
                                    Spacer(modifier = Modifier.height(12.dp))
                                }

                                // Action 1: Start Video (Teknofest Start)
                                Button(
                                    onClick = { handleStartVideo() },
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4338CA)),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Icon(Icons.Default.PlayArrow, contentDescription = null, tint = Color.White)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(if (sourceType == "YouTube") "YouTube Start" else "Teknofest Start")
                                }

                                // Show Upload & Share Buttons once video is started!
                                // DISABLED while recording is in progress (`enabled = !isRecording`) to prevent premature clicks!
                                if (isVideoStarted) {
                                    Spacer(modifier = Modifier.height(12.dp))

                                    // Action 2: Upload Video to Backend (Disabled while recording!)
                                    Button(
                                        onClick = { handleUploadAndRunAi() },
                                        modifier = Modifier.fillMaxWidth(),
                                        enabled = !isRecording && !isUploading,
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF10B981)),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        if (isUploading) {
                                            CircularProgressIndicator(modifier = Modifier.size(20.dp), color = Color.White)
                                        } else {
                                            Icon(Icons.Default.CloudUpload, contentDescription = null, tint = Color.White)
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Text(if (isRecording) "Recording Stream... Please Wait" else "Upload Video to Backend")
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(8.dp))

                                    // Action 3: ZIP (Lossless) & Open Android Share Sheet for Lifebox (Disabled while recording!)
                                    OutlinedButton(
                                        onClick = { handleZipAndShare() },
                                        modifier = Modifier.fillMaxWidth(),
                                        enabled = !isRecording && !isZipping,
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        if (isZipping) {
                                            CircularProgressIndicator(modifier = Modifier.size(20.dp))
                                        } else {
                                            Icon(Icons.Default.Share, contentDescription = null, tint = Color(0xFF4338CA))
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Text("ZIP & Share")
                                        }
                                    }

                                    // File info badge when recording finishes
                                    if (!isRecording) {
                                        recordedFile?.let { file ->
                                            Spacer(modifier = Modifier.height(12.dp))
                                            Card(
                                                modifier = Modifier.fillMaxWidth(),
                                                colors = CardDefaults.cardColors(containerColor = Color(0xFFF3F4F6))
                                            ) {
                                                Column(modifier = Modifier.padding(12.dp)) {
                                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF10B981), modifier = Modifier.size(16.dp))
                                                        Spacer(modifier = Modifier.width(6.dp))
                                                        Text("Stream Recording Ready:", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = Color(0xFF10B981))
                                                    }
                                                    Spacer(modifier = Modifier.height(4.dp))
                                                    Text("Path: ${file.absolutePath}", fontSize = 10.sp, color = Color(0xFF4B5563))
                                                    Text("Size: ${file.length() / 1024 / 1024} MB", fontSize = 10.sp, color = Color(0xFF6B7280))

                                                    zippedFile?.let { zFile ->
                                                        Spacer(modifier = Modifier.height(4.dp))
                                                        Text("ZIP Archive: ${zFile.name} (${zFile.length() / 1024 / 1024} MB)", fontSize = 10.sp, color = Color(0xFF4338CA), fontWeight = FontWeight.Bold)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                1 -> {
                    // AI RESULT TAB (Tab 06)
                    if (!isVideoUploaded) {
                        // Friendly empty state explaining that video needs to be uploaded first
                        Scaffold(
                            topBar = {
                                TopAppBar(
                                    title = { Text("Inference Results", fontWeight = FontWeight.Bold) },
                                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
                                )
                            },
                            containerColor = Color(0xFFF3F4F6)
                        ) { innerPad ->
                            Box(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(innerPad)
                                    .padding(24.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = CardDefaults.cardColors(containerColor = Color.White),
                                    shape = RoundedCornerShape(16.dp)
                                ) {
                                    Column(
                                        modifier = Modifier.padding(32.dp),
                                        horizontalAlignment = Alignment.CenterHorizontally
                                    ) {
                                        Icon(Icons.Default.CloudUpload, contentDescription = null, tint = Color(0xFF4338CA), modifier = Modifier.size(48.dp))
                                        Spacer(modifier = Modifier.height(16.dp))
                                        Text("No Video Uploaded Yet", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Text(
                                            "Please start a video and click 'Upload Video to Backend' on the Home tab first.",
                                            fontSize = 13.sp,
                                            color = Color(0xFF6B7280),
                                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                                        )
                                        Spacer(modifier = Modifier.height(24.dp))
                                        Button(
                                            onClick = { selectedTab = 0 },
                                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4338CA))
                                        ) {
                                            Text("Go to Home Tab")
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        AIResultScreen(jobId = currentJobId, onBack = { selectedTab = 0 })
                    }
                }

                2 -> {
                    // TRACE TAB (Tab 07)
                    TraceScreen(
                        flowId = flowId,
                        correlationId = correlationId,
                        phoneNumber = phoneNumber,
                        qodStatus = qodStatus,
                        traceLogs = traceLogs
                    )
                }
            }
        }
    }
}
