package com.example.mob.feature.home

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.mob.ui.theme.*
import java.util.Calendar

private val reminderOptions = listOf("없음", "시작 시", "10분 전", "20분 전", "30분 전", "1시간 전", "1일 전")
private val repeatCycleOptions = listOf("안 함", "매일", "매주", "매월", "매년")

private val eventColors = listOf(
    Color(0xFF4A90E2),
    Color(0xFF7B68EE),
    Color(0xFFFF8C00),
    Color(0xFF4CAF50),
    Color(0xFFE74C3C),
    Color(0xFFEC407A),
    Color(0xFF00ACC1),
    Color(0xFFFFC107),
    Color(0xFF8D6E63),
    Color(0xFF2E3A59)
)

private val demoScheduleDays = mapOf(
    "2026-4-22" to listOf("팀 회의", "병원 예약"),
    "2026-4-23" to listOf("프로젝트"),
    "2026-4-24" to listOf("운동")
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalendarRegisterSheet(onDismiss: () -> Unit) {
    val today = remember {
        val c = Calendar.getInstance()
        "${c.get(Calendar.YEAR)}. ${c.get(Calendar.MONTH) + 1}. ${c.get(Calendar.DAY_OF_MONTH)}"
    }

    var selectedTab by remember { mutableIntStateOf(0) }

    // 일정
    var scheduleTitle    by remember { mutableStateOf("") }
    var scheduleDate     by remember { mutableStateOf(today) }
    var scheduleAllDay   by remember { mutableStateOf(true) }
    var scheduleStart    by remember { mutableStateOf("09:00") }
    var scheduleEnd      by remember { mutableStateOf("10:00") }
    var scheduleReminder by remember { mutableStateOf("없음") }
    var scheduleColor    by remember { mutableStateOf(eventColors[0]) }

    // 할 일
    var todoTitle        by remember { mutableStateOf("") }
    var todoDate         by remember { mutableStateOf(today) }
    var todoHasDeadline  by remember { mutableStateOf(false) }
    var todoDeadline     by remember { mutableStateOf("18:00") }
    var todoReminder     by remember { mutableStateOf("없음") }
    var todoColor        by remember { mutableStateOf(eventColors[2]) }

    // 반복
    var repeatTitle  by remember { mutableStateOf("") }
    var repeatCycle  by remember { mutableStateOf("안 함") }
    var repeatStart  by remember { mutableStateOf(today) }
    var repeatHasEnd by remember { mutableStateOf(false) }
    var repeatEnd    by remember { mutableStateOf(today) }
    var repeatAlarm  by remember { mutableStateOf("없음") }
    var repeatColor  by remember { mutableStateOf(eventColors[1]) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = Color.White,
        dragHandle = {
            Box(
                Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 4.dp),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    Modifier
                        .size(width = 36.dp, height = 4.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(Color(0xFFDDDDDD))
                )
            }
        }
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("등록", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, contentDescription = "닫기", tint = TextPrimary)
                }
            }

            TabRow(
                selectedTabIndex = selectedTab,
                containerColor = Color.White,
                contentColor = Color.Black
            ) {
                listOf("일정", "할 일", "반복").forEachIndexed { i, label ->
                    Tab(
                        selected = selectedTab == i,
                        onClick = { selectedTab = i },
                        text = {
                            Text(
                                label,
                                fontWeight = if (selectedTab == i) FontWeight.SemiBold else FontWeight.Normal,
                                color = if (selectedTab == i) Color.Black else TextSecondary
                            )
                        }
                    )
                }
            }

            Spacer(Modifier.height(20.dp))

            Column(modifier = Modifier.fillMaxWidth()) {
                when (selectedTab) {
                    0 -> ScheduleFormContent(
                        title = scheduleTitle, onTitleChange = { scheduleTitle = it },
                        date = scheduleDate, onDateChange = { scheduleDate = it },
                        isAllDay = scheduleAllDay, onAllDayChange = { scheduleAllDay = it },
                        startTime = scheduleStart, onStartChange = { scheduleStart = it },
                        endTime = scheduleEnd, onEndChange = { scheduleEnd = it },
                        reminder = scheduleReminder, onReminderChange = { scheduleReminder = it },
                        selectedColor = scheduleColor, onColorChange = { scheduleColor = it }
                    )
                    1 -> TodoFormContent(
                        title = todoTitle, onTitleChange = { todoTitle = it },
                        date = todoDate, onDateChange = { todoDate = it },
                        hasDeadline = todoHasDeadline, onHasDeadlineChange = { todoHasDeadline = it },
                        deadlineTime = todoDeadline, onDeadlineTimeChange = { todoDeadline = it },
                        reminder = todoReminder, onReminderChange = { todoReminder = it },
                        selectedColor = todoColor, onColorChange = { todoColor = it }
                    )
                    2 -> RepeatFormContent(
                        title = repeatTitle, onTitleChange = { repeatTitle = it },
                        cycle = repeatCycle, onCycleChange = { repeatCycle = it },
                        startDate = repeatStart, onStartDateChange = { repeatStart = it },
                        hasEnd = repeatHasEnd, onHasEndChange = { repeatHasEnd = it },
                        endDate = repeatEnd, onEndDateChange = { repeatEnd = it },
                        alarm = repeatAlarm, onAlarmChange = { repeatAlarm = it },
                        selectedColor = repeatColor, onColorChange = { repeatColor = it }
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            Button(
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth().height(52.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color.Black)
            ) {
                Text("등록", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
            }

            Spacer(Modifier.height(40.dp))
        }
    }
}

// ─── 일정 폼 ───────────────────────────────────────────────────────────────

@Composable
private fun ScheduleFormContent(
    title: String, onTitleChange: (String) -> Unit,
    date: String, onDateChange: (String) -> Unit,
    isAllDay: Boolean, onAllDayChange: (Boolean) -> Unit,
    startTime: String, onStartChange: (String) -> Unit,
    endTime: String, onEndChange: (String) -> Unit,
    reminder: String, onReminderChange: (String) -> Unit,
    selectedColor: Color, onColorChange: (Color) -> Unit
) {
    FormLabel("제목")
    RegTextField(value = title, onValueChange = onTitleChange, placeholder = "제목을 입력하세요")

    Spacer(Modifier.height(16.dp))
    FormLabel("날짜")
    DateChip(date, onDateChange)

    Spacer(Modifier.height(12.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(8.dp))

    ToggleRow("종일", isAllDay, onAllDayChange)

    AnimatedVisibility(
        visible = !isAllDay,
        enter = expandVertically(expandFrom = Alignment.Top) + fadeIn(),
        exit = shrinkVertically(shrinkTowards = Alignment.Top) + fadeOut()
    ) {
        Column {
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TimePickerCell(startTime, onStartChange, Modifier.weight(1f))
                Text("~", fontSize = 14.sp, color = TextSecondary)
                TimePickerCell(endTime, onEndChange, Modifier.weight(1f))
            }
        }
    }

    Spacer(Modifier.height(8.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(8.dp))

    ReminderRow(reminder, onReminderChange)

    Spacer(Modifier.height(8.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(8.dp))

    ColorPickerRow(selectedColor, onColorChange)
    Spacer(Modifier.height(4.dp))
}

// ─── 할 일 폼 ──────────────────────────────────────────────────────────────

@Composable
private fun TodoFormContent(
    title: String, onTitleChange: (String) -> Unit,
    date: String, onDateChange: (String) -> Unit,
    hasDeadline: Boolean, onHasDeadlineChange: (Boolean) -> Unit,
    deadlineTime: String, onDeadlineTimeChange: (String) -> Unit,
    reminder: String, onReminderChange: (String) -> Unit,
    selectedColor: Color, onColorChange: (Color) -> Unit
) {
    FormLabel("제목")
    RegTextField(value = title, onValueChange = onTitleChange, placeholder = "제목을 입력하세요")

    Spacer(Modifier.height(16.dp))
    FormLabel("날짜")
    DateChip(date, onDateChange)

    Spacer(Modifier.height(12.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(8.dp))

    ToggleRow("마감 시간", hasDeadline, onHasDeadlineChange)

    AnimatedVisibility(
        visible = hasDeadline,
        enter = expandVertically(expandFrom = Alignment.Top) + fadeIn(),
        exit = shrinkVertically(shrinkTowards = Alignment.Top) + fadeOut()
    ) {
        Column {
            Spacer(Modifier.height(8.dp))
            TimePickerCell(deadlineTime, onDeadlineTimeChange)
        }
    }

    Spacer(Modifier.height(8.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(8.dp))

    ReminderRow(reminder, onReminderChange)

    Spacer(Modifier.height(8.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(8.dp))

    ColorPickerRow(selectedColor, onColorChange)
    Spacer(Modifier.height(4.dp))
}

// ─── 반복 폼 ──────────────────────────────────────────────────────────────

@Composable
private fun RepeatFormContent(
    title: String, onTitleChange: (String) -> Unit,
    cycle: String, onCycleChange: (String) -> Unit,
    startDate: String, onStartDateChange: (String) -> Unit,
    hasEnd: Boolean, onHasEndChange: (Boolean) -> Unit,
    endDate: String, onEndDateChange: (String) -> Unit,
    alarm: String, onAlarmChange: (String) -> Unit,
    selectedColor: Color, onColorChange: (Color) -> Unit
) {
    FormLabel("제목")
    RegTextField(value = title, onValueChange = onTitleChange, placeholder = "제목을 입력하세요")

    Spacer(Modifier.height(16.dp))

    FormRow(label = "반복 주기") {
        SimpleDropdown(cycle, repeatCycleOptions, onCycleChange)
    }

    Spacer(Modifier.height(4.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(12.dp))

    FormRow(label = "시작일") {
        DateChip(startDate, onStartDateChange)
    }

    Spacer(Modifier.height(4.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(12.dp))

    FormRow(label = "반복 종료") {
        if (hasEnd) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                DateChip(endDate, onEndDateChange)
                Spacer(Modifier.width(6.dp))
                IconButton(
                    onClick = { onHasEndChange(false) },
                    modifier = Modifier.size(24.dp)
                ) {
                    Icon(Icons.Default.Close, contentDescription = null, modifier = Modifier.size(16.dp), tint = TextSecondary)
                }
            }
        } else {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(AppBackground)
                    .clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = null
                    ) { onHasEndChange(true) }
                    .padding(horizontal = 14.dp, vertical = 8.dp)
            ) {
                Text("안 함", fontSize = 13.sp, color = TextSecondary)
            }
        }
    }

    Spacer(Modifier.height(4.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(12.dp))

    ReminderRow(alarm, onAlarmChange)

    Spacer(Modifier.height(8.dp))
    HorizontalDivider(color = DividerColor)
    Spacer(Modifier.height(8.dp))

    ColorPickerRow(selectedColor, onColorChange)
    Spacer(Modifier.height(4.dp))
}

// ─── 색상 선택 ─────────────────────────────────────────────────────────────

@Composable
private fun ColorPickerRow(selectedColor: Color, onColorChange: (Color) -> Unit) {
    var showPicker by remember { mutableStateOf(false) }

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text("색상", fontSize = 14.sp, color = TextPrimary)
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(AppBackground)
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null
                ) { showPicker = true }
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(18.dp)
                    .clip(CircleShape)
                    .background(selectedColor)
            )
            Spacer(Modifier.width(8.dp))
            Icon(
                Icons.Default.KeyboardArrowDown,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = TextSecondary
            )
        }
    }

    if (showPicker) {
        Dialog(onDismissRequest = { showPicker = false }) {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f)),
                elevation = CardDefaults.cardElevation(16.dp)
            ) {
                Column(modifier = Modifier.padding(24.dp)) {
                    Text(
                        "색상 선택",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Spacer(Modifier.height(20.dp))
                    eventColors.chunked(5).forEach { rowColors ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly
                        ) {
                            rowColors.forEach { color ->
                                Box(
                                    modifier = Modifier
                                        .size(44.dp)
                                        .clip(CircleShape)
                                        .background(color)
                                        .then(
                                            if (color == selectedColor)
                                                Modifier.border(3.dp, Color.Black, CircleShape)
                                            else
                                                Modifier.border(2.dp, Color.White.copy(alpha = 0.6f), CircleShape)
                                        )
                                        .clickable(
                                            interactionSource = remember { MutableInteractionSource() },
                                            indication = null
                                        ) {
                                            onColorChange(color)
                                            showPicker = false
                                        }
                                )
                            }
                        }
                        Spacer(Modifier.height(14.dp))
                    }
                }
            }
        }
    }
}

