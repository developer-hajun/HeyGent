module.exports = {
  // 한 줄이 너무 길어지지 않도록 100자 기준에서 줄바꿈합니다.
  printWidth: 100,

  // 들여쓰기는 공백 2칸을 사용합니다.
  tabWidth: 2,

  // 문자열은 기본적으로 작은따옴표를 사용합니다.
  singleQuote: true,

  // 문장 끝 세미콜론은 붙이지 않습니다.
  semi: false,

  // Tailwind 클래스는 Prettier가 권장 순서로 자동 정렬합니다.
  plugins: ['prettier-plugin-tailwindcss'],

  // 운영체제마다 줄바꿈 문자가 달라도 충돌이 덜 나도록 자동 처리합니다.
  endOfLine: 'auto',

  // 객체, 배열, 파라미터 끝에 가능한 곳은 trailing comma를 유지합니다.
  trailingComma: 'all',
}
