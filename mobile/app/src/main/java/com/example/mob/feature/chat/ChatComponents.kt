package com.example.mob.feature.chat

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.GraphicEq
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.*
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size as GeomSize
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mob.ui.theme.*

private val BotBubbleColor = Color(0xFF1C1C1E)

data class ChatMessage(
    val isBot: Boolean,
    val text: String,
    val timestamp: String,
    val isTyping: Boolean = false
)

@Composable
fun BotMessageBubble(message: ChatMessage, agentName: String = "Jarvis") {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
    ) {
        Text(
            text = agentName,
            fontSize = 12.sp,
            color = TextSecondary,
            modifier = Modifier.padding(start = 4.dp, bottom = 4.dp)
        )
        if (message.isTyping) {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp))
                    .background(BotBubbleColor)
                    .padding(horizontal = 16.dp, vertical = 14.dp)
            ) {
                TypingIndicator()
            }
        } else {
            Row(verticalAlignment = Alignment.Bottom) {
                Box(
                    modifier = Modifier
                        .widthIn(max = 260.dp)
                        .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp))
                        .background(BotBubbleColor)
                        .padding(horizontal = 16.dp, vertical = 12.dp)
                ) {
                    Text(message.text, fontSize = 14.sp, color = Color.White, lineHeight = 20.sp)
                }
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = message.timestamp,
                    fontSize = 10.sp,
                    color = TextSecondary,
                    lineHeight = 14.sp
                )
            }
        }
    }
}

@Composable
fun UserMessageBubble(message: ChatMessage) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp),
        horizontalAlignment = Alignment.End
    ) {
        Row(verticalAlignment = Alignment.Bottom) {
            Text(
                text = message.timestamp,
                fontSize = 10.sp,
                color = TextSecondary,
                lineHeight = 14.sp
            )
            Spacer(modifier = Modifier.width(6.dp))
            Box(
                modifier = Modifier
                    .widthIn(max = 260.dp)
                    .clip(RoundedCornerShape(topStart = 16.dp, topEnd = 4.dp, bottomStart = 16.dp, bottomEnd = 16.dp))
                    .background(Color.White)
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Text(
                    text = message.text,
                    fontSize = 14.sp,
                    color = TextPrimary,
                    lineHeight = 20.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}

@Composable
fun TaskStatusBanner(taskName: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFFF0F2F5))
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(ActiveGreen)
        )
        Spacer(modifier = Modifier.width(10.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text("Current Task", fontSize = 11.sp, color = TextSecondary)
            Text(taskName, fontSize = 13.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
        }
        Text("Processing...", fontSize = 12.sp, color = TextSecondary)
    }
}

@Composable
fun TypingIndicator() {
    val infiniteTransition = rememberInfiniteTransition(label = "typing")
    val alphas = (0..2).map { i ->
        infiniteTransition.animateFloat(
            initialValue = 0.3f,
            targetValue = 1.0f,
            animationSpec = infiniteRepeatable(
                animation = tween(400, delayMillis = i * 140, easing = FastOutSlowInEasing),
                repeatMode = RepeatMode.Reverse
            ),
            label = "dot$i"
        )
    }
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(5.dp)
    ) {
        alphas.forEach { alpha ->
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = alpha.value))
            )
        }
        Spacer(modifier = Modifier.width(4.dp))
        Text("처리 중...", fontSize = 13.sp, color = Color.White.copy(alpha = 0.7f))
    }
}

