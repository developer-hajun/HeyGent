package com.example.mob.feature.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mob.data.remote.OpenAiModelsResponse
import com.example.mob.data.remote.OpenAiProvider
import com.example.mob.data.remote.OpenAiUsageResponse
import com.example.mob.data.remote.RetrofitClient
import com.example.mob.ui.theme.NavyPrimary
import com.example.mob.ui.theme.TextPrimary
import com.example.mob.ui.theme.TextSecondary

private enum class SettingPage { GENERAL, SKILL, MODEL, PERSONALIZE, API_KEY }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingSheet(
    onDismiss: () -> Unit,
    agentName: String = "Jarvis",
    onAgentNameChange: (String) -> Unit = {}
) {
    var currentPage by remember { mutableStateOf<SettingPage?>(null) }
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = Color.White,
        shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp)
    ) {
        Box(modifier = Modifier.fillMaxWidth().heightIn(min = 420.dp)) {
            if (currentPage == null) {
                SettingMainPage(
                    onNavigate = { currentPage = it },
                    onDismiss = onDismiss
                )
            } else {
                SettingSubPage(
                    page = currentPage!!,
                    onBack = { currentPage = null },
                    onDismiss = onDismiss,
                    agentName = agentName,
                    onAgentNameChange = onAgentNameChange
                )
            }
        }
    }
}

@Composable
private fun SettingMainPage(
    onNavigate: (SettingPage) -> Unit,
    onDismiss: () -> Unit
) {
    Column(modifier = Modifier.padding(horizontal = 20.dp).padding(bottom = 32.dp)) {
        SheetHeader(title = "설정", onClose = onDismiss)
        Spacer(modifier = Modifier.height(8.dp))
        SettingRow(Icons.AutoMirrored.Filled.KeyboardArrowRight, "일반") { onNavigate(SettingPage.GENERAL) }
        SettingRow(Icons.Default.Bolt, "스킬 목록") { onNavigate(SettingPage.SKILL) }
        SettingRow(Icons.Default.Storage, "모델") { onNavigate(SettingPage.MODEL) }
        SettingRow(Icons.Default.Palette, "개인 맞춤 설정") { onNavigate(SettingPage.PERSONALIZE) }
        SettingRow(Icons.Default.Key, "API 키") { onNavigate(SettingPage.API_KEY) }
    }
}

@Composable
private fun SettingSubPage(
    page: SettingPage,
    onBack: () -> Unit,
    onDismiss: () -> Unit,
    agentName: String,
    onAgentNameChange: (String) -> Unit
) {
    val title = when (page) {
        SettingPage.GENERAL -> "일반"
        SettingPage.SKILL -> "스킬 목록"
        SettingPage.MODEL -> "모델"
        SettingPage.PERSONALIZE -> "개인 맞춤 설정"
        SettingPage.API_KEY -> "API 키"
    }
    Column(
        modifier = Modifier
            .padding(horizontal = 20.dp)
            .padding(bottom = 32.dp)
            .verticalScroll(rememberScrollState())
    ) {
        SheetHeader(title = title, onClose = onDismiss, onBack = onBack)
        Spacer(modifier = Modifier.height(8.dp))
        when (page) {
            SettingPage.GENERAL -> GeneralContent()
            SettingPage.SKILL -> SkillContent()
            SettingPage.MODEL -> ModelContent()
            SettingPage.PERSONALIZE -> PersonalizeContent(agentName = agentName, onAgentNameChange = onAgentNameChange)
            SettingPage.API_KEY -> ApiKeyContent()
        }
    }
}

// ────────────────────────────── 일반 ──────────────────────────────

@Composable
private fun GeneralContent() {}

// ────────────────────────────── 스킬 목록 ──────────────────────────────