// ─── 공통 컴포넌트 ─────────────────────────────────────────────────────────

@Composable
private fun FormLabel(text: String) {
    Text(text, fontSize = 12.sp, color = TextSecondary, fontWeight = FontWeight.Medium)
    Spacer(Modifier.height(6.dp))
}

@Composable
private fun FormRow(label: String, content: @Composable () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = 14.sp, color = TextPrimary)
        content()
    }
}

@Composable
private fun ToggleRow(label: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = 14.sp, color = TextPrimary)
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Color.White,
                checkedTrackColor = Color.Black,
                uncheckedThumbColor = Color.White,
                uncheckedTrackColor = Color(0xFFDDDDDD)
            )
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun RegTextField(value: String, onValueChange: (String) -> Unit, placeholder: String) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        placeholder = { Text(placeholder, color = TextHint) },
        singleLine = true,
        shape = RoundedCornerShape(10.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = Color.Black,
            unfocusedBorderColor = DividerColor
        )
    )
}

@Composable
private fun DateChip(date: String, onDateChange: (String) -> Unit) {
    var showPicker by remember { mutableStateOf(false) }

    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(AppBackground)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null
            ) { showPicker = true }
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(Icons.Default.CalendarToday, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(6.dp))
        Text(date, fontSize = 13.sp, color = TextPrimary)
    }

    if (showPicker) {
        CalendarPickerDialog(
            onDismiss = { showPicker = false },
            onDateSelected = { selected ->
                onDateChange(selected)
                showPicker = false
            }
        )
    }
}

