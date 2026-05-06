import { useNavigate } from 'react-router'
import { devLogin } from '@/apis/auth'
import { getMyInfo } from '@/apis/users'
import { useAuthStore } from '@/store/useAuthStore'

const KAKAO_AUTH_URL =
  `https://kauth.kakao.com/oauth/authorize` +
  `?client_id=${import.meta.env.VITE_KAKAO_CLIENT_ID}` +
  `&redirect_uri=${import.meta.env.VITE_KAKAO_REDIRECT_URI}` +
  `&response_type=code`

function KakaoIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M12 3C6.477 3 2 6.597 2 11.05c0 2.845 1.636 5.35 4.121 6.878l-1.05 3.894c-.09.337.285.605.573.408L10.1 19.6c.613.088 1.24.134 1.9.134 5.523 0 10-3.597 10-8.05C22 6.597 17.523 3 12 3z" />
    </svg>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const { setTokens, setUserInfo } = useAuthStore()

  const handleKakaoLogin = () => {
    window.location.href = KAKAO_AUTH_URL
  }

  const handleDevLogin = async () => {
    try {
      const res = await devLogin()
      setTokens(res.data.accessToken, res.data.refreshToken)
      try {
        const userRes = await getMyInfo()
        setUserInfo(userRes.data)
      } catch {
        // 사용자 정보 조회 실패해도 로그인 진행
      }
      navigate('/', { replace: true })
    } catch {
      // 개발 서버가 없으면 무시
    }
  }

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-[#f2f3f8] px-4 sm:px-6 dark:bg-[#0f1117]">
      {/* Card */}
      <div className="w-full max-w-sm space-y-8 rounded-3xl border border-black/6 bg-white px-6 py-8 shadow-xl sm:px-8 sm:py-10 dark:border-white/8 dark:bg-white/5">
        {/* Logo */}
        <div className="flex flex-col items-center gap-1">
          <span
            className="tracking-tight select-none"
            style={{ fontFamily: 'var(--font-display)', fontSize: '36px', fontWeight: 800 }}
          >
            <span className="text-foreground">Hey</span>
            <span
              style={{
                background: 'linear-gradient(135deg, var(--primary) 0%, var(--chart-5) 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              G
            </span>
            <span className="text-foreground">ent</span>
          </span>
          <span
            className="text-muted-foreground tracking-widest select-none"
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: '10px',
              fontWeight: 500,
            }}
          >
            AI 협업 생중계
          </span>
        </div>

        {/* Description */}
        <div className="space-y-1 text-center">
          <p className="text-foreground text-sm font-medium">AI 에이전트와 함께 시작하세요</p>
          <p className="text-muted-foreground text-xs leading-relaxed">
            카카오 계정으로 간편하게 로그인하고
            <br />
            전문 AI 에이전트와 협업하세요.
          </p>
        </div>

        {/* Kakao Login Button */}
        <div className="space-y-2">
          <button
            onClick={handleKakaoLogin}
            className="flex w-full items-center justify-center gap-2.5 rounded-xl px-6 py-3.5 text-sm font-semibold transition-all duration-150 hover:opacity-90 active:scale-[0.98]"
            style={{ backgroundColor: '#FEE500', color: '#191600' }}
          >
            <KakaoIcon />
            <span>카카오 계정으로 로그인</span>
          </button>

          {import.meta.env.DEV && (
            <button
              onClick={handleDevLogin}
              className="text-muted-foreground hover:text-foreground w-full rounded-xl border border-dashed border-current px-6 py-3 text-xs font-medium transition-colors duration-150"
            >
              개발용 테스트 로그인
            </button>
          )}
        </div>
      </div>

      {/* Footer */}
      <p className="text-muted-foreground mt-8 text-center text-xs">
        © 2025 HeyGent. All rights reserved.
      </p>
    </div>
  )
}