@Composable
private fun SkillContent() {
    data class Skill(val name: String, val desc: String, var enabled: Boolean)
    val skills = remember {
        mutableStateListOf(
            Skill("깃허브 PR 리뷰", "Pull Request를 자동으로 분석하고 리뷰합니다", true),
            Skill("리마인드 생성", "일정과 알림을 자동으로 생성하고 관리합니다", true),
            Skill("식단 추천", "개인 맞춤 식단을 추천합니다", true),
            Skill("헬스 커넥트 조회", "건강 데이터를 조회하고 분석합니다", false),
            Skill("IoT 알림 전송", "IoT 기기로 알림을 전송합니다", true)
        )
    }

    Text("Heygent가 사용할 수 있는 스킬을 관리합니다", fontSize = 13.sp, color = TextSecondary)
    Spacer(modifier = Modifier.height(16.dp))

    skills.forEachIndexed { i, skill ->
        Card(
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFF8F8F8)),
            elevation = CardDefaults.cardElevation(0.dp)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(skill.name, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
                    Text(skill.desc, fontSize = 12.sp, color = TextSecondary)
                }
                Switch(
                    checked = skill.enabled,
                    onCheckedChange = { skills[i] = skill.copy(enabled = it) },
                    colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = NavyPrimary)
                )
            }
        }
    }
}

// ────────────────────────────── 모델 ──────────────────────────────

@Composable
private fun ModelContent() {
    var isLoadingProviders by remember { mutableStateOf(true) }
    var providers by remember { mutableStateOf<List<OpenAiProvider>>(emptyList()) }
    var selectedProvider by remember { mutableStateOf<OpenAiProvider?>(null) }
    var isLoadingUsage by remember { mutableStateOf(false) }
    var usageData by remember { mutableStateOf<OpenAiUsageResponse?>(null) }
    var errorMsg by remember { mutableStateOf<String?>(null) }
    var modelsData by remember { mutableStateOf<OpenAiModelsResponse?>(null) }

    // 1단계: providers + models 병렬 로드
    LaunchedEffect(Unit) {
        try {
            val providersResponse = RetrofitClient.aiApiService.getOpenAiProviders()
            if (providersResponse.status == 200) {
                providers = providersResponse.data?.providers ?: emptyList()
                selectedProvider = providers.firstOrNull { it.connected && it.available }
            } else {
                errorMsg = providersResponse.message
            }
        } catch (_: Exception) {
            errorMsg = "Provider 조회에 실패했습니다."
        } finally {
            isLoadingProviders = false
        }
        try {
            val modelsResponse = RetrofitClient.aiApiService.getOpenAiModels()
            if (modelsResponse.status == 200) {
                modelsData = modelsResponse.data
            }
        } catch (_: Exception) { }
    }

    // 2단계: 선택된 provider 바뀌면 사용량 조회
    LaunchedEffect(selectedProvider) {
        val provider = selectedProvider ?: return@LaunchedEffect
        isLoadingUsage = true
        usageData = null
        errorMsg = null
        try {
            val response = RetrofitClient.aiApiService.getOpenAiUsage(
                providerName = provider.providerName
            )
            if (response.status == 200) {
                usageData = response.data
            } else {
                errorMsg = response.message
            }
        } catch (_: Exception) {
            errorMsg = "사용량 조회에 실패했습니다."
        } finally {
            isLoadingUsage = false
        }
    }

    Text("사용 중인 AI 모델과 사용량을 확인합니다", fontSize = 13.sp, color = TextSecondary)
    Spacer(modifier = Modifier.height(16.dp))

    if (isLoadingProviders) {
        Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = NavyPrimary, modifier = Modifier.size(32.dp))
        }
        return
    }

    if (providers.isEmpty()) {
        Text(
            text = errorMsg ?: "연결된 provider가 없습니다.",
            fontSize = 13.sp,
            color = Color(0xFFE53935)
        )
        return
    }

    // Provider 선택 카드 목록
    providers.forEach { provider ->
        val isSelected = selectedProvider?.providerName == provider.providerName
        val statusColor = when (provider.status) {
            "connected" -> Color(0xFF4CAF50)
            "expired"   -> Color(0xFFFF9800)
            else        -> Color(0xFF9E9E9E)
        }
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 4.dp),
            onClick = {
                if (provider.connected && provider.available) {
                    selectedProvider = provider
                }
            },
            colors = CardDefaults.cardColors(
                containerColor = if (isSelected) Color(0xFFE8EAF6) else Color(0xFFF8F8F8)
            ),
            elevation = CardDefaults.cardElevation(0.dp),
            border = if (isSelected) androidx.compose.foundation.BorderStroke(1.5.dp, NavyPrimary) else null
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(provider.providerName, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                    Text(provider.authType, fontSize = 11.sp, color = TextSecondary)
                }
                Text(provider.status, fontSize = 11.sp, color = statusColor, fontWeight = FontWeight.Medium)
            }
        }
    }

    // 사용 가능한 모델 목록
    if (modelsData != null) {
        Spacer(modifier = Modifier.height(16.dp))
        Text("사용 가능한 모델", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
        Spacer(modifier = Modifier.height(8.dp))
        modelsData!!.models.forEach { model ->
            val isDefault = model == modelsData!!.defaultModel
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = model,
                    fontSize = 13.sp,
                    color = if (isDefault) NavyPrimary else TextPrimary,
                    fontWeight = if (isDefault) FontWeight.SemiBold else FontWeight.Normal,
                    modifier = Modifier.weight(1f)
                )
                if (isDefault) {
                    Text(
                        text = "기본",
                        fontSize = 10.sp,
                        color = Color.White,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier
                            .background(NavyPrimary, shape = androidx.compose.foundation.shape.RoundedCornerShape(4.dp))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }
        }
    }

    // 선택된 provider 사용량
    if (selectedProvider != null) {
        Spacer(modifier = Modifier.height(16.dp))
        Text("사용량", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
        Spacer(modifier = Modifier.height(8.dp))

        if (isLoadingUsage) {
            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = NavyPrimary, modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
            }
        } else if (usageData != null) {
            val usageCount = usageData!!.usage.getAsJsonArray("data")?.size() ?: 0
            val costsCount = usageData!!.costs.getAsJsonArray("data")?.size() ?: 0
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF8F8F8)),
                elevation = CardDefaults.cardElevation(0.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("사용 기록", fontSize = 12.sp, color = TextSecondary)
                        Text("${usageCount}건", fontSize = 12.sp, color = TextPrimary, fontWeight = FontWeight.Medium)
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("비용 기록", fontSize = 12.sp, color = TextSecondary)
                        Text("${costsCount}건", fontSize = 12.sp, color = TextPrimary, fontWeight = FontWeight.Medium)
                    }
                }
            }
        } else if (errorMsg != null) {
            Text(text = errorMsg!!, fontSize = 13.sp, color = Color(0xFFE53935))
        }
    }
}

