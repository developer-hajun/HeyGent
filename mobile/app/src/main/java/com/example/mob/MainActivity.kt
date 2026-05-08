package com.example.mob

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.mob.common.AppDrawer
import com.example.mob.feature.auth.LoginScreen
import com.example.mob.feature.chat.ChatScreen
import com.example.mob.feature.health.HealthViewModel
import com.example.mob.feature.home.HomeScreen
import com.example.mob.feature.profile.ProfileScreen
import com.example.mob.ui.theme.MOBTheme
import com.example.mob.ui.theme.NavyPrimary
import com.example.mob.ui.theme.TextSecondary
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import androidx.compose.ui.platform.LocalContext
import android.app.Activity
import androidx.compose.runtime.LaunchedEffect
import android.util.Log
import android.os.Build
import androidx.core.content.ContextCompat
import com.kakao.sdk.common.KakaoSdk
import com.kakao.sdk.common.util.Utility
import com.example.mob.voice.WakeWordForegroundService

private sealed class Screen(val route: String, val label: String, val icon: ImageVector) {
    data object Chat    : Screen("chat",    "Chat",    Icons.AutoMirrored.Filled.Chat)
    data object Home    : Screen("home",    "Home",    Icons.Default.Home)
    data object Profile : Screen("profile", "Profile", Icons.Default.Person)
}

private val bottomNavScreens = listOf(Screen.Chat, Screen.Home, Screen.Profile)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        KakaoSdk.init(this, getString(R.string.kakao_app_key))
        Log.d("KAKAO_KEY_HASH", Utility.getKeyHash(this))
        enableEdgeToEdge()
        setContent {
            MOBTheme {
                var splashDone by remember { mutableStateOf(false) }
                var isLoggedIn by remember { mutableStateOf(false) }
                WakeWordServicePermissionEffect()

                LaunchedEffect(Unit) {
                    delay(1800)
                    splashDone = true
                }

                when {
                    !splashDone -> SplashScreen()
                    !isLoggedIn -> LoginScreen(onLoginSuccess = { isLoggedIn = true })
                    else        -> MainApp(onLogout = { isLoggedIn = false })
                }
            }
        }
    }
}

@Composable
private fun WakeWordServicePermissionEffect() {
    val context = LocalContext.current
    val permissions = remember {
        buildList {
            add(Manifest.permission.RECORD_AUDIO)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }.toTypedArray()
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants[Manifest.permission.RECORD_AUDIO] == true) {
            WakeWordForegroundService.start(context)
        }
    }

    LaunchedEffect(Unit) {
        val hasAudioPermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        if (hasAudioPermission) {
            WakeWordForegroundService.start(context)
        } else {
            permissionLauncher.launch(permissions)
        }

        if (!Settings.canDrawOverlays(context)) {
            context.startActivity(
                Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:${context.packageName}")
                )
            )
        }
    }
}

@Composable
private fun SplashScreen() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = "HEYGENT",
            color = Color.White,
            fontSize = 34.sp,
            fontWeight = FontWeight.ExtraBold,
            letterSpacing = 5.sp
        )
    }
}

@Composable
private fun MainApp(onLogout: () -> Unit) {
    val context = LocalContext.current
    val healthViewModel = remember { HealthViewModel(context) }

    val navController = rememberNavController()
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    // 주기적 동기화 시작
    LaunchedEffect(Unit) {
        healthViewModel.startPeriodicSync()
        // 권한이 없으면 요청 (최초 1회)
        if (!healthViewModel.syncState.value.let { it is HealthViewModel.HealthSyncState.Success }) {
            (context as? Activity)?.let { healthViewModel.requestPermissions(it) }
        }
    }

    // 앱 세션 동안 유지 (앱 재실행 시 초기화됨)
    var activeChatSessionId by remember { mutableStateOf<Int?>(null) }
    var agentName by remember { mutableStateOf("Jarvis") }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            AppDrawer(
                onClose = { scope.launch { drawerState.close() } },
                agentName = agentName,
                onNewChat = {
                    activeChatSessionId = 0
                    navController.navigate(Screen.Chat.route) { launchSingleTop = true }
                    scope.launch { drawerState.close() }
                },
                onHistoryItemClick = { sessionId ->
                    activeChatSessionId = sessionId
                    navController.navigate(Screen.Chat.route) { launchSingleTop = true }
                    scope.launch { drawerState.close() }
                }
            )
        }
    ) {
        Scaffold(
            bottomBar = { AppBottomBar(navController) }
        ) { innerPadding ->
            val bottomPadding = innerPadding.calculateBottomPadding()
            val onMenuClick: () -> Unit = { scope.launch { drawerState.open() } }

            NavHost(
                navController = navController,
                startDestination = Screen.Home.route,
                enterTransition = { EnterTransition.None },
                exitTransition  = { ExitTransition.None },
                popEnterTransition = { EnterTransition.None },
                popExitTransition  = { ExitTransition.None }
            ) {
                composable(Screen.Chat.route) {
                    ChatScreen(
                        onMenuClick = onMenuClick,
                        activeChatSessionId = activeChatSessionId,
                        onActiveChatSessionChange = { activeChatSessionId = it },
                        agentName = agentName,
                        bottomPadding = bottomPadding
                    )
                }
                composable(Screen.Home.route) {
                    HomeScreen(
                        onMenuClick = onMenuClick,
                        bottomPadding = bottomPadding
                    )
                }
                composable(Screen.Profile.route) {
                    ProfileScreen(
                        onMenuClick = onMenuClick,
                        bottomPadding = bottomPadding,
                        onLogout = onLogout,
                        agentName = agentName,
                        onAgentNameChange = { agentName = it },
                        healthViewModel = healthViewModel
                    )
                }
            }
        }
    }
}

@Composable
private fun AppBottomBar(navController: NavHostController) {
    val currentRoute = navController.currentBackStackEntryAsState().value?.destination?.route

    NavigationBar(containerColor = Color.White, tonalElevation = 0.dp) {
        bottomNavScreens.forEach { screen ->
            val selected = currentRoute == screen.route
            NavigationBarItem(
                selected = selected,
                onClick = {
                    navController.navigate(screen.route) {
                        popUpTo(Screen.Home.route) { inclusive = false }
                        launchSingleTop = true
                    }
                },
                icon = { Icon(screen.icon, contentDescription = screen.label) },
                label = { Text(screen.label, fontSize = 11.sp) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = NavyPrimary,
                    selectedTextColor = NavyPrimary,
                    unselectedIconColor = TextSecondary,
                    unselectedTextColor = TextSecondary,
                    indicatorColor = Color(0xFFE8EAF0)
                )
            )
        }
    }
}