@Composable
fun ChatInputBar(
    inputText: String,
    onInputChange: (String) -> Unit,
    isProcessing: Boolean,
    onSend: () -> Unit,
    onStop: () -> Unit,
    onPlusClick: () -> Unit = {},
    onVoiceMode: () -> Unit = {},
    placeholder: String = "젠틀맨 어시스턴트에게 질문하세요..."
) {
    var isRecording by remember { mutableStateOf(false) }

    Surface(shadowElevation = 8.dp, color = SurfaceWhite) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (!isRecording) {
                IconButton(onClick = onPlusClick, modifier = Modifier.size(36.dp)) {
                    Icon(Icons.Default.Add, contentDescription = null, tint = TextSecondary)
                }
                Spacer(modifier = Modifier.width(6.dp))
            }

            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(24.dp))
                    .background(AppBackground)
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                contentAlignment = Alignment.CenterStart
            ) {
                when {
                    isRecording -> RecordingWaveform()
                    isProcessing -> Text("응답을 기다리는 중...", color = TextSecondary, fontSize = 14.sp)
                    else -> BasicTextField(
                        value = inputText,
                        onValueChange = onInputChange,
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 4,
                        textStyle = TextStyle(fontSize = 14.sp, color = TextPrimary),
                        cursorBrush = SolidColor(NavyPrimary),
                        decorationBox = { innerTextField ->
                            Box {
                                if (inputText.isEmpty()) {
                                    Text(placeholder, color = TextHint, fontSize = 14.sp)
                                }
                                innerTextField()
                            }
                        }
                    )
                }
            }

            Spacer(modifier = Modifier.width(6.dp))

            if (!isProcessing) {
                IconButton(
                    onClick = { isRecording = !isRecording },
                    modifier = Modifier.size(36.dp)
                ) {
                    Icon(
                        Icons.Default.Mic,
                        contentDescription = null,
                        tint = if (isRecording) HealthRed else TextSecondary
                    )
                }
                Spacer(modifier = Modifier.width(4.dp))
            }

            when {
                isProcessing -> Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(HealthRed)
                        .clickable { onStop() },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.Stop, contentDescription = "정지", tint = Color.White, modifier = Modifier.size(20.dp))
                }
                isRecording -> Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(HealthRed)
                        .clickable { isRecording = false },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.Stop, contentDescription = "녹음 중지", tint = Color.White, modifier = Modifier.size(20.dp))
                }
                inputText.isNotBlank() -> Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(NavyPrimary)
                        .clickable { onSend() },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "전송", tint = Color.White, modifier = Modifier.size(18.dp))
                }
                else -> Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(NavyPrimary)
                        .clickable { onVoiceMode() },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.GraphicEq, contentDescription = "음성 대화", tint = Color(0xFF19C37D), modifier = Modifier.size(22.dp))
                }
            }
        }
    }
}

@Composable
private fun RecordingWaveform() {
    val transition = rememberInfiniteTransition(label = "recording")
    val barHeights = (0 until 7).map { i ->
        transition.animateFloat(
            initialValue = 0.15f,
            targetValue = 1.0f,
            animationSpec = infiniteRepeatable(
                animation = tween(240 + i * 55, easing = FastOutSlowInEasing),
                repeatMode = RepeatMode.Reverse
            ),
            label = "bar$i"
        )
    }

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text("녹음 중", fontSize = 13.sp, color = HealthRed)
        Spacer(Modifier.width(10.dp))
        Canvas(modifier = Modifier.width(64.dp).height(24.dp)) {
            val barW = 4.dp.toPx()
            val gap = 4.dp.toPx()
            val total = 7 * barW + 6 * gap
            val startX = (size.width - total) / 2f
            barHeights.forEachIndexed { i, h ->
                val barH = size.height * h.value
                val x = startX + i * (barW + gap)
                val y = (size.height - barH) / 2f
                drawRoundRect(
                    color = Color(0xFFEF5350),
                    topLeft = Offset(x, y),
                    size = GeomSize(barW, barH),
                    cornerRadius = CornerRadius(2.dp.toPx())
                )
            }
        }
    }
}

@Composable
fun VoiceModeOverlay(onStop: () -> Unit) {
    val transition = rememberInfiniteTransition(label = "voice")
    var isSpeaking by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        while (true) {
            kotlinx.coroutines.delay(3000)
            isSpeaking = !isSpeaking
        }
    }

    val pulse1 = transition.animateFloat(
        0.88f, 1.12f,
        infiniteRepeatable(tween(1000, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "p1"
    )
    val pulse2 = transition.animateFloat(
        0.75f, 1.25f,
        infiniteRepeatable(tween(1400, delayMillis = 200, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "p2"
    )
    val pulse3 = transition.animateFloat(
        0.65f, 1.38f,
        infiniteRepeatable(tween(1800, delayMillis = 400, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "p3"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.offset(y = (-48).dp)
        ) {
            Canvas(modifier = Modifier.size(200.dp)) {
                val base = 44.dp.toPx()
                drawCircle(NavyPrimary.copy(alpha = 0.12f), base * 2.2f * pulse3.value)
                drawCircle(NavyPrimary.copy(alpha = 0.22f), base * 1.75f * pulse2.value)
                drawCircle(NavyPrimary.copy(alpha = 0.38f), base * 1.35f * pulse1.value)
                drawCircle(NavyPrimary, base)
            }
            Spacer(Modifier.height(28.dp))
            Text(
                if (isSpeaking) "말하는 중..." else "듣는 중...",
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium
            )
        }

        Box(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 72.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.15f))
                    .clickable { onStop() },
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .background(Color.White, RoundedCornerShape(4.dp))
                )
            }
        }
    }
}
