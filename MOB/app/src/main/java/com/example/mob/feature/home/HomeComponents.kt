package com.example.mob.feature.home

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Bedtime
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mob.ui.theme.*
import java.util.Calendar

data class ScheduleItem(val title: String, val time: String, val color: Color)
data class TodoItem(val title: String, val time: String, val color: Color)
data class CalEvent(val title: String, val color: Color)

val sampleSchedules = listOf(
    ScheduleItem("팀 회의", "오늘 · 오후 3:00", ScheduleBlue),
    ScheduleItem("병원 예약", "오늘 · 오후 5:30", SchedulePurple)
)

val sampleTodos = listOf(
    TodoItem("프로젝트 마감", "내일 · 오전 10:00", TodoOrange),
    TodoItem("운동하기", "매일 · 오전 7:00", TodoGreen)
)

@Composable
fun ScheduleCard(items: List<ScheduleItem>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceWhite),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("📅", fontSize = 16.sp)
                Spacer(modifier = Modifier.width(6.dp))
                Text("일정", fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = ScheduleBlue)
            }
            Spacer(modifier = Modifier.height(12.dp))
            items.forEach { item ->
                Row(
                    verticalAlignment = Alignment.Top,
                    modifier = Modifier.padding(bottom = 10.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .padding(top = 5.dp)
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(item.color)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(item.title, fontSize = 13.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
                        Text(item.time, fontSize = 11.sp, color = TextSecondary)
                    }
                }
            }
        }
    }
}

@Composable
fun TodoCard(items: List<TodoItem>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceWhite),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("☑️", fontSize = 16.sp)
                Spacer(modifier = Modifier.width(6.dp))
                Text("할일", fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = TodoOrange)
            }
            Spacer(modifier = Modifier.height(12.dp))
            items.forEach { item ->
                Row(
                    verticalAlignment = Alignment.Top,
                    modifier = Modifier.padding(bottom = 10.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .padding(top = 5.dp)
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(item.color)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(item.title, fontSize = 13.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
                        Text(item.time, fontSize = 11.sp, color = TextSecondary)
                    }
                }
            }
        }
    }
}

private data class CalendarMonth(val year: Int, val month: Int) {
    fun plusMonths(n: Int): CalendarMonth {
        val cal = Calendar.getInstance().apply { set(year, month - 1, 1); add(Calendar.MONTH, n) }
        return CalendarMonth(cal.get(Calendar.YEAR), cal.get(Calendar.MONTH) + 1)
    }
    fun daysInMonth(): Int =
        Calendar.getInstance().apply { set(year, month - 1, 1) }.getActualMaximum(Calendar.DAY_OF_MONTH)
    fun firstDayOfWeek(): Int {
        val javaDay = Calendar.getInstance().apply { set(year, month - 1, 1) }.get(Calendar.DAY_OF_WEEK)
        return (javaDay - 2 + 7) % 7
    }
    fun prevMonth(): CalendarMonth = plusMonths(-1)
}

