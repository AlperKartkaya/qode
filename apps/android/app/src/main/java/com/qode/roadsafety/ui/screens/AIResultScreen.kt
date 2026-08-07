package com.qode.roadsafety.ui.screens

import android.widget.Toast
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.gson.GsonBuilder
import com.qode.roadsafety.data.api.ApiClient
import com.qode.roadsafety.data.model.AiResultResponse
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.isActive
import androidx.compose.ui.text.style.TextAlign
import java.io.File
import android.content.Intent

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AIResultScreen(
    jobId: String?,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var status by remember { mutableStateOf("PROCESSING") }
    var simulatedProgress by remember { mutableFloatStateOf(0.1f) }
    var elapsedTimeSeconds by remember { mutableLongStateOf(0L) }
    var stepMessage by remember { mutableStateOf("Initializing AI Analysis...") }
    var aiResultResponse by remember { mutableStateOf<AiResultResponse?>(null) }
    var isRefreshing by remember { mutableStateOf(false) }
    var jsonFile by remember { mutableStateOf<File?>(null) }

    val animatedProgress by animateFloatAsState(
        targetValue = simulatedProgress,
        label = "ProgressAnimation"
    )

    fun fetchResult(isManual: Boolean = false) {
        if (jobId == null) {
            status = "FAILED"
            stepMessage = "No Job ID provided."
            return
        }
        if (isManual) isRefreshing = true
        scope.launch {
            try {
                val res = ApiClient.service.getJobStatus(jobId)
                if (res.isSuccessful && res.body() != null) {
                    val body = res.body()!!
                    status = body.status
                    if (status == "DONE" || status == "FAILED") {
                        simulatedProgress = 1.0f
                    }
                    stepMessage = "Job status: ${body.status}"
                    
                    if (status == "DONE") {
                        val resultRes = ApiClient.service.getAiResult(jobId)
                        if (resultRes.isSuccessful && resultRes.body() != null) {
                            aiResultResponse = AiResultResponse(
                                status = "DONE",
                                progress = 1.0f,
                                message = "Analysis complete",
                                result = resultRes.body()!!
                            )
                        } else {
                            status = "FAILED"
                            stepMessage = "Result fetch failed"
                        }
                    } else if (status == "FAILED") {
                        stepMessage = "Job failed: ${body.failureCode}"
                    }
                    
                    if (isManual) Toast.makeText(context, "Status updated", Toast.LENGTH_SHORT).show()
                } else {
                    status = "FAILED"
                    if (isManual) Toast.makeText(context, "Error: ${res.code()}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                status = "FAILED"
                if (isManual) Toast.makeText(context, "Connection Error: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                if (isManual) isRefreshing = false
            }
        }
    }

    // Auto-polling and Simulated Progress Loop
    LaunchedEffect(status) {
        if (status == "PROCESSING" || status == "QUEUED" || status == "IDLE") {
            val startTime = System.currentTimeMillis() - (elapsedTimeSeconds * 1000)
            while (isActive) {
                delay(1000)
                elapsedTimeSeconds = (System.currentTimeMillis() - startTime) / 1000
                // Asymptotic progress towards 0.99
                val target = 1f - (1f / (1f + elapsedTimeSeconds * 0.05f))
                if (target > simulatedProgress) {
                    simulatedProgress = target.coerceAtMost(0.99f)
                }
                // Poll every ~1.5s (but we are in a 1s loop, so just poll every 2s)
                if (elapsedTimeSeconds % 2 == 0L) {
                    fetchResult()
                }
            }
        }
    }

    LaunchedEffect(Unit) {
        fetchResult()
    }

    LaunchedEffect(aiResultResponse) {
        val result = aiResultResponse?.result
        if (result != null) {
            val gson = GsonBuilder().create()
            val resultStr = gson.toJson(result)
            val dir = android.os.Environment.getExternalStoragePublicDirectory(android.os.Environment.DIRECTORY_DOWNLOADS)
            val qodeDir = File(dir, "QoDe").apply { mkdirs() }
            val file = File(qodeDir, "results.json")
            file.writeText(resultStr)
            
            val md = java.security.MessageDigest.getInstance("MD5")
            val hashStr = md.digest(resultStr.toByteArray()).joinToString("") { "%02x".format(it) }
            val md5File = File(qodeDir, "results.json.md5")
            md5File.writeText(hashStr)
            
            jsonFile = file
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Inference Results", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { fetchResult(true) }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = Color(0xFF4338CA))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        },
        containerColor = Color(0xFFF3F4F6)
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Text("Computer Vision Analysis", fontSize = 14.sp, color = Color(0xFF6B7280))

            Spacer(modifier = Modifier.height(16.dp))

            when (status) {
                "PROCESSING", "UPLOADED", "IDLE" -> {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(32.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column {
                                    Text("Analyzing Video Frames", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color(0xFF111827))
                                    val minutes = elapsedTimeSeconds / 60
                                    val seconds = elapsedTimeSeconds % 60
                                    Text(String.format("Elapsed: %02d:%02d", minutes, seconds), fontSize = 13.sp, color = Color(0xFF6B7280))
                                }
                                Text("${(animatedProgress * 100).toInt()}%", fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, color = Color(0xFF4338CA))
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            // Animated Progress Bar
                            LinearProgressIndicator(
                                progress = { animatedProgress },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(10.dp),
                                color = Color(0xFF4338CA),
                                trackColor = Color(0xFFE5E7EB)
                            )

                            Spacer(modifier = Modifier.height(16.dp))

                            Text(
                                text = stepMessage,
                                fontSize = 13.sp,
                                color = Color(0xFF6B7280),
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }

                "FAILED" -> {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(40.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Icon(Icons.Default.Warning, contentDescription = null, tint = Color(0xFFEF4444), modifier = Modifier.size(48.dp))
                            Spacer(modifier = Modifier.height(16.dp))
                            Text("Inference Failed", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color(0xFFEF4444))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(stepMessage, fontSize = 14.sp, color = Color.Gray, textAlign = TextAlign.Center)
                            Spacer(modifier = Modifier.height(16.dp))
                            Button(
                                onClick = { fetchResult(true) },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFEF4444))
                            ) {
                                Text("Retry Fetching")
                            }
                        }
                    }
                }

                "DONE" -> {
                    val result = aiResultResponse?.result

                    // Success Banner
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFDEF7EC)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF10B981))
                            Spacer(modifier = Modifier.width(12.dp))
                            Text("Analysis Complete (100%)", fontWeight = FontWeight.Bold, color = Color(0xFF03543F))
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Vehicle Details Card
                    result?.aracBilgisi?.let { vehicle ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            shape = RoundedCornerShape(16.dp)
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.DirectionsCar, contentDescription = null, tint = Color(0xFF4338CA))
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Text("Vehicle Details", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                                }
                                Spacer(modifier = Modifier.height(16.dp))

                                DetailRow("Type", vehicle.tip)
                                DetailRow("Plate", vehicle.plaka)
                                DetailRow("Color", vehicle.renk)
                                DetailRow("Confidence", "${(vehicle.confidenceScore * 100).toInt()}%")
                            }
                        }

                        Spacer(modifier = Modifier.height(16.dp))
                    }

                    // Timeline Detections Card
                    result?.tespitler?.let { detections ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            shape = RoundedCornerShape(16.dp)
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.Timeline, contentDescription = null, tint = Color(0xFF4338CA))
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Text("Timeline Detections", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                                    }
                                    Surface(
                                        color = Color(0xFFEEF2FF),
                                        shape = RoundedCornerShape(12.dp)
                                    ) {
                                        Text(
                                            "${detections.size}",
                                            color = Color(0xFF4338CA),
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 12.sp,
                                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                detections.forEach { item ->
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 8.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(44.dp)
                                                .background(Color(0xFFF3F4F6), CircleShape),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Text("${item.zamanSaniye.toInt()}s", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color(0xFF4B5563))
                                        }

                                        Spacer(modifier = Modifier.width(16.dp))

                                        Column(modifier = Modifier.weight(1f)) {
                                            Text(item.kategori, fontSize = 12.sp, color = Color(0xFF6B7280))
                                            Text(item.etiket, fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF111827))
                                        }

                                        Surface(
                                            color = Color(0xFFECFCCB),
                                            shape = RoundedCornerShape(8.dp)
                                        ) {
                                            Text(
                                                "${(item.confidenceScore * 100).toInt()}%",
                                                color = Color(0xFF3F6212),
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 12.sp,
                                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                            )
                                        }
                                    }
                                    HorizontalDivider(color = Color(0xFFF3F4F6))
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(16.dp))
                    }

                    // Raw JSON Card
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Column(modifier = Modifier.padding(20.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Code, contentDescription = null, tint = Color(0xFF4338CA))
                                Spacer(modifier = Modifier.width(10.dp))
                                Text("Raw JSON Results", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            val gson = remember { GsonBuilder().create() }
                            val singleLineJson = remember(aiResultResponse) { gson.toJson(result) }
                            val md5Hash = remember(singleLineJson) {
                                val md = java.security.MessageDigest.getInstance("MD5")
                                md.digest(singleLineJson.toByteArray()).joinToString("") { "%02x".format(it) }
                            }

                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(Color(0xFF111827), RoundedCornerShape(12.dp))
                                    .padding(16.dp)
                            ) {
                                Column {
                                    Text(
                                        text = singleLineJson,
                                        color = Color(0xFF34D399),
                                        fontFamily = FontFamily.Monospace,
                                        fontSize = 11.sp
                                    )
                                    Spacer(modifier = Modifier.height(12.dp))
                                    HorizontalDivider(color = Color(0xFF374151))
                                    Spacer(modifier = Modifier.height(12.dp))
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Icon(Icons.Default.Fingerprint, contentDescription = null, tint = Color(0xFF9CA3AF), modifier = Modifier.size(14.dp))
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Text(
                                                text = "MD5 Fingerprint: $md5Hash",
                                                color = Color(0xFF9CA3AF),
                                                fontFamily = FontFamily.Monospace,
                                                fontSize = 10.sp
                                            )
                                        }
                                        IconButton(
                                            onClick = {
                                                val clipboard = context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                                                val clip = android.content.ClipData.newPlainText("MD5 Hash", md5Hash)
                                                clipboard.setPrimaryClip(clip)
                                                Toast.makeText(context, "Kopyalandı!", Toast.LENGTH_SHORT).show()
                                            },
                                            modifier = Modifier.size(24.dp)
                                        ) {
                                            Icon(Icons.Default.ContentCopy, contentDescription = "Copy Hash", tint = Color(0xFF9CA3AF), modifier = Modifier.size(14.dp))
                                        }
                                    }
                                }
                            }
                            
                            jsonFile?.let { file ->
                                Spacer(modifier = Modifier.height(16.dp))
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF3F4F6))
                                ) {
                                    Column(modifier = Modifier.padding(12.dp)) {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF10B981), modifier = Modifier.size(16.dp))
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Text("results.json Kaydedildi", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = Color(0xFF10B981))
                                        }
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text("Konum: ${file.absolutePath}", fontSize = 10.sp, color = Color(0xFF4B5563))
                                        
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Button(
                                            onClick = {
                                                val uri = androidx.core.content.FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
                                                val shareIntent = Intent().apply {
                                                    action = Intent.ACTION_SEND
                                                    type = "application/json"
                                                    putExtra(Intent.EXTRA_STREAM, uri)
                                                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                                }
                                                context.startActivity(Intent.createChooser(shareIntent, "JSON Sonucunu Paylaş"))
                                            },
                                            modifier = Modifier.fillMaxWidth(),
                                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4338CA)),
                                            shape = RoundedCornerShape(8.dp)
                                        ) {
                                            Icon(Icons.Default.Share, contentDescription = null, tint = Color.White)
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Text("Sonucu Paylaş")
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
}

@Composable
private fun DetailRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = Color(0xFF6B7280), fontSize = 15.sp)
        Text(value, fontWeight = FontWeight.Bold, fontSize = 15.sp, color = Color(0xFF111827))
    }
    HorizontalDivider(color = Color(0xFFF3F4F6))
}
