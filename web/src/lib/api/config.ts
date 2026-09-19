// .env.example 기준: 값이 명시적으로 'false'가 아니면 목(mock)을 사용한다.
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== 'false';
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
