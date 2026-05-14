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
import com.example.mob.data.remote.ChatSessionResponse
import com.example.mob.ui.theme.*

// ─── ChatScreen (진입점) ───────────────────────────────────────────────────

@Composable
fun ChatScreen(
    onMenuClick: () -> Unit,
    activeChatSessionId: String?,
    onActiveChatSessionChange: (String?) -> Unit,
    viewModel: ChatViewModel,
    agentName: String = "Jarvis",
    bottomPadding: Dp = 0.dp
) {
    val sessions by viewModel.sessions.collectAsState()
    val messages by viewModel.messages.collectAsState()
    val isProcessing by viewModel.isProcessing.collectAsState()
    val isLoadingSessions by viewModel.isLoadingSessions.collectAsState()

    LaunchedEffect(activeChatSessionId) {
        when {
            activeChatSessionId == null -> { /* 목록 화면 — 별도 처리 없음 */ }
            activeChatSessionId.isEmpty() -> viewModel.startNewSession()
            else -> viewModel.openSession(activeChatSessionId)
        }
    }

    if (activeChatSessionId == null) {
        LaunchedEffect(Unit) { viewModel.loadSessions() }
        ChatListView(
            onMenuClick = onMenuClick,
            agentName = agentName,
            sessions = sessions,
            isLoading = isLoadingSessions,
            onChatSelected = { onActiveChatSessionChange(it) },
            bottomPadding = bottomPadding
        )
    } else {
        val activeId by viewModel.activeSessionId.collectAsState()
        SingleChatView(
            agentName = agentName,
            messages = messages,
            isProcessing = isProcessing,
            onMenuClick = onMenuClick,
            onBack = { onActiveChatSessionChange(null) },
            onSend = { viewModel.sendMessage(it) },
            onStop = { viewModel.stopProcessing() },
            bottomPadding = bottomPadding
        )
    }
}

// ─── 채팅 목록 ─────────────────────────────────────────────────────────────

@Composable
private fun ChatListView(
    onMenuClick: () -> Unit,
    agentName: String,
    sessions: List<ChatSessionResponse>,
    isLoading: Boolean,
    onChatSelected: (String) -> Unit,
    bottomPadding: Dp
) {
    Scaffold(
        topBar = { AppTopBar(title = agentName, onMenuClick = onMenuClick) },
        containerColor = Color.White,
        contentWindowInsets = WindowInsets(0)
    ) { innerPadding ->
        when {
            isLoading -> Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(top = innerPadding.calculateTopPadding()),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(color = NavyPrimary)
            }
            sessions.isEmpty() -> Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(top = innerPadding.calculateTopPadding()),
                contentAlignment = Alignment.Center
            ) {
                Text("채팅 세션이 없습니다.", color = TextSecondary, fontSize = 14.sp)
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(
                    top = innerPadding.calculateTopPadding(),
                    bottom = bottomPadding + 12.dp
                )
            ) {
                items(sessions, key = { it.sessionId }) { session ->
                    ChatSessionRow(session = session, onClick = { onChatSelected(session.sessionId) })
                    HorizontalDivider(color = Color(0xFFF0F0F0))
                }
            }
        }
    }
}

@Composable
private fun ChatSessionRow(session: ChatSessionResponse, onClick: () -> Unit) {
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
                    text = session.title ?: "채팅",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary,
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(text = session.formatTime(), fontSize = 12.sp, color = TextSecondary)
            }
            Spacer(Modifier.height(3.dp))
            Text(
                text = "${session.messageCount}개의 메시지",
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
    agentName: String,
    messages: List<ChatMessage>,
    isProcessing: Boolean,
    onMenuClick: () -> Unit,
    onBack: () -> Unit,
    onSend: (String) -> Unit,
    onStop: () -> Unit,
    bottomPadding: Dp
) {
    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    var showAttachMenu by remember { mutableStateOf(false) }
    var showModelPanel by remember { mutableStateOf(false) }
    var isVoiceMode by remember { mutableStateOf(false) }

    val displayMessages = if (isProcessing) {
        messages + ChatMessage(isBot = true, text = "", timestamp = "", isTyping = true)
    } else messages

    val lastUserMessage = messages.lastOrNull { !it.isBot }?.text ?: ""

    LaunchedEffect(displayMessages.size) {
        if (displayMessages.isNotEmpty()) listState.animateScrollToItem(displayMessages.size - 1)
    }

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
                if (isProcessing && lastUserMessage.isNotEmpty()) {
                    TaskStatusBanner(
                        taskName = lastUserMessage.take(40) + if (lastUserMessage.length > 40) "..." else ""
                    )
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
                    placeholder = "무엇이든 편하게 물어보세요",
                    onSend = {
                        if (inputText.isNotBlank()) {
                            onSend(inputText)
                            inputText = ""
                        }
                    },
                    onStop = onStop,
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
                    .clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = null
                    ) { showAttachMenu = false }
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
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { showAttachMenu = false }
                            .padding(horizontal = 16.dp, vertical = 14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Image, contentDescription = null, tint = TextPrimary, modifier = Modifier.size(22.dp))
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("사진", fontSize = 15.sp, color = TextPrimary)
                    }
                    HorizontalDivider(color = Color(0xFFF0F0F0))
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { showAttachMenu = false }
                            .padding(horizontal = 16.dp, vertical = 14.dp),
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
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Color.White,
                        checkedTrackColor = Color.Black,
                        uncheckedThumbColor = Color.White,
                        uncheckedTrackColor = Color(0xFFDDDDDD)
                    )
                )
            }
        }
    }
}

@Composable
private fun InferenceOptionRow(label: String, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable { onClick() }.padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            label,
            fontSize = 14.sp,
            color = TextPrimary,
            fontWeight = if (selected) FontWeight.Medium else FontWeight.Normal,
            modifier = Modifier.weight(1f)
        )
        if (selected) Icon(Icons.Default.Check, contentDescription = null, tint = TextPrimary, modifier = Modifier.size(18.dp))
    }
}
