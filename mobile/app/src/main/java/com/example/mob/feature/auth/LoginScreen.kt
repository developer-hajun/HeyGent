package com.example.mob.feature.auth

import android.util.Log
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mob.data.remote.KakaoLoginRequest
import com.example.mob.data.remote.RetrofitClient
import com.example.mob.ui.theme.TextSecondary
import com.kakao.sdk.common.model.ClientError
import com.kakao.sdk.common.model.ClientErrorCause
import com.kakao.sdk.user.UserApiClient
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(onLoginSuccess: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    val handleKakaoToken: (String) -> Unit = { kakaoAccessToken ->
        Log.d("KAKAO_LOGIN", "카카오 accessToken 수신: ${kakaoAccessToken.take(20)}...")
        scope.launch {
            isLoading = true
            errorMessage = null
            try {
                Log.d("AUTH_API", "POST /api/v1/auth/kakao/mobile 호출 시작")
                Log.d("AUTH_API", "요청 body: accessToken=${kakaoAccessToken.take(20)}...")
                val response = RetrofitClient.authApiService.kakaoLogin(
                    KakaoLoginRequest(accessToken = kakaoAccessToken)
                )
                Log.d("AUTH_API", "응답 수신: status=${response.status}, message=${response.message}")
                if (response.status == 200 && response.data != null) {
                    val serviceJwt = response.data.accessToken
                    val refreshToken = response.data.refreshToken
                    Log.d("AUTH_API", "로그인 성공 - JWT 발급 완료")
                    Log.d("AUTH_API", "serviceJwt: ${serviceJwt.take(20)}...")
                    Log.d("AUTH_API", "refreshToken: ${refreshToken.take(20)}...")
                    RetrofitClient.setToken(serviceJwt)
                    // TODO: refreshToken을 SharedPreferences/DataStore에 저장하여 자동 로그인에 활용
                    onLoginSuccess()
                } else {
                    Log.e("AUTH_API", "로그인 실패: status=${response.status}, message=${response.message}, data=${response.data}")
                    errorMessage = response.message
                }
            } catch (e: retrofit2.HttpException) {
                Log.e("AUTH_API", "HTTP 오류: code=${e.code()}, message=${e.message()}", e)
                errorMessage = "서버 오류가 발생했습니다. (${e.code()})"
            } catch (e: java.net.ConnectException) {
                Log.e("AUTH_API", "서버 연결 실패 - IP/포트 확인 필요", e)
                errorMessage = "서버에 연결할 수 없습니다."
            } catch (e: Exception) {
                Log.e("AUTH_API", "예외 발생: ${e.javaClass.simpleName}", e)
                errorMessage = "로그인 중 오류가 발생했습니다."
            } finally {
                isLoading = false
            }
        }
    }

    val loginWithKakaoAccount: () -> Unit = {
        UserApiClient.instance.loginWithKakaoAccount(context) { token, error ->
            if (error != null) {
                Log.e("KAKAO_LOGIN", "카카오계정 로그인 실패: ${error.javaClass.simpleName} - ${error.message}", error)
            } else if (token != null) {
                Log.d("KAKAO_LOGIN", "카카오 accessToken 발급 성공: ${token.accessToken.take(20)}...")
                handleKakaoToken(token.accessToken)
            }
        }
    }

    val onKakaoLoginClick: () -> Unit = {
        if (!isLoading) {
            if (UserApiClient.instance.isKakaoTalkLoginAvailable(context)) {
                Log.d("KAKAO_LOGIN", "카카오톡 앱으로 로그인 시도")
                UserApiClient.instance.loginWithKakaoTalk(context) { token, error ->
                    if (error != null) {
                        Log.e("KAKAO_LOGIN", "카카오톡 로그인 실패, 카카오계정으로 fallback", error)
                        if (error is ClientError && error.reason == ClientErrorCause.Cancelled) return@loginWithKakaoTalk
                        loginWithKakaoAccount()
                    } else if (token != null) {
                        handleKakaoToken(token.accessToken)
                    }
                }
            } else {
                Log.d("KAKAO_LOGIN", "카카오톡 미설치, 카카오계정으로 로그인 시도")
                loginWithKakaoAccount()
            }
        }
    }

    Box(
        modifier = Modifier
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

            if (isLoading) {
                CircularProgressIndicator(color = Color(0xFFFEE500))
            } else {
                KakaoLoginButton(onClick = onKakaoLoginClick)
            }

            if (errorMessage != null) {
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = errorMessage!!,
                    color = Color.Red,
                    fontSize = 13.sp,
                )
            }
        }

        Text(
            text = "로그인하면 서비스 이용약관 및 개인정보처리방침에 동의합니다",
            color = TextSecondary,
            fontSize = 11.sp,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 32.dp),
        )
    }
}

@Composable
private fun KakaoLoginButton(onClick: () -> Unit) {
    Box(
        modifier = Modifier
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