@Composable
fun CalendarSection() {
    var currentMonth by remember { mutableStateOf(CalendarMonth(2026, 4)) }
    val todayYear = 2026; val todayMonth = 4; val todayDay = 27
    val scheduleDays = remember {
        mapOf(
            22 to listOf(CalEvent("팀 회의", ScheduleBlue), CalEvent("병원 예약", SchedulePurple)),
            23 to listOf(CalEvent("프로젝트", TodoOrange)),
            24 to listOf(CalEvent("운동", TodoGreen))
        )
    }
    var showRegisterSheet by remember { mutableStateOf(false) }

    if (showRegisterSheet) {
        CalendarRegisterSheet(onDismiss = { showRegisterSheet = false })
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceWhite),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {

            // 헤더 (축소)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("📅", fontSize = 14.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("달력", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                }
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(16.dp))
                        .background(NavyPrimary)
                        .clickable { showRegisterSheet = true }
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text("+ 등록", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // 월 내비게이션
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = { currentMonth = currentMonth.plusMonths(-1) },
                    modifier = Modifier.size(28.dp)
                ) {
                    Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "이전 달", tint = TextPrimary)
                }
                Text(
                    "${currentMonth.year}년 ${currentMonth.month}월",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = TextPrimary
                )
                IconButton(
                    onClick = { currentMonth = currentMonth.plusMonths(1) },
                    modifier = Modifier.size(28.dp)
                ) {
                    Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = "다음 달", tint = TextPrimary)
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            // 요일 헤더 (월요일 시작)
            Row(modifier = Modifier.fillMaxWidth()) {
                listOf("월", "화", "수", "목", "금", "토", "일").forEach { day ->
                    Text(
                        text = day,
                        modifier = Modifier.weight(1f),
                        textAlign = TextAlign.Center,
                        fontSize = 11.sp,
                        color = TextSecondary,
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            Spacer(modifier = Modifier.height(4.dp))

            // 날짜 그리드
            val firstDay = currentMonth.firstDayOfWeek()
            val daysInMonth = currentMonth.daysInMonth()
            val prevMonthDays = currentMonth.prevMonth().daysInMonth()
            val cells = mutableListOf<Triple<Int, Boolean, Boolean>>()
            for (i in firstDay downTo 1) cells.add(Triple(prevMonthDays - i + 1, false, false))
            for (d in 1..daysInMonth) {
                val isToday = currentMonth.year == todayYear && currentMonth.month == todayMonth && d == todayDay
                cells.add(Triple(d, true, isToday))
            }
            for (d in 1..(42 - cells.size)) cells.add(Triple(d, false, false))

            cells.chunked(7).forEach { week ->
                Row(modifier = Modifier.fillMaxWidth()) {
                    week.forEach { (day, isCurrentMonth, isToday) ->
                        val events = if (isCurrentMonth && currentMonth.year == todayYear && currentMonth.month == todayMonth)
                            scheduleDays[day] else null

                        Column(
                            modifier = Modifier
                                .weight(1f)
                                .padding(vertical = 2.dp)
                                .then(
                                    if (isCurrentMonth) Modifier.clickable(
                                        interactionSource = remember { MutableInteractionSource() },
                                        indication = null
                                    ) {} else Modifier
                                ),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            // 날짜 숫자
                            Box(
                                modifier = Modifier
                                    .size(26.dp)
                                    .then(
                                        if (isToday) Modifier.clip(CircleShape).background(Color.Black)
                                        else Modifier
                                    ),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = day.toString(),
                                    fontSize = 13.sp,
                                    fontWeight = if (isToday) FontWeight.Bold else FontWeight.Normal,
                                    color = when {
                                        isToday         -> Color.White
                                        !isCurrentMonth -> TextHint
                                        else            -> TextPrimary
                                    }
                                )
                            }

                            // 이벤트 칩 영역
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 2.dp)
                                    .height(14.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                if (!events.isNullOrEmpty()) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(1.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .weight(1f)
                                                .clip(RoundedCornerShape(3.dp))
                                                .background(events.first().color.copy(alpha = 0.18f))
                                                .padding(horizontal = 2.dp, vertical = 2.dp),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Text(
                                                text = events.first().title,
                                                fontSize = if (events.size > 1) 6.sp else 7.sp,
                                                color = events.first().color,
                                                maxLines = 1,
                                                overflow = TextOverflow.Ellipsis,
                                                textAlign = TextAlign.Center
                                            )
                                        }
                                        if (events.size > 1) {
                                            Box(
                                                modifier = Modifier
                                                    .clip(RoundedCornerShape(3.dp))
                                                    .background(TextHint.copy(alpha = 0.2f))
                                                    .padding(horizontal = 2.dp, vertical = 2.dp),
                                                contentAlignment = Alignment.Center
                                            ) {
                                                Text(
                                                    text = "+${events.size - 1}",
                                                    fontSize = 6.sp,
                                                    color = TextSecondary
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun HealthMetricCard(
    icon: ImageVector,
    iconBgColor: Color,
    title: String,
    value: String,
    badge: String,
    badgePositive: Boolean = true,
    chartColor: Color
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceWhite),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(iconBgColor),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(icon, contentDescription = null, tint = Color.White, modifier = Modifier.size(26.dp))
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(title, fontSize = 13.sp, color = TextSecondary)
                    Text(value, fontSize = 22.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(
                            if (badgePositive) TodoGreen.copy(alpha = 0.1f)
                            else Color.Gray.copy(alpha = 0.1f)
                        )
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = badge,
                        fontSize = 12.sp,
                        color = if (badgePositive) TodoGreen else TextSecondary,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
            Spacer(modifier = Modifier.height(12.dp))
            SimpleLineChart(chartColor)
        }
    }
}

val stepsIcon = Icons.Default.ShowChart
val heartIcon = Icons.Default.Favorite
val sleepIcon = Icons.Default.Bedtime

@Composable
fun SimpleLineChart(lineColor: Color) {
    val points = listOf(0.4f, 0.5f, 0.3f, 0.6f, 0.5f, 0.7f, 0.55f, 0.65f, 0.6f)
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(36.dp)
    ) {
        val w = size.width
        val h = size.height
        val path = Path()
        points.forEachIndexed { i, v ->
            val x = i / (points.size - 1).toFloat() * w
            val y = h - v * h
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, color = lineColor, style = Stroke(width = 3.dp.toPx(), cap = StrokeCap.Round))
    }
}
