import { useNavigate } from 'react-router-dom';

function LandingPage() {
  const navigate = useNavigate();

  const features = [
    {
      badge: 'ASYNC PARALLEL ENGINE',
      title: '비동기 병렬 추론 아키텍처',
      desc: 'FastAPI 비동기 코루틴(asyncio)을 활용하여 단일 프롬프트를 다중 파운데이션 모델에 동시 전송하고 응답을 병렬 수집합니다.'
    },
    {
      badge: 'QUANTITATIVE METRICS',
      title: '실시간 지연시간 & 토큰 분석',
      desc: '각 모델의 네트워크 왕복 지연 시간(Latency, ms)과 토큰 소모량(Token Usage)을 실시간 측정하여 정량적 비교 지표를 제공합니다.'
    },
    {
      badge: 'DEVSECOPS INFRA',
      title: '무포트(Port-less) 보안 및 과금 방어',
      desc: 'AWS SSM 기반 CI/CD 파이프라인과 IP 기반 Rate Limiting(slowapi), 입력 길이 검증을 통해 엔터프라이즈급 보안을 구현했습니다.'
    }
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#0d1117', color: '#c9d1d9', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '2rem 1.5rem', boxSizing: 'border-box' }}>
      {/* 상단 네비게이션 헤더 */}
      <header style={{ maxWidth: '1100px', width: '100%', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #21262d', paddingBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontWeight: 'bold', fontSize: '1.1rem', color: '#f0f6fc' }}>
          <span style={{ background: '#238636', color: 'white', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>AWS</span>
          <span>Bedrock Eval Platform</span>
        </div>
        <span style={{ fontSize: '0.85rem', color: '#8b949e', border: '1px solid #30363d', padding: '0.3rem 0.7rem', borderRadius: '20px', background: '#161b22' }}>
          v1.0 Production
        </span>
      </header>

      {/* 중앙 히어로 섹션 (글자 겹침 완벽 해결) */}
      <main style={{ maxWidth: '960px', width: '100%', margin: '4rem auto', textAlign: 'center' }}>
        <div style={{ display: 'inline-block', background: 'rgba(56, 139, 253, 0.1)', color: '#58a6ff', border: '1px solid rgba(56, 139, 253, 0.4)', padding: '0.4rem 1rem', borderRadius: '20px', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '1.5rem' }}>
          Amazon Bedrock 기반 다중 LLM 성능 비교 솔루션
        </div>

        <h1 style={{ fontSize: 'clamp(2.2rem, 5vw, 3.6rem)', lineHeight: '1.25', fontWeight: '800', color: '#f0f6fc', margin: '0 0 1.5rem 0', letterSpacing: '-0.02em', wordBreak: 'keep-all' }}>
          Multi-LLM Prompt<br />
          <span style={{ color: '#58a6ff' }}>Evaluation Console</span>
        </h1>

        <p style={{ fontSize: '1.15rem', color: '#8b949e', maxWidth: '680px', margin: '0 auto 2.5rem auto', lineHeight: '1.7', wordBreak: 'keep-all' }}>
          단 한 번의 프롬프트 입력으로 <strong>Claude 3 Sonnet</strong>, <strong>Claude 3 Haiku</strong>, <strong>Llama 3</strong>의 실제 출력 결과와 응답 속도(Latency), 토큰 사용량을 실시간으로 비교 분석하세요.
        </p>

        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '4rem' }}>
          <button
            onClick={() => navigate('/app')}
            style={{ padding: '1rem 2.4rem', fontSize: '1.15rem', background: '#238636', color: 'white', border: '1px solid rgba(240,246,252,0.1)', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', boxShadow: '0 4px 14px rgba(35, 134, 54, 0.4)' }}
          >
            프롬프트 평가 시작하기 →
          </button>
        </div>

        {/* 하단 3대 핵심 기능 카드 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.2rem', textAlign: 'left' }}>
          {features.map((item, idx) => (
            <div key={idx} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '1.5rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#79c0ff', marginBottom: '0.6rem', letterSpacing: '0.05em' }}>
                {item.badge}
              </div>
              <h3 style={{ fontSize: '1.15rem', color: '#f0f6fc', margin: '0 0 0.8rem 0' }}>
                {item.title}
              </h3>
              <p style={{ fontSize: '0.92rem', color: '#8b949e', margin: 0, lineHeight: '1.6', wordBreak: 'keep-all' }}>
                {item.desc}
              </p>
            </div>
          ))}
        </div>
      </main>

      {/* 푸터 */}
      <footer style={{ textAlign: 'center', color: '#484f58', fontSize: '0.85rem', borderTop: '1px solid #21262d', paddingTop: '1rem', maxWidth: '1100px', width: '100%', margin: '0 auto' }}>
        Architecture: React (S3 + CloudFront) • FastAPI (AWS EC2 + Nginx) • Amazon RDS (PostgreSQL) • GitHub Actions (AWS SSM)
      </footer>
    </div>
  );
}

export default LandingPage;