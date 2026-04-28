package com.example.mob.feature.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mob.common.AppTopBar
import com.example.mob.ui.theme.*
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// ─── 데이터 ────────────────────────────────────────────────────────────────

private data class ChatListItem(
    val id: Int,
    val title: String,
    val preview: String,
    val time: String,
    val inputPlaceholder: String,
    val initialMessages: List<ChatMessage>
)

private val messagesSession = listOf(
    ChatMessage(isBot = true,  text = "안녕하세요. 오늘 어떻게 도와드릴까요?", timestamp = "오전\n09:58"),
    ChatMessage(isBot = false, text = "이번 주 일정 계획을 도와주실 수 있나요?", timestamp = "오전\n10:00"),
    ChatMessage(isBot = true,  text = "물론입니다. 캘린더와 우선순위를 분석하겠습니다. 월요일 오전에 분기 보고서에 집중하고, 화요일에 클라이언트 발표 준비를 하시는 것이 좋겠습니다.", timestamp = "오전\n10:01")
)

private val messagesDefault = listOf(
    ChatMessage(isBot = true,  text = "안녕하세요! 프레젠테이션에 어떻게 도움을 드릴까요?", timestamp = "오후\n10:58"),
    ChatMessage(isBot = false, text = "프레젠테이션 아웃라인 작성을 도와주세요", timestamp = "오후\n11:00"),
    ChatMessage(isBot = true,  text = "기꺼이 도와드리겠습니다. 프레젠테이션의 주제가 무엇인가요?", timestamp = "오후\n11:01")
)

private val chatSessions = listOf(
    ChatListItem(1, "주간 일정 계획", "물론입니다. 캘린더와 우선순위를 분석하겠습니다.", "오후 2:30", "궁금한 내용을 입력해 주세요", messagesSession),
    ChatListItem(2, "발표 자료 아웃라인", "기꺼이 도와드리겠습니다. 프레젠테이션의 주제가 무엇인가요?", "어제", "무엇을 도와드릴까요?", messagesDefault),
    ChatListItem(3, "건강 지표 검토", "건강 데이터를 분석해드리겠습니다.", "오전 10:15", "필요한 일을 입력해 주세요",
        listOf(ChatMessage(isBot = true, text = "안녕하세요! 건강 지표 분석을 도와드리겠습니다.", timestamp = "오전\n10:15"))),
    ChatListItem(4, "회의 요약", "회의 내용을 정리해드리겠습니다.", "어제", "오늘은 무엇을 도와드릴까요?",
        listOf(ChatMessage(isBot = true, text = "안녕하세요! 회의 요약을 도와드리겠습니다.", timestamp = "어제"))),
    ChatListItem(5, "리서치 요청", "원하시는 내용을 조사해드리겠습니다.", "4월 20일", "무엇이든 편하게 물어보세요",
        listOf(ChatMessage(isBot = true, text = "안녕하세요! 리서치를 도와드리겠습니다.", timestamp = "4월\n20일")))
)

private val newChatSession = ChatListItem(
    id = 0,
    title = "새 채팅",
    preview = "",
    time = "",
    inputPlaceholder = "무엇이든 편하게 물어보세요",
    initialMessages = emptyList()
)

private val botResponses = listOf(
    "이해했습니다. 바로 도와드리겠습니다.",
    "물론입니다! 요청을 분석하고 답변드리겠습니다.",
    "네. 요청을 바탕으로 제안드립니다.",
    "기꺼이 도와드리겠습니다."
)

private fun currentTime(): String = SimpleDateFormat("a\nhh:mm", Locale.KOREAN).format(Date())

// ─── ChatScreen (진입점) ───────────────────────────────────────────────────

@Composable
fun ChatScreen(
    onMenuClick: () -> Unit,
    activeChatSessionId: Int?,
    onActiveChatSessionChange: (Int?) -> Unit,
    agentName: String = "Jarvis",
    bottomPadding: Dp = 0.dp
) {
    val session = when (activeChatSessionId) {
        null -> null
        0 -> newChatSession
        else -> chatSessions.find { it.id == activeChatSessionId }
    }

    if (session == null) {
        ChatListView(
            onMenuClick = onMenuClick,
            agentName = agentName,
            onChatSelected = { item -> onActiveChatSessionChange(item.id) },
            bottomPadding = bottomPadding
        )
    } else {
        key(session.id) {
            SingleChatView(
                session = session,
                agentName = agentName,
                onMenuClick = onMenuClick,
                onBack = { onActiveChatSessionChange(null) },
                bottomPadding = bottomPadding
            )
        }
    }
}

// ─── 채팅 목록 ─────────────────────────────────────────────────────────────

