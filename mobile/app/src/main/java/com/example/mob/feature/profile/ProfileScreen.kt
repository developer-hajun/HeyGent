package com.example.mob.feature.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalContext
import com.example.mob.common.AppTopBar
import com.example.mob.data.remote.RetrofitClient
import com.example.mob.data.remote.UpdateUserRequest
import com.example.mob.feature.health.HealthViewModel
import com.example.mob.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(
    onMenuClick: () -> Unit,
    bottomPadding: Dp = 0.dp,
    onLogout: () -> Unit = {},
    agentName: String = "Jarvis",
    onAgentNameChange: (String) -> Unit = {},
    healthViewModel: HealthViewModel? = null
) {
    val context = LocalContext.current
    val activity = context as? android.app.Activity
    
    var showSettings by remember { mutableStateOf(false) }
    var agentCallName by remember { mutableStateOf("") }
    var isLoadingProfile by remember { mutableStateOf(true) }
    var isEditingName by remember { mutableStateOf(false) }
    var nameInput by remember { mutableStateOf("") }
    var isSavingName by remember { mutableStateOf(false) }
    var saveNameError by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        try {
            val response = RetrofitClient.userApiService.getMe()
            if (response.status == 200) {
                agentCallName = response.data?.nickname ?: ""
            }
        } catch (_: Exception) {
        } finally {
            isLoadingProfile = false
        }
    }
    val saveName = {
        val trimmed = nameInput.trim()
        if (trimmed.isNotBlank()) {
            scope.launch {
                isSavingName = true
                saveNameError = null
                try {
                    val response = RetrofitClient.userApiService.updateMe(
                        UpdateUserRequest(nickname = trimmed)
                    )
                    if (response.status == 200) {
                        agentCallName = response.data?.nickname ?: trimmed
                        isEditingName = false
                    } else {
                        saveNameError = response.message
                    }
                } catch (e: Exception) {
                    saveNameError = "저장에 실패했습니다."
                } finally {
                    isSavingName = false
                }
            }
        }
    }

    Scaffold(
        topBar = {
            AppTopBar(
                title = "HEYGENT",
                onMenuClick = onMenuClick,
                actions = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(end = 8.dp),
                    ) {
                        Icon(
                            Icons.Default.Computer,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Box(
                            modifier =
                                Modifier
                                    .size(6.dp)
                                    .clip(CircleShape)
                                    .background(ActiveGreen),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("PC ON", color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                    }
                },
            )
        },
        containerColor = AppBackground,
        contentWindowInsets = WindowInsets(0),
    ) { innerPadding ->
        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .padding(top = innerPadding.calculateTopPadding())
                    .verticalScroll(rememberScrollState()),
        ) {
            // Hero section
            Box(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .background(NavyPrimary)
                        .padding(vertical = 32.dp),
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        modifier =
                            Modifier
                                .size(88.dp)
                                .clip(CircleShape)
                                .background(Color.White.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            Icons.Default.Person,
                            contentDescription = null,
                            tint = Color.White.copy(alpha = 0.7f),
                            modifier = Modifier.size(52.dp),
                        )
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                    if (isLoadingProfile) {
                        CircularProgressIndicator(
                            color = Color.White.copy(alpha = 0.7f),
                            modifier = Modifier.size(24.dp),
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Text(
                            agentCallName.ifBlank { "사용자" },
                            color = Color.White,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            ProfileSectionTitle("계정")
            ProfileCard {
                Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
                    Text(
                        "어떻게 불러드릴까요?",
                        fontSize = 12.sp,
                        color = TextSecondary,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    if (isEditingName) {
                        Column {
                            OutlinedTextField(
                                value = nameInput,
                                onValueChange = { nameInput = it },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true,
                                enabled = !isSavingName,
                                shape = RoundedCornerShape(10.dp),
                                textStyle =
                                    TextStyle(
                                        fontSize = 15.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = TextPrimary,
                                    ),
                                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                                keyboardActions = KeyboardActions(onDone = { saveName() }),
                                trailingIcon = {
                                    if (isSavingName) {
                                        CircularProgressIndicator(
                                            modifier = Modifier.size(24.dp),
                                            strokeWidth = 2.dp,
                                            color = NavyPrimary,
                                        )
                                    } else {
                                        IconButton(onClick = { saveName() }) {
                                            Icon(
                                                Icons.Default.Check,
                                                contentDescription = "저장",
                                                tint = NavyPrimary,
                                            )
                                        }
                                    }
                                },
                                colors =
                                    OutlinedTextFieldDefaults.colors(
                                        focusedBorderColor = NavyPrimary,
                                        unfocusedBorderColor = DividerColor,
                                    ),
                            )
                            if (saveNameError != null) {
                                Text(
                                    text = saveNameError!!,
                                    fontSize = 12.sp,
                                    color = HealthRed,
                                    modifier = Modifier.padding(top = 4.dp, start = 4.dp),
                                )
                            }
                        }
                    } else {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                agentCallName,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Medium,
                                color = TextPrimary,
                            )
                            IconButton(
                                onClick = {
                                    nameInput = agentCallName
                                    isEditingName = true
                                },
                                modifier = Modifier.size(32.dp),
                            ) {
                                Icon(
                                    Icons.Default.Edit,
                                    contentDescription = "수정",
                                    tint = TextSecondary,
                                    modifier = Modifier.size(18.dp),
                                )
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            ProfileSectionTitle("건강 데이터 동기화")
            ProfileCard {
                var syncEnabled by remember { mutableStateOf(true) }
                Column {
                    Row(
                        modifier =
                            Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            modifier =
                                Modifier
                                    .size(42.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(TodoGreen),
                            contentAlignment = Alignment.Center,
                        ) {
                            Icon(
                                Icons.Default.Favorite,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(24.dp),
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                "Samsung Health",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Medium,
                                color = TextPrimary,
                            )
                            Text(
                                if (syncEnabled) "연결됨" else "연결 해제됨",
                                fontSize = 12.sp,
                                color = TextSecondary,
                            )
                        }
                        Switch(
                            checked = syncEnabled,
                            onCheckedChange = { 
                                syncEnabled = it 
                                if (it) {
                                    healthViewModel?.startPeriodicSync()
                                    activity?.let { act -> healthViewModel?.requestPermissions(act) }
                                } else {
                                    healthViewModel?.stopPeriodicSync()
                                }
                            },
                            colors =
                                SwitchDefaults.colors(
                                    checkedThumbColor = Color.White,
                                    checkedTrackColor = TodoGreen,
                                ),
                        )
                    }
                    if (syncEnabled) {
                        Text(
                            "마지막 동기화: 방금 전",
                            fontSize = 12.sp,
                            color = TextSecondary,
                            modifier = Modifier.padding(start = 16.dp, bottom = 14.dp),
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            ProfileSectionTitle("설정 및 작업")
            ProfileCard {
                Column {
                    ActionRow(
                        icon = Icons.Default.Settings,
                        label = "설정",
                        labelColor = TextPrimary,
                        showArrow = true,
                        onClick = { showSettings = true },
                    )
                    HorizontalDivider(
                        modifier = Modifier.padding(horizontal = 16.dp),
                        color = Color(0xFFEEEEEE),
                    )
                    ActionRow(
                        icon = Icons.AutoMirrored.Filled.Logout,
                        label = "로그아웃",
                        labelColor = HealthRed,
                        showArrow = false,
                        onClick = {
                            scope.launch {
                                try {
                                    val token = RetrofitClient.getRefreshToken()
                                    if (token.isNotBlank()) {
                                        RetrofitClient.authApiService.logout(token)
                                    }
                                } catch (_: Exception) {
                                } finally {
                                    RetrofitClient.clearTokens()
                                    onLogout()
                                }
                            }
                        },
                    )
                }
            }

            Spacer(modifier = Modifier.height(bottomPadding + 24.dp))
        }
    }

    if (showSettings) {
        SettingSheet(
            onDismiss = { showSettings = false },
            agentName = agentName,
            onAgentNameChange = onAgentNameChange
        )
    }
}

@Composable
private fun ProfileSectionTitle(title: String) {
    Text(
        text = title,
        fontSize = 16.sp,
        fontWeight = FontWeight.Bold,
        color = TextPrimary,
        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
    )
    Spacer(modifier = Modifier.height(6.dp))
}

@Composable
private fun ProfileCard(content: @Composable () -> Unit) {
    Card(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceWhite),
        elevation = CardDefaults.cardElevation(1.dp),
    ) {
        content()
    }
}

@Composable
private fun ActionRow(
    icon: ImageVector,
    label: String,
    labelColor: Color,
    showArrow: Boolean,
    onClick: () -> Unit,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .clickable { onClick() }
                .padding(horizontal = 16.dp, vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, contentDescription = null, tint = labelColor, modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(12.dp))
        Text(label, fontSize = 15.sp, color = labelColor, modifier = Modifier.weight(1f))
        if (showArrow) {
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = TextSecondary,
                modifier = Modifier.size(20.dp),
            )
        }
    }
}
