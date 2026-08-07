package com.qode.roadsafety

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.Crossfade
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.qode.roadsafety.ui.screens.HomeScreen
import com.qode.roadsafety.ui.screens.NumberVerifyScreen

enum class Screen {
    NUMBER_VERIFY,
    HOME
}

class MainActivity : ComponentActivity() {
    private var authorizedFlowId by mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        acceptAuthorizationCallback(intent)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    var currentScreen by remember { mutableStateOf(Screen.NUMBER_VERIFY) }
                    var verifiedPhone by remember { mutableStateOf("+905390000020") }
                    var verifiedFlowId by remember { mutableStateOf("") }
                    var verificationCorrelator by remember { mutableStateOf<String?>(null) }

                    Crossfade(targetState = currentScreen, label = "ScreenTransition") { screen ->
                        when (screen) {
                            Screen.NUMBER_VERIFY -> {
                                NumberVerifyScreen(
                                    authorizedFlowId = authorizedFlowId,
                                    onAuthorizationConsumed = { authorizedFlowId = null },
                                    onVerificationSuccess = { phone, flowId, correlator ->
                                        verifiedPhone = phone
                                        verifiedFlowId = flowId
                                        verificationCorrelator = correlator
                                        currentScreen = Screen.HOME
                                    }
                                )
                            }
                            Screen.HOME -> {
                                HomeScreen(
                                    phoneNumber = verifiedPhone,
                                    flowId = verifiedFlowId,
                                    verificationCorrelator = verificationCorrelator,
                                    onLogout = {
                                        currentScreen = Screen.NUMBER_VERIFY
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        acceptAuthorizationCallback(intent)
    }

    private fun acceptAuthorizationCallback(intent: Intent?) {
        val uri = intent?.data ?: return
        if (uri.scheme == "qode" && uri.host == "auth" && uri.path == "/callback") {
            authorizedFlowId = uri.getQueryParameter("flowId")
        }
    }
}
