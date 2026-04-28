package com.example.mob.feature.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mob.common.AppTopBar
import com.example.mob.ui.theme.*
import java.util.Calendar

@Composable
fun HomeScreen(
    onMenuClick: () -> Unit,
    bottomPadding: Dp = 0.dp
) {
    Scaffold(
        topBar = {
            AppTopBar(
                title = "HEYGENT",
                onMenuClick = onMenuClick,
                actions = {
                    IconButton(onClick = {}) {
                        Icon(Icons.Default.Notifications, contentDescription = "알림", tint = Color.White)
                    }
                }
            )
        },
        containerColor = Color.White,
        contentWindowInsets = WindowInsets(0)
    ) { innerPadding ->
        val (greeting, subGreeting) = remember {
            val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
            when (hour) {
                in 0..4   -> "조용한 새벽입니다." to "빠르게 도와드리겠습니다."
                in 5..8   -> "좋은 아침입니다." to "하루를 시작해 볼까요?"
                in 9..11  -> "활기찬 오전입니다." to "필요한 일을 정리해 드리겠습니다."
                in 12..13 -> "여유로운 점심입니다." to "잠시 쉬어가 볼까요?"
                in 14..17 -> "차분한 오후입니다." to "남은 일정을 도와드리겠습니다."
                in 18..20 -> "편안한 저녁입니다." to "하루를 정리해 볼까요?"
                else      -> "고요한 밤입니다." to "조용히 도와드리겠습니다."
            }
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(
                top = innerPadding.calculateTopPadding(),
                bottom = bottomPadding + 24.dp
            )
        ) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(NavyPrimary)
                        .padding(horizontal = 20.dp, vertical = 20.dp)
                ) {
                    Column {
                        Text(
                            text = greeting,
                            color = Color.White,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = subGreeting,
                            color = Color.White.copy(alpha = 0.7f),
                            fontSize = 14.sp
                        )
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }

            item {
                Box(modifier = Modifier.padding(horizontal = 16.dp)) {
                    CalendarSection()
                }
            }

            item { Spacer(modifier = Modifier.height(20.dp)) }

            item {
                Text(
                    text = "건강 요약",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                )
            }

            item { Spacer(modifier = Modifier.height(8.dp)) }

            item {
                Column(
                    modifier = Modifier.padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    HealthMetricCard(
                        icon = stepsIcon,
                        iconBgColor = ScheduleBlue,
                        title = "걸음 수",
                        value = "8,432",
                        badge = "+12%",
                        badgePositive = true,
                        chartColor = ScheduleBlue
                    )
                    HealthMetricCard(
                        icon = heartIcon,
                        iconBgColor = HealthRed,
                        title = "심박수",
                        value = "72 bpm",
                        badge = "정상",
                        badgePositive = false,
                        chartColor = HealthRed
                    )
                    HealthMetricCard(
                        icon = sleepIcon,
                        iconBgColor = SchedulePurple,
                        title = "수면",
                        value = "7.5h",
                        badge = "+0.5h",
                        badgePositive = true,
                        chartColor = ScheduleBlue
                    )
                }
            }
        }
    }
}