// ────────────────────────────── 개인 맞춤 설정 ──────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PersonalizeContent(agentName: String, onAgentNameChange: (String) -> Unit) {
    var voiceName by remember { mutableStateOf(agentName) }

    Text("에이전트 이름을 설정합니다", fontSize = 13.sp, color = TextSecondary)
    Spacer(modifier = Modifier.height(20.dp))

    Text("에이전트 이름", fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
    Text("에이전트를 호출할 이름을 설정합니다.", fontSize = 12.sp, color = TextSecondary)
    Spacer(modifier = Modifier.height(8.dp))
    OutlinedTextField(
        value = voiceName,
        onValueChange = {
            voiceName = it
            onAgentNameChange(it)
        },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        shape = RoundedCornerShape(8.dp)
    )
}

// ────────────────────────────── API 키 ──────────────────────────────

@Composable
private fun ApiKeyContent() {
    var openAiKey by remember { mutableStateOf("") }
    var openAiVisible by remember { mutableStateOf(false) }
    var anthropicKey by remember { mutableStateOf("") }
    var anthropicVisible by remember { mutableStateOf(false) }
    var githubToken by remember { mutableStateOf("") }

    Text("외부 서비스 연동을 위한 API 키를 관리합니다", fontSize = 13.sp, color = TextSecondary)
    Spacer(modifier = Modifier.height(20.dp))

    ApiKeyField(
        label = "OpenAI API",
        value = openAiKey,
        onValueChange = { openAiKey = it },
        visible = openAiVisible,
        onToggleVisibility = { openAiVisible = !openAiVisible }
    )
    Spacer(modifier = Modifier.height(16.dp))
    ApiKeyField(
        label = "Anthropic API",
        value = anthropicKey,
        onValueChange = { anthropicKey = it },
        visible = anthropicVisible,
        onToggleVisibility = { anthropicVisible = !anthropicVisible }
    )
    Spacer(modifier = Modifier.height(16.dp))

    Text("GitHub Token", fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
    Spacer(modifier = Modifier.height(6.dp))
    OutlinedTextField(
        value = githubToken,
        onValueChange = { githubToken = it },
        placeholder = { Text("GitHub Token 키를 입력하세요", color = TextSecondary) },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        shape = RoundedCornerShape(8.dp)
    )
}

@Composable
private fun ApiKeyField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    visible: Boolean,
    onToggleVisibility: () -> Unit
) {
    Text(label, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
    Spacer(modifier = Modifier.height(6.dp))
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        placeholder = { Text("키를 입력하세요", color = TextSecondary) },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        shape = RoundedCornerShape(8.dp),
        visualTransformation = if (visible) androidx.compose.ui.text.input.VisualTransformation.None
        else androidx.compose.ui.text.input.PasswordVisualTransformation(),
        trailingIcon = {
            IconButton(onClick = onToggleVisibility) {
                Icon(
                    if (visible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                    contentDescription = "표시/숨김",
                    tint = TextSecondary
                )
            }
        }
    )
}

// ────────────────────────────── 공통 컴포넌트 ──────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DropdownSetting(
    label: String,
    description: String,
    options: List<String>,
    defaultValue: String
) {
    var expanded by remember { mutableStateOf(false) }
    var selected by remember { mutableStateOf(defaultValue) }

    Text(label, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
    Text(description, fontSize = 12.sp, color = TextSecondary)
    Spacer(modifier = Modifier.height(8.dp))

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded }
    ) {
        OutlinedTextField(
            value = selected,
            onValueChange = {},
            readOnly = true,
            modifier = Modifier
                .fillMaxWidth()
                .menuAnchor(MenuAnchorType.PrimaryNotEditable),
            shape = RoundedCornerShape(8.dp),
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = NavyPrimary,
                unfocusedBorderColor = Color(0xFFDDDDDD)
            )
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
            containerColor = Color.White
        ) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = {
                        Text(
                            option,
                            fontSize = 14.sp,
                            color = if (option == selected) NavyPrimary else TextPrimary,
                            fontWeight = if (option == selected) FontWeight.SemiBold else FontWeight.Normal
                        )
                    },
                    onClick = {
                        selected = option
                        expanded = false
                    }
                )
            }
        }
    }
}

@Composable
private fun SettingToggleItem(
    label: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(modifier = Modifier.weight(1f)) {
            Text(label, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
            Text(description, fontSize = 12.sp, color = TextSecondary)
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = NavyPrimary)
        )
    }
}

@Composable
private fun SheetHeader(title: String, onClose: () -> Unit, onBack: (() -> Unit)? = null) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (onBack != null) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "뒤로", tint = TextSecondary)
            }
        }
        Text(
            title,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = TextPrimary,
            modifier = Modifier.weight(1f)
        )
        IconButton(onClick = onClose) {
            Icon(Icons.Default.Close, contentDescription = "닫기", tint = TextSecondary)
        }
    }
    HorizontalDivider(color = Color(0xFFEEEEEE))
    Spacer(modifier = Modifier.height(8.dp))
}

@Composable
private fun SettingRow(icon: ImageVector, label: String, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        onClick = onClick,
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF8F8F8)),
        elevation = CardDefaults.cardElevation(0.dp),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(20.dp))
            Spacer(modifier = Modifier.width(12.dp))
            Text(label, fontSize = 15.sp, color = TextPrimary, modifier = Modifier.weight(1f))
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = TextSecondary,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}
