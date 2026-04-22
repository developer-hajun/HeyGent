import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // 빌드 산출물은 lint 대상에서 제외합니다.
  globalIgnores(['dist']),
  {
    // 타입스크립트와 TSX 파일만 현재 규칙 대상으로 잡습니다.
    files: ['**/*.{ts,tsx}'],
    extends: [
      // 자바스크립트 기본 권장 규칙입니다.
      js.configs.recommended,
      // 타입스크립트 기본 권장 규칙입니다.
      tseslint.configs.recommended,
      // React Hooks 사용 규칙을 강제합니다.
      reactHooks.configs.flat.recommended,
      // Vite HMR 동작을 깨는 export 패턴을 점검합니다.
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      // 최신 문법을 충분히 해석할 수 있도록 ECMAScript 버전을 지정합니다.
      ecmaVersion: 2020,
      // 브라우저 전역 객체(window, document 등)를 기본 전역으로 인식합니다.
      globals: globals.browser,
    },
  },
])
