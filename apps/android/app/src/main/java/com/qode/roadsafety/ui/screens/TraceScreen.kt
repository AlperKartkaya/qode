package com.qode.roadsafety.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class TraceLogItem(
    val timestamp: String,
    val endpoint: String,
    val status: String,
    val detail: String
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TraceScreen(
    flowId: String,
    correlationId: String,
    phoneNumber: String,
    qodStatus: String,
    traceLogs: List<TraceLogItem>
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("API Trace & Logs", fontWeight = FontWeight.Bold) },
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
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Flow & Correlation Info Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.BugReport, contentDescription = null, tint = Color(0xFF4338CA))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("OPEN GATEWAY TRACE SESSION", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFF4338CA))
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    Text("MSISDN: $phoneNumber", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Text("Flow ID: $flowId", fontSize = 13.sp, color = Color(0xFF4B5563))
                    Text("Correlation ID: $correlationId", fontSize = 13.sp, color = Color(0xFF4B5563))
                    Text("QoD Status: $qodStatus", fontSize = 13.sp, color = Color(0xFF4B5563))
                }
            }

            // Real-Time Trace Logs Console
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("API REQUEST TRACE LOGS", fontWeight = FontWeight.Bold, fontSize = 13.sp, color = Color(0xFF6B7280))
                    Spacer(modifier = Modifier.height(12.dp))

                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFF111827), RoundedCornerShape(8.dp))
                            .padding(12.dp)
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (traceLogs.isEmpty()) {
                                Text("[INFO] Waiting for OpenGateway API calls...", color = Color.Gray, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                            } else {
                                traceLogs.forEach { item ->
                                    Column {
                                        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                                            Text("[${item.timestamp}] ${item.endpoint}", color = Color(0xFF38BDF8), fontFamily = FontFamily.Monospace, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                            Text(item.status, color = if (item.status.contains("200") || item.status.contains("202") || item.status.contains("201")) Color(0xFF34D399) else Color(0xFFF87171), fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                                        }
                                        Text(item.detail, color = Color(0xFFD1D5DB), fontFamily = FontFamily.Monospace, fontSize = 10.sp)
                                        Divider(color = Color(0xFF1F2937), modifier = Modifier.padding(vertical = 4.dp))
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
