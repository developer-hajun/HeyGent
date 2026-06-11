package com.example.mob.feature.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mob.common.AppTopBar
import com.example.mob.ui.theme.*

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
        containerColor = AppBackground,
        contentWindowInsets = WindowInsets(0)
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(
                top = innerPadding.calculateTopPadding() + 16.dp,
                bottom = bottomPadding + 24.dp
            )
        ) {
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
                        value = "-",
                        badge = "-",
                        badgePositive = true,
                        chartColor = ScheduleBlue
                    )
                    HealthMetricCard(
                        icon = heartIcon,
                        iconBgColor = HealthRed,
                        title = "심박수",
                        value = "-",
                        badge = "-",
                        badgePositive = false,
                        chartColor = HealthRed
                    )
                    HealthMetricCard(
                        icon = sleepIcon,
                        iconBgColor = SchedulePurple,
                        title = "수면",
                        value = "-",
                        badge = "-",
                        badgePositive = true,
                        chartColor = ScheduleBlue
                    )
                }
            }
        }
    }
}
