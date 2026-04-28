package com.example.mob.feature.profile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun GeneralContent() {
    var notificationsOn by remember { mutableStateOf(true) }
    var soundOn by remember { mutableStateOf(true) }

    Text("애플리케이션의 기본 설정을 관리합니다", fontSize = 13.sp, color = TextSecondary)
    Spacer(modifier = Modifier.height(20.dp))

    DropdownSetting(
        label = "언어",
        description = "애플리케이션 표시 언어를 선택합니다",
        options = listOf("한국어", "English"),
        defaultValue = "한국어"
    )
    Spacer(modifier = Modifier.height(16.dp))
    SettingToggleItem("알림", "데스크톱 알림을 활성화합니다", notificationsOn) { notificationsOn = it }
    Spacer(modifier = Modifier.height(16.dp))
    SettingToggleItem("효과음", "알림 및 상호작용 시 효과음을 재생합니다", soundOn) { soundOn = it }
}

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
    data class ModelInfo(val name: String, val used: Int, val total: Int)
    val models = listOf(
        ModelInfo("GPT-4 Turbo", 1250, 5000),
        ModelInfo("Claude 3 Sonnet", 840, 3000),
        ModelInfo("Gemini Pro", 320, 2000)
    )

    Text("사용 중인 AI 모델과 사용량을 확인합니다", fontSize = 13.sp, color = TextSecondary)
    Spacer(modifier = Modifier.height(16.dp))

    models.forEach { model ->
        val usageRate = model.used.toFloat() / model.total * 100
        Card(
            modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFF8F8F8)),
            elevation = CardDefaults.cardElevation(0.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(model.name, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                    Text("${model.used} / ${model.total} 요청", fontSize = 12.sp, color = TextSecondary)
                }
                Spacer(modifier = Modifier.height(6.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("사용률: ${"%.1f".format(usageRate)}%", fontSize = 12.sp, color = TextSecondary)
                    Text("남은 요청: ${model.total - model.used}", fontSize = 12.sp, color = TextSecondary)
                }
            }
        }
    }
}

// ────────────────────────────── 개인 맞춤 설정 ──────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PersonalizeContent(agentName: String, onAgentNameChange: (String) -> Unit) {
    var voiceName by remember { mutableStateOf(agentName) }

    Text("에이전트의 스타일과 말투를 개인화합니다", fontSize = 13.sp, color = TextSecondary)
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
    Spacer(modifier = Modifier.height(16.dp))

    DropdownSetting(
        label = "기본 스타일 및 말투",
        description = "에이전트가 응답하는 스타일과 말투를 지정합니다",
        options = listOf("기본값", "격식체", "반말", "친근한"),
        defaultValue = "기본값"
    )
    Spacer(modifier = Modifier.height(16.dp))
    DropdownSetting(
        label = "언어",
        description = "응답 언어를 선택합니다",
        options = listOf("자동 탐지", "한국어", "English"),
        defaultValue = "자동 탐지"
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