@Composable
private fun ChatListView(
    onMenuClick: () -> Unit,
    agentName: String,
    onChatSelected: (ChatListItem) -> Unit,
    bottomPadding: Dp
) {
    Scaffold(
        topBar = { AppTopBar(title = agentName, onMenuClick = onMenuClick) },
        containerColor = Color.White,
        contentWindowInsets = WindowInsets(0)
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(
                top = innerPadding.calculateTopPadding(),
                bottom = bottomPadding + 12.dp
            )
        ) {
            items(chatSessions) { item ->
                ChatSessionRow(item = item, onClick = { onChatSelected(item) })
                HorizontalDivider(color = Color(0xFFF0F0F0))
            }
        }
    }
}

@Composable
private fun ChatSessionRow(item: ChatListItem, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null
            ) { onClick() }
            .padding(horizontal = 20.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = item.title,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary
                )
                Text(text = item.time, fontSize = 12.sp, color = TextSecondary)
            }
            Spacer(Modifier.height(3.dp))
            Text(
                text = item.preview,
                fontSize = 13.sp,
                color = TextSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

// ─── 단일 채팅방 ───────────────────────────────────────────────────────────

@Composable
private fun SingleChatView(
    session: ChatListItem,
    agentName: String,
    onMenuClick: () -> Unit,
    onBack: () -> Unit,
    bottomPadding: Dp
) {
    var messages by remember { mutableStateOf(session.initialMessages) }
    var isProcessing by remember { mutableStateOf(false) }
    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    var showAttachMenu by remember { mutableStateOf(false) }
    var showModelPanel by remember { mutableStateOf(false) }
    var isVoiceMode by remember { mutableStateOf(false) }

    LaunchedEffect(messages.size, isProcessing) {
        val count = messages.size + if (isProcessing) 1 else 0
        if (count > 0) listState.animateScrollToItem(count - 1)
    }

    LaunchedEffect(isProcessing) {
        if (isProcessing) {
            delay(3000)
            messages = messages + ChatMessage(
                isBot = true,
                text = botResponses.random(),
                timestamp = currentTime()
            )
            isProcessing = false
        }
    }

    val displayMessages = if (isProcessing) {
        messages + ChatMessage(isBot = true, text = "", timestamp = "", isTyping = true)
    } else messages

    val lastUserMessage = messages.lastOrNull { !it.isBot }?.text ?: session.title

    Box(modifier = Modifier.fillMaxSize()) {
        Scaffold(
            topBar = {
                AppTopBar(
                    title = agentName,
                    onMenuClick = onMenuClick,
                    onBack = onBack,
                    actions = {
                        Box {
                            IconButton(onClick = { showModelPanel = !showModelPanel }) {
                                Icon(Icons.Default.MoreVert, contentDescription = "더 보기", tint = Color.White)
                            }
                            DropdownMenu(
                                expanded = showModelPanel,
                                onDismissRequest = { showModelPanel = false },
                                modifier = Modifier.width(288.dp),
                                containerColor = Color.White
                            ) {
                                ModelPanelContent()
                            }
                        }
                    }
                )
            },
            containerColor = AppBackground,
            contentWindowInsets = WindowInsets(0)
        ) { innerPadding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(top = innerPadding.calculateTopPadding())
            ) {
                if (isProcessing) {
                    TaskStatusBanner(taskName = lastUserMessage.take(40) + if (lastUserMessage.length > 40) "..." else "")
                }

                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(vertical = 12.dp)
                ) {
                    items(displayMessages) { msg ->
                        if (msg.isBot) BotMessageBubble(msg, agentName) else UserMessageBubble(msg)
                        Spacer(modifier = Modifier.height(4.dp))
                    }
                }

                ChatInputBar(
                    inputText = inputText,
                    onInputChange = { inputText = it },
                    isProcessing = isProcessing,
                    placeholder = session.inputPlaceholder,
                    onSend = {
                        if (inputText.isNotBlank()) {
                            messages = messages + ChatMessage(isBot = false, text = inputText, timestamp = currentTime())
                            inputText = ""
                            isProcessing = true
                        }
                    },
                    onStop = { isProcessing = false },
                    onPlusClick = { showAttachMenu = !showAttachMenu },
                    onVoiceMode = { isVoiceMode = true }
                )

                if (bottomPadding > 0.dp) Spacer(modifier = Modifier.height(bottomPadding))
            }
        }

        if (showAttachMenu) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) { showAttachMenu = false }
            )
            Card(
                modifier = Modifier
                    .align(Alignment.BottomStart)
                    .padding(start = 12.dp, bottom = bottomPadding + 68.dp),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(8.dp)
            ) {
                Column(modifier = Modifier.width(140.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth().clickable { showAttachMenu = false }.padding(horizontal = 16.dp, vertical = 14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Image, contentDescription = null, tint = TextPrimary, modifier = Modifier.size(22.dp))
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("사진", fontSize = 15.sp, color = TextPrimary)
                    }
                    HorizontalDivider(color = Color(0xFFF0F0F0))
                    Row(
                        modifier = Modifier.fillMaxWidth().clickable { showAttachMenu = false }.padding(horizontal = 16.dp, vertical = 14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.AttachFile, contentDescription = null, tint = TextPrimary, modifier = Modifier.size(22.dp))
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("파일", fontSize = 15.sp, color = TextPrimary)
                    }
                }
            }
        }

        if (isVoiceMode) {
            VoiceModeOverlay(onStop = { isVoiceMode = false })
        }
    }
}

