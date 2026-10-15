import { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

// [Phase 3 신규] 랜딩 페이지 컴포넌트
function LandingPage() {
  const navigate = useNavigate();
  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', textAlign: 'center' }}>
      <h1 style={{ fontSize: '3.5rem', marginBottom: '1rem', color: '#c9d1d9' }}>Multi-LLM Evaluation Console</h1>
      <p style={{ fontSize: '1.2rem', color: '#8b949e', marginBottom: '3rem', maxWidth: '600px', lineHeight: '1.6' }}>
        Amazon Bedrock 기반 다중 대형언어모델(LLM) 통합 성능 평가 플랫폼입니다. 
        단 한 번의 프롬프트 입력으로 다양한 AI 모델의 응답 속도, 비용, 퀄리티를 비교 분석하세요.
      </p>
      <button 
        onClick={() => navigate('/app')}
        style={{ padding: '1rem 2.5rem', fontSize: '1.2rem', background: '#2ea043', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', transition: 'background 0.2s' }}
      >
        프롬프트 평가 시작하기
      </button>
    </div>
  );
}

// [Phase 3 분리] 기존 메인 대시보드 컴포넌트
function Dashboard() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState(['Claude-3-Sonnet']);
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const [isCooldown, setIsCooldown] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [activeTab, setActiveTab] = useState('evaluation');
  const [historyData, setHistoryData] = useState([]);
  const [groupedHistory, setGroupedHistory] = useState([]);
  const [displayCount, setDisplayCount] = useState(5);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.evergreen3579.cloud';

  const availableModels = [
    { id: 'Claude-3-Sonnet', label: 'Anthropic : Claude 3 Sonnet' },
    { id: 'Claude-3-Haiku', label: 'Anthropic : Claude 3 Haiku' },
    { id: 'Llama-3', label: 'Meta : Llama 3' }
  ];

  const handleModelToggle = (modelId) => {
    setSelectedModels(prev => 
      prev.includes(modelId)
        ? prev.filter(id => id !== modelId)
        : [...prev, modelId]
    );
  };

  const handleEvaluate = async () => {
    if (selectedModels.length === 0) {
      alert('최소 하나 이상의 모델을 선택해주세요.');
      return;
    }
    if (!prompt.trim()) {
      alert('프롬프트를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    setResults([]);
    setErrorMsg('');

    try {
      const response = await axios.post(`${API_BASE_URL}/mock-bedrock-eval/`, {
        models: selectedModels,
        prompt: prompt
      });
      setResults(response.data);
    } catch (error) {
      console.error('API 호출 에러:', error);
      if (error.response?.status === 429) {
        setErrorMsg('과도한 요청입니다. 약 1분 후 다시 시도해주세요.');
      } else {
        alert('데이터 통신에 실패했습니다. 백엔드 서버 상태를 확인하세요.');
      }
    } finally {
      setIsLoading(false);
      setIsCooldown(true);
      setTimeout(() => {
        setIsCooldown(false);
      }, 10000);
    }
  };

  const fetchHistory = async () => {
    setIsHistoryLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/evaluations/`);
      const rawData = response.data.sort((a, b) => b.id - a.id);
      setHistoryData(rawData);

      const grouped = rawData.reduce((acc, curr) => {
        const key = curr.prompt.trim();
        if (!acc[key]) {
          acc[key] = {
            prompt: curr.prompt,
            created_at: curr.created_at,
            evaluations: []
          };
        }
        acc[key].evaluations.push(curr);
        return acc;
      }, {});

      const groupedArray = Object.values(grouped).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setGroupedHistory(groupedArray);
      setDisplayCount(5);
    } catch (error) {
      console.error('히스토리 로드 에러:', error);
      alert('평가 기록을 불러오는데 실패했습니다.');
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const loadMoreHistory = () => {
    setDisplayCount(prev => prev + 5);
  };

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab]);

  return (
    <div className="app-container">
      <header className="header" style={{ position: 'relative' }}>
        <button 
          onClick={() => navigate('/')}
          style={{ position: 'absolute', left: 0, top: '10px', background: 'transparent', color: '#8b949e', border: '1px solid #30363d', padding: '0.4rem 0.8rem', borderRadius: '6px', cursor: 'pointer' }}
        >
          ← 홈으로
        </button>
        <h1>Multi-LLM Evaluation Console</h1>
        <p>Amazon Bedrock API 기반 대형언어모델 성능 비교 플랫폼</p>
      </header>
      
      {errorMsg && (
        <div style={{ background: '#f85149', color: 'white', padding: '10px 20px', borderRadius: '6px', marginBottom: '1rem', textAlign: 'center', fontWeight: 'bold' }}>
          ⚠️ {errorMsg}
        </div>
      )}

      <div className="tabs" style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '1px solid #30363d', paddingBottom: '1rem' }}>
        <button 
          style={{ padding: '0.6rem 1.2rem', background: activeTab === 'evaluation' ? '#2ea043' : 'transparent', color: activeTab === 'evaluation' ? 'white' : '#c9d1d9', border: activeTab === 'evaluation' ? 'none' : '1px solid #30363d', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
          onClick={() => setActiveTab('evaluation')}
        >
          새 평가 실행
        </button>
        <button 
          style={{ padding: '0.6rem 1.2rem', background: activeTab === 'history' ? '#1f6feb' : 'transparent', color: activeTab === 'history' ? 'white' : '#c9d1d9', border: activeTab === 'history' ? 'none' : '1px solid #30363d', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
          onClick={() => setActiveTab('history')}
        >
          과거 평가 기록
        </button>
      </div>

      <main>
        {activeTab === 'evaluation' && (
          <>
            <div className="input-group">
              <label className="group-label">Target Models (Multiple Selection)</label>
              <div className="checkbox-group">
                {availableModels.map(model => (
                  <label key={model.id} className="checkbox-label">
                    <input 
                      type="checkbox" 
                      checked={selectedModels.includes(model.id)}
                      onChange={() => handleModelToggle(model.id)}
                    />
                    {model.label}
                  </label>
                ))}
              </div>
            </div>

            <div className="input-group">
              <label className="group-label">Prompt Input</label>
              <textarea 
                className="form-control"
                rows="6" 
                maxLength={1000}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="> Enter your test prompt here..."
              />
              <div style={{ textAlign: 'right', fontSize: '0.85rem', color: prompt.length >= 1000 ? '#f85149' : '#8b949e', marginTop: '0.5rem' }}>
                {prompt.length} / 1000
              </div>
            </div>

            <button 
              className="submit-btn"
              onClick={handleEvaluate} 
              disabled={isLoading || isCooldown}
              style={{ opacity: (isLoading || isCooldown) ? 0.5 : 1, cursor: (isLoading || isCooldown) ? 'not-allowed' : 'pointer' }}
            >
              {isLoading ? 'Executing Parallel Evaluation...' : isCooldown ? '잠시 후 재시도 가능 (과금 방지 쿨다운 중)...' : 'Run Evaluation'}
            </button>

            {/* [Phase 3] API 로딩 중 스켈레톤 UI 렌더링 (선택한 모델 개수만큼 렌더링) */}
            {isLoading ? (
              <div className="results-grid" style={{ marginTop: '2rem' }}>
                {selectedModels.map((modelId, index) => (
                  <div key={index} className="result-card skeleton-box" style={{ background: '#0d1117', border: '1px solid #30363d', padding: '1.5rem', borderRadius: '8px' }}>
                    <div className="skeleton-pulse" style={{ height: '24px', width: '50%', background: '#21262d', marginBottom: '1.5rem', borderRadius: '4px' }}></div>
                    <div className="skeleton-pulse" style={{ height: '16px', width: '80%', background: '#21262d', marginBottom: '0.8rem', borderRadius: '4px' }}></div>
                    <div className="skeleton-pulse" style={{ height: '16px', width: '60%', background: '#21262d', marginBottom: '2rem', borderRadius: '4px' }}></div>
                    <div className="skeleton-pulse" style={{ height: '100px', width: '100%', background: '#21262d', borderRadius: '4px' }}></div>
                  </div>
                ))}
              </div>
            ) : results.length > 0 ? (
              <div className="results-grid" style={{ marginTop: '2rem' }}>
                {results.map((res, index) => (
                  <div key={index} className="result-card">
                    <h3>{res.model_name}</h3>
                    <div className="result-item"><span className="result-label">Task ID:</span> <strong>#{res.id}</strong></div>
                    <div className="result-item"><span className="result-label">Score:</span> <span style={{ color: '#2ea043', fontWeight: 'bold' }}>{res.evaluation_score} / 100</span></div>
                    <div className="result-item"><span className="result-label">Latency:</span> <span style={{ color: '#d2a8ff' }}>{res.processing_time_ms} ms</span></div>
                    <div className="result-item"><span className="result-label">Tokens:</span> <span style={{ color: '#79c0ff' }}>{res.token_count}</span></div>
                    <div className="result-item" style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
                      <span className="result-label" style={{ marginBottom: '0.5rem' }}>Response:</span> 
                      <div className="result-response">{res.response}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </>
        )}

        {activeTab === 'history' && (
          <div className="history-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0 }}>Evaluation History (묶음 보기)</h2>
              <button 
                onClick={fetchHistory} 
                style={{ padding: '0.4rem 0.8rem', background: '#30363d', color: 'white', border: '1px solid #8b949e', borderRadius: '6px', cursor: 'pointer' }}
                disabled={isHistoryLoading}
              >
                {isHistoryLoading ? 'Loading...' : '🔄 데이터 갱신'}
              </button>
            </div>
            
            {groupedHistory.length === 0 && !isHistoryLoading ? (
              <div style={{ padding: '2rem', textAlign: 'center', background: '#161b22', borderRadius: '8px', border: '1px solid #30363d' }}>
                저장된 평가 기록이 없습니다.
              </div>
            ) : (
              <div className="grouped-history-container" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                {groupedHistory.slice(0, displayCount).map((group, groupIndex) => (
                  <div key={groupIndex} className="history-group-card" style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '1.5rem' }}>
                    <div className="prompt-header" style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid #21262d' }}>
                      <span style={{ color: '#8b949e', fontSize: '0.9rem' }}>💡 동일 질문 평가 묶음</span>
                      <div style={{ marginTop: '0.5rem', fontSize: '1.1rem', color: '#c9d1d9', fontWeight: 'bold', wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                        "{group.prompt}"
                      </div>
                    </div>

                    <div className="evaluations-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                      {group.evaluations.map((evalData, evalIndex) => (
                        <div key={evalIndex} className="eval-card" style={{ background: '#161b22', padding: '1rem', borderRadius: '6px', borderLeft: '4px solid #1f6feb' }}>
                          <h4 style={{ margin: '0 0 0.8rem 0', color: '#58a6ff' }}>{evalData.model_name}</h4>
                          <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}><span style={{ color: '#8b949e' }}>Score: </span> <span style={{ color: '#2ea043', fontWeight: 'bold' }}>{evalData.evaluation_score} / 100</span></div>
                          <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}><span style={{ color: '#8b949e' }}>Latency: </span> <span style={{ color: '#d2a8ff' }}>{evalData.processing_time_ms} ms</span></div>
                          <div style={{ fontSize: '0.9rem', color: '#c9d1d9', background: '#010409', padding: '0.8rem', borderRadius: '4px', marginTop: '0.8rem', maxHeight: '150px', overflowY: 'auto' }}>
                            {evalData.response}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {displayCount < groupedHistory.length && (
                  <button 
                    onClick={loadMoreHistory}
                    style={{ padding: '0.8rem', background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', width: '100%', marginTop: '1rem' }}
                  >
                    더 보기 ({displayCount} / {groupedHistory.length}) ▼
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

// [Phase 3 신규] 라우팅을 총괄하는 App 컨테이너
function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/app" element={<Dashboard />} />
    </Routes>
  );
}

export default App;