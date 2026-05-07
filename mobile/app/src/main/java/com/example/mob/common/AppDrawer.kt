package com.example.mob.common

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private data class HistoryItem(
    val id: Int,
    val title: String,
    val time: String,
)

@Composable
fun AppDrawer(
    onClose: () -> Unit,
    agentName: String = "Jarvis",
    onNewChat: () -> Unit = {},
    onHistoryItemClick: (Int) -> Unit = {},
) {
    val historyItems = remember {
        mutableStateListOf(
            HistoryItem(1, "주간 일정 계획", "오후 2:30"),
            HistoryItem(3, "건강 지표 검토", "오전 10:15"),
            HistoryItem(2, "발표 자료 아웃라인", "어제"),
            HistoryItem(4, "회의 요약", "어제"),
            HistoryItem(5, "리서치 요청", "4월 20일"),
        )
    }
    var itemToDelete by remember { mutableStateOf<HistoryItem?>(null) }

    itemToDelete?.let { target ->
        AlertDialog(
            onDismissRequest = { itemToDelete = null },
            title = { Text("세션 삭제", color = Color.White) },
            text = { Text("'${target.title}' 세션을 삭제하시겠습니까?", color = Color.White.copy(alpha = 0.8f)) },
            confirmButton = {
                TextButton(onClick = {
                    historyItems.remove(target)
                    itemToDelete = null
                }) {
                    Text("삭제", color = Color(0xFFEF5350))
                }
            },
            dismissButton = {
                TextButton(onClick = { itemToDelete = null }) {
                    Text("취소", color = Color.White.copy(alpha = 0.7f))
                }
            },
            containerColor = Color(0xFF1E1E1E),
        )
    }

    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .background(Color.Black)
                .verticalScroll(rememberScrollState())
                .padding(bottom = 32.dp),
    ) {
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(start = 20.dp, end = 8.dp, top = 56.dp, bottom = 20.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text(agentName, color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Text(
                    "당신만을 위한 어시스턴트",
                    color = Color.White.copy(alpha = 0.6f),
                    fontSize = 13.sp,
                )
            }
            IconButton(onClick = onClose) {
                Icon(Icons.Default.Close, contentDescription = "닫기", tint = Color.White)
            }
        }

        // 새 채팅 버튼
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White.copy(alpha = 0.12f))
                    .clickable { onNewChat() }
                    .padding(horizontal = 16.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                Icons.Default.Add,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(18.dp),
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text("새 세션", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
        }

        Spacer(modifier = Modifier.height(20.dp))

        DrawerSectionLabel("최근 기록")
        Spacer(modifier = Modifier.height(8.dp))
        historyItems.forEach { item ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onHistoryItemClick(item.id) }
                    .padding(start = 16.dp, top = 10.dp, bottom = 10.dp, end = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        item.title,
                        color = Color.White,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                    )
                    Text(item.time, color = Color.White.copy(alpha = 0.5f), fontSize = 12.sp)
                }
                IconButton(
                    onClick = { itemToDelete = item },
                    modifier = Modifier.size(32.dp)
                ) {
                    Icon(
                        Icons.Default.Close,
                        contentDescription = "삭제",
                        tint = Color.White.copy(alpha = 0.35f),
                        modifier = Modifier.size(15.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun DrawerSectionLabel(text: String) {
    Text(
        text = text,
        color = Color.White.copy(alpha = 0.5f),
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        letterSpacing = 1.5.sp,
        modifier = Modifier.padding(start = 20.dp),
    )
}