// ─── 모델 패널 ─────────────────────────────────────────────────────────────

@Composable
private fun ModelPanelContent() {
    val modelOptions = remember {
        mapOf(
            "ChatGPT" to listOf("GPT-5.3 Instant", "GPT-5.4 Thinking", "GPT-5.4 Pro"),
            "Claude"  to listOf("Claude Opus 4.7", "Claude Sonnet 4.6", "Claude Haiku 4.5"),
            "Gemini"  to listOf("Gemini 2.5 Pro", "Gemini 2.5 Flash", "Gemini 2.5 Flash-Lite", "Gemini 3.1 Pro", "Gemini 3.1 Flash-Lite")
        )
    }
    var selectedService by remember { mutableStateOf("ChatGPT") }
    var selectedModel   by remember { mutableStateOf("GPT-5.3 Instant") }
    var gptInference    by remember { mutableStateOf("Instant") }
    var geminiInference by remember { mutableStateOf("빠른 모델") }
    var claudeAdaptive  by remember { mutableStateOf(false) }
    var showServiceMenu by remember { mutableStateOf(false) }
    var showModelMenu   by remember { mutableStateOf(false) }

    Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
        Text("서비스", fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(6.dp))
        Box {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFFDDDDDD), RoundedCornerShape(8.dp))
                    .clip(RoundedCornerShape(8.dp))
                    .clickable { showServiceMenu = true }
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(selectedService, fontSize = 14.sp, color = TextPrimary, modifier = Modifier.weight(1f))
                Icon(Icons.Default.KeyboardArrowDown, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(18.dp))
            }
            DropdownMenu(expanded = showServiceMenu, onDismissRequest = { showServiceMenu = false }, containerColor = Color.White) {
                listOf("ChatGPT", "Claude", "Gemini").forEach { option ->
                    DropdownMenuItem(
                        text = { Text(option, fontSize = 14.sp) },
                        onClick = { selectedService = option; selectedModel = modelOptions[option]?.first() ?: ""; showServiceMenu = false }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))
        Text("모델", fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(6.dp))
        Box {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFFDDDDDD), RoundedCornerShape(8.dp))
                    .clip(RoundedCornerShape(8.dp))
                    .clickable { showModelMenu = true }
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(selectedModel, fontSize = 14.sp, color = TextPrimary, modifier = Modifier.weight(1f))
                Icon(Icons.Default.KeyboardArrowDown, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(18.dp))
            }
            DropdownMenu(expanded = showModelMenu, onDismissRequest = { showModelMenu = false }, modifier = Modifier.heightIn(max = 280.dp), containerColor = Color.White) {
                modelOptions[selectedService]?.forEach { option ->
                    DropdownMenuItem(text = { Text(option, fontSize = 14.sp) }, onClick = { selectedModel = option; showModelMenu = false })
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))
        HorizontalDivider(color = Color(0xFFEEEEEE))
        Spacer(modifier = Modifier.height(12.dp))
        Text("추론 강도", fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(4.dp))

        when (selectedService) {
            "ChatGPT" -> listOf("Instant", "Thinking").forEach { option ->
                InferenceOptionRow(option, gptInference == option) { gptInference = option }
            }
            "Gemini" -> listOf("빠른 모델", "사고 모델", "PRO").forEach { option ->
                InferenceOptionRow(option, geminiInference == option) { geminiInference = option }
            }
            "Claude" -> Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("적응형 사고", fontSize = 14.sp, color = TextPrimary)
                Switch(
                    checked = claudeAdaptive,
                    onCheckedChange = { claudeAdaptive = it },
                    colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color.Black, uncheckedThumbColor = Color.White, uncheckedTrackColor = Color(0xFFDDDDDD))
                )
            }
        }
    }
}

@Composable
private fun InferenceOptionRow(label: String, selected: Boolean, onClick: () -> Unit) {
    Row(modifier = Modifier.fillMaxWidth().clickable { onClick() }.padding(vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, fontSize = 14.sp, color = TextPrimary, fontWeight = if (selected) FontWeight.Medium else FontWeight.Normal, modifier = Modifier.weight(1f))
        if (selected) Icon(Icons.Default.Check, contentDescription = null, tint = TextPrimary, modifier = Modifier.size(18.dp))
    }
}
