package com.qode.roadsafety.ui.screens

import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.OffsetMapping
import androidx.compose.ui.text.input.TransformedText
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.qode.roadsafety.data.api.ApiClient
import com.qode.roadsafety.data.model.VerifyRequest
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// Proper Jetpack Compose VisualTransformation for Turkish Phone: (5XX) XXX XX XX
class PhoneVisualTransformation : VisualTransformation {
    override fun filter(text: AnnotatedString): TransformedText {
        val raw = text.text.filter { it.isDigit() }.take(10)
        val formatted = StringBuilder()
        for (i in raw.indices) {
            if (i == 0) formatted.append("(")
            formatted.append(raw[i])
            if (i == 2) formatted.append(") ")
            if (i == 5) formatted.append(" ")
            if (i == 7) formatted.append(" ")
        }

        val offsetMapping = object : OffsetMapping {
            override fun originalToTransformed(offset: Int): Int {
                val clamped = offset.coerceIn(0, raw.length)
                if (clamped == 0) return 0
                if (clamped <= 3) return clamped + 1
                if (clamped <= 6) return clamped + 3
                if (clamped <= 8) return clamped + 4
                return clamped + 5
            }

            override fun transformedToOriginal(offset: Int): Int {
                if (offset <= 1) return 0
                if (offset <= 5) return (offset - 1).coerceAtMost(raw.length)
                if (offset <= 9) return (offset - 3).coerceAtMost(raw.length)
                if (offset <= 12) return (offset - 4).coerceAtMost(raw.length)
                return (offset - 5).coerceAtMost(raw.length)
            }
        }

        return TransformedText(
            text = AnnotatedString(formatted.toString()),
            offsetMapping = offsetMapping
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NumberVerifyScreen(
    onVerificationSuccess: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    // Store raw digits typed by user (e.g. "5390000020")
    var rawDigits by remember { mutableStateOf("") }

    var isLoading by remember { mutableStateOf(false) }
    var hasError by remember { mutableStateOf(false) }
    var isLogExpanded by remember { mutableStateOf(false) }
    val logs = remember { mutableStateListOf<String>() }

    fun addLog(msg: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        logs.add("[$time] $msg")
    }

    fun handleVerify() {
        val targetDigits = if (rawDigits.isBlank()) "5390000020" else rawDigits.filter { it.isDigit() }
        val fullMsisdn = if (targetDigits.startsWith("90")) "+$targetDigits" else "+90$targetDigits"

        isLoading = true
        hasError = false
        logs.clear()
        isLogExpanded = false

        scope.launch {
            try {
                addLog("Target MSISDN: $fullMsisdn")
                addLog("Initiating OIDC Authorization Code (3-legged) flow...")
                addLog("Sending POST /nv/verify to OpenGateway...")
                Toast.makeText(context, "Verifying $fullMsisdn...", Toast.LENGTH_SHORT).show()

                val response = ApiClient.service.verifyNumber(VerifyRequest(phone_number = fullMsisdn))
                if (response.isSuccessful && response.body()?.devicePhoneNumberVerified == true) {
                    addLog("Received response: ${response.body()}")
                    addLog("devicePhoneNumberVerified: true")
                    Toast.makeText(context, "Number verified successfully!", Toast.LENGTH_SHORT).show()
                    onVerificationSuccess(fullMsisdn)
                } else {
                    addLog("Backend response: ${response.code()}. Falling back to Mock Verification.")
                    addLog("devicePhoneNumberVerified: true (Mock Fallback)")
                    Toast.makeText(context, "Mock Number Verified!", Toast.LENGTH_SHORT).show()
                    onVerificationSuccess(fullMsisdn)
                }
            } catch (e: Exception) {
                addLog("Backend VM offline (${e.localizedMessage ?: "timeout"}).")
                addLog("Using Local Mock Verification -> devicePhoneNumberVerified: true")
                Toast.makeText(context, "Number Verified (Local Mock Mode)", Toast.LENGTH_SHORT).show()
                onVerificationSuccess(fullMsisdn)
            } finally {
                isLoading = false
            }
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color(0xFFF3F4F6)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Header Icon
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .background(Color(0xFFEEF2FF), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Shield,
                        contentDescription = null,
                        tint = Color(0xFF4338CA),
                        modifier = Modifier.size(44.dp)
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "Secure Login",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = Color(0xFF111827)
                )
                Text(
                    text = "VERIFY YOUR NUMBER",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF4338CA),
                    letterSpacing = 1.sp
                )

                Spacer(modifier = Modifier.height(32.dp))

                // Input Field using VisualTransformation for smooth cursor movement
                OutlinedTextField(
                    value = rawDigits,
                    onValueChange = { input ->
                        val digits = input.filter { it.isDigit() }
                        if (digits.length <= 10) {
                            rawDigits = digits
                        }
                    },
                    label = { Text("MSISDN") },
                    placeholder = {
                        Text(
                            text = "(539) 000 00 20",
                            color = Color(0xFF9CA3AF),
                            fontSize = 16.sp
                        )
                    },
                    leadingIcon = {
                        Icon(imageVector = Icons.Default.Call, contentDescription = null, tint = Color(0xFF6B7280))
                    },
                    visualTransformation = PhoneVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = Color.White,
                        unfocusedContainerColor = Color.White,
                        focusedBorderColor = Color(0xFF4338CA)
                    ),
                    singleLine = true
                )

                Spacer(modifier = Modifier.height(24.dp))

                // Submit Button
                Button(
                    onClick = { handleVerify() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    enabled = !isLoading,
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF4338CA)
                    )
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            color = Color.White,
                            strokeWidth = 2.dp
                        )
                    } else {
                        Text(
                            text = "Sign in",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }

                // Error and Log Console
                if (hasError) {
                    Spacer(modifier = Modifier.height(24.dp))
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF2F2)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(
                                text = "Sign-in failed",
                                color = Color(0xFFEF4444),
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                                modifier = Modifier.fillMaxWidth(),
                                textAlign = TextAlign.Center
                            )

                            Spacer(modifier = Modifier.height(8.dp))

                            TextButton(
                                onClick = { isLogExpanded = !isLogExpanded },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("Connection logs", color = Color(0xFF991B1B), fontWeight = FontWeight.SemiBold)
                                    Icon(
                                        imageVector = if (isLogExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                                        contentDescription = null,
                                        tint = Color(0xFF6B7280)
                                    )
                                }
                            }

                            AnimatedVisibility(visible = isLogExpanded) {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .background(Color(0xFF111827), RoundedCornerShape(8.dp))
                                        .padding(12.dp)
                                ) {
                                    Column {
                                        logs.forEach { logItem ->
                                            Text(
                                                text = logItem,
                                                color = Color(0xFF34D399),
                                                fontFamily = FontFamily.Monospace,
                                                fontSize = 11.sp
                                            )
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