@Composable
private fun CalendarPickerDialog(
    onDismiss: () -> Unit,
    onDateSelected: (String) -> Unit
) {
    val cal = remember { Calendar.getInstance() }
    var viewYear  by remember { mutableIntStateOf(cal.get(Calendar.YEAR)) }
    var viewMonth by remember { mutableIntStateOf(cal.get(Calendar.MONTH) + 1) }
    var selYear   by remember { mutableIntStateOf(cal.get(Calendar.YEAR)) }
    var selMonth  by remember { mutableIntStateOf(cal.get(Calendar.MONTH) + 1) }
    var selDay    by remember { mutableIntStateOf(cal.get(Calendar.DAY_OF_MONTH)) }

    val todayYear  = 2026
    val todayMonth = 4
    val todayDay   = 27

    Dialog(onDismissRequest = onDismiss) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(8.dp)
        ) {
            Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = {
                        val c = Calendar.getInstance().apply { set(viewYear, viewMonth - 1, 1); add(Calendar.MONTH, -1) }
                        viewYear = c.get(Calendar.YEAR); viewMonth = c.get(Calendar.MONTH) + 1
                    }, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = null, tint = TextPrimary)
                    }
                    Text("${viewYear}년 ${viewMonth}월", fontSize = 15.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
                    IconButton(onClick = {
                        val c = Calendar.getInstance().apply { set(viewYear, viewMonth - 1, 1); add(Calendar.MONTH, 1) }
                        viewYear = c.get(Calendar.YEAR); viewMonth = c.get(Calendar.MONTH) + 1
                    }, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = TextPrimary)
                    }
                }

                Spacer(Modifier.height(8.dp))

                // 요일 헤더 (월요일 시작)
                Row(modifier = Modifier.fillMaxWidth()) {
                    listOf("월", "화", "수", "목", "금", "토", "일").forEach { d ->
                        Text(
                            text = d,
                            modifier = Modifier.weight(1f),
                            textAlign = TextAlign.Center,
                            fontSize = 12.sp,
                            color = TextSecondary,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }

                Spacer(Modifier.height(6.dp))

                // 월요일 시작으로 firstDay 계산
                val javaFirstDay = Calendar.getInstance().apply { set(viewYear, viewMonth - 1, 1) }.get(Calendar.DAY_OF_WEEK)
                val firstDay = (javaFirstDay - 2 + 7) % 7
                val daysInMonth = Calendar.getInstance().apply { set(viewYear, viewMonth - 1, 1) }.getActualMaximum(Calendar.DAY_OF_MONTH)
                val prevDays = Calendar.getInstance().apply { set(viewYear, viewMonth - 1, 1); add(Calendar.MONTH, -1) }.getActualMaximum(Calendar.DAY_OF_MONTH)

                val cells = mutableListOf<Triple<Int, Boolean, Boolean>>()
                for (i in firstDay downTo 1) cells.add(Triple(prevDays - i + 1, false, false))
                for (d in 1..daysInMonth) {
                    val isToday = viewYear == todayYear && viewMonth == todayMonth && d == todayDay
                    cells.add(Triple(d, true, isToday))
                }
                for (d in 1..(42 - cells.size)) cells.add(Triple(d, false, false))

                cells.chunked(7).forEach { week ->
                    Row(modifier = Modifier.fillMaxWidth()) {
                        week.forEach { (day, isCurrentMonth, isToday) ->
                            val isSelected = isCurrentMonth && day == selDay && viewYear == selYear && viewMonth == selMonth
                            val events = if (isCurrentMonth) demoScheduleDays["$viewYear-$viewMonth-$day"] else null

                            Column(
                                modifier = Modifier
                                    .weight(1f)
                                    .padding(vertical = 2.dp)
                                    .then(
                                        if (isCurrentMonth) Modifier.clickable(
                                            interactionSource = remember { MutableInteractionSource() },
                                            indication = null
                                        ) {
                                            selYear = viewYear; selMonth = viewMonth; selDay = day
                                        } else Modifier
                                    ),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(28.dp)
                                        .then(
                                            when {
                                                isSelected -> Modifier.clip(CircleShape).background(Color.Black)
                                                isToday    -> Modifier.clip(CircleShape).background(NavyPrimary)
                                                else       -> Modifier
                                            }
                                        ),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = day.toString(),
                                        fontSize = 12.sp,
                                        color = when {
                                            isSelected || isToday -> Color.White
                                            !isCurrentMonth       -> TextHint
                                            else                  -> TextPrimary
                                        },
                                        fontWeight = if (isSelected || isToday) FontWeight.Bold else FontWeight.Normal
                                    )
                                }
                                Box(
                                    modifier = Modifier.fillMaxWidth().height(14.dp),
                                    contentAlignment = Alignment.TopCenter
                                ) {
                                    if (!events.isNullOrEmpty()) {
                                        Text(
                                            text = events.first(),
                                            fontSize = 7.sp,
                                            color = ScheduleBlue,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                            textAlign = TextAlign.Center,
                                            modifier = Modifier.fillMaxWidth().padding(horizontal = 1.dp)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                Spacer(Modifier.height(8.dp))

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = onDismiss) {
                        Text("취소", color = TextSecondary)
                    }
                    TextButton(onClick = { onDateSelected("$selYear. $selMonth. $selDay") }) {
                        Text("확인", color = Color.Black, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
    }
}

@Composable
private fun TimePickerCell(time: String, onTimeChange: (String) -> Unit, modifier: Modifier = Modifier) {
    var showPicker by remember { mutableStateOf(false) }
    val parts = time.split(":")
    var tempHour   by remember(time) { mutableIntStateOf(parts[0].toIntOrNull() ?: 9) }
    var tempMinute by remember(time) { mutableIntStateOf(parts[1].toIntOrNull() ?: 0) }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(AppBackground)
            .clickable { showPicker = true }
            .padding(vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(time, fontSize = 15.sp, color = TextPrimary, fontWeight = FontWeight.SemiBold)
    }

    if (showPicker) {
        AlertDialog(
            onDismissRequest = { showPicker = false },
            title = { Text("시간 선택", fontWeight = FontWeight.Bold) },
            text = {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        IconButton(onClick = { if (tempHour < 23) tempHour++ }) {
                            Icon(Icons.Default.KeyboardArrowUp, contentDescription = null)
                        }
                        Text("%02d".format(tempHour), fontSize = 28.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                        IconButton(onClick = { if (tempHour > 0) tempHour-- }) {
                            Icon(Icons.Default.KeyboardArrowDown, contentDescription = null)
                        }
                    }
                    Text("  :  ", fontSize = 28.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        IconButton(onClick = { tempMinute = (tempMinute + 5) % 60 }) {
                            Icon(Icons.Default.KeyboardArrowUp, contentDescription = null)
                        }
                        Text("%02d".format(tempMinute), fontSize = 28.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                        IconButton(onClick = { tempMinute = (tempMinute - 5 + 60) % 60 }) {
                            Icon(Icons.Default.KeyboardArrowDown, contentDescription = null)
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    onTimeChange("%02d:%02d".format(tempHour, tempMinute))
                    showPicker = false
                }) { Text("확인", color = Color.Black, fontWeight = FontWeight.SemiBold) }
            },
            dismissButton = {
                TextButton(onClick = { showPicker = false }) { Text("취소", color = TextSecondary) }
            },
            containerColor = Color.White
        )
    }
}

@Composable
private fun ReminderRow(reminder: String, onReminderChange: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text("미리 알림", fontSize = 14.sp, color = TextPrimary)
        Box {
            Row(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(AppBackground)
                    .clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = null
                    ) { expanded = true }
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(reminder, fontSize = 13.sp, color = TextPrimary)
                Spacer(Modifier.width(4.dp))
                Icon(Icons.Default.KeyboardArrowUp, contentDescription = null, modifier = Modifier.size(16.dp), tint = TextSecondary)
            }
            DropdownMenu(
                expanded = expanded,
                onDismissRequest = { expanded = false },
                containerColor = Color.White
            ) {
                reminderOptions.forEach { option ->
                    DropdownMenuItem(
                        text = { Text(option, fontSize = 14.sp) },
                        onClick = { onReminderChange(option); expanded = false }
                    )
                }
            }
        }
    }
}

@Composable
private fun SimpleDropdown(selected: String, options: List<String>, onSelect: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(AppBackground)
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null
                ) { expanded = true }
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(selected, fontSize = 13.sp, color = TextPrimary)
            Spacer(Modifier.width(4.dp))
            Icon(Icons.Default.KeyboardArrowDown, contentDescription = null, modifier = Modifier.size(16.dp), tint = TextSecondary)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }, containerColor = Color.White) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option, fontSize = 14.sp) },
                    onClick = { onSelect(option); expanded = false }
                )
            }
        }
    }
}
