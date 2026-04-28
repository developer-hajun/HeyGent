package com.example.mob.feature.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mob.ui.theme.TextSecondary

@Composable
fun LoginScreen(onLoginSuccess: () -> Unit) {
    Box(
        modifier =
            Modifier
                .fillMaxSize()
                .background(Color.White),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = "HEYGENT",
                color = Color.Black,
                fontSize = 38.sp,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = 6.sp,
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "당신의 맞춤형 어시스턴트",
                color = TextSecondary,
                fontSize = 14.sp,
                letterSpacing = 1.sp,
            )

            Spacer(modifier = Modifier.height(80.dp))

            KakaoLoginButton(onClick = onLoginSuccess)
        }

        Text(
            text = "로그인하면 서비스 이용약관 및 개인정보처리방침에 동의합니다",
            color = TextSecondary,
            fontSize = 11.sp,
            modifier =
                Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 32.dp),
        )
    }
}

@Composable
private fun KakaoLoginButton(onClick: () -> Unit) {
    Box(
        modifier =
            Modifier
                .width(280.dp)
                .height(52.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFFFEE500))
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                    onClick = onClick,
                ),
        contentAlignment = Alignment.Center,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center,
        ) {
            Text(text = "💬", fontSize = 18.sp)
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "카카오로 계속하기",
                color = Color(0xFF3A1D1D),
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}
