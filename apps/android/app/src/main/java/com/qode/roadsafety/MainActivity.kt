package com.qode.roadsafety

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
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    var currentScreen by remember { mutableStateOf(Screen.NUMBER_VERIFY) }
                    var verifiedPhone by remember { mutableStateOf("+905390000020") }

                    Crossfade(targetState = currentScreen, label = "ScreenTransition") { screen ->
                        when (screen) {
                            Screen.NUMBER_VERIFY -> {
                                NumberVerifyScreen(
                                    onVerificationSuccess = { phone ->
                                        verifiedPhone = phone
                                        currentScreen = Screen.HOME
                                    }
                                )
                            }
                            Screen.HOME -> {
                                HomeScreen(
                                    phoneNumber = verifiedPhone,
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
}
