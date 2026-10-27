import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

function Dashboard() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState([
    'Gemini-2.5-Flash',
    'Groq-Llama-3.1-8B',
    'Groq-Llama-3.3-70B'
  ]);
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const [isCooldown, setIsCooldown] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [activeTab, setActiveTab] = useState('evaluation');
  const [groupedHistory, setGroupedHistory] = useState([]);
  const [displayCount, setDisplayCount] = useState(5);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.evergreen3579.cloud';

  // 요청하신 3개 모델 순서 및 이름 반영
  const availableModels = [
    { id: 'Gemini-2.5-Flash', label: 'Google - Gemini 2.5 Flash' },
    { id: 'Groq-Llama-3.1-8B', label: 'Groq - Llama 3.1 8B Instant' },
    { id: 'Groq-Llama-3.3-70B', label: 'Groq - Llama 3.3 70B Versatile' }
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
      <header className="header" style={{ position: 'relative', paddingTop: '0.5rem' }}>
        <button 
          onClick={() => navigate('/')}
          style={{ position: 'absolute', left: 0, top: '10px', background: '#161b22', color: '#c9d1d9', border: '1px solid #30363d', padding: '0.45rem 0.9rem', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          ← 홈으로
        </button>
        <h1 style={{ fontSize: '2rem', margin: '0 0 0.5rem 0', lineHeight: '1.3' }}>Multi-LLM Evaluation Console</h1>
        <p style={{ color: '#8b949e', margin: 0 }}>Google Gemini & Groq LPU 기반 다중 모델 실시간 응답 및 성능 비교</p>
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
                rows="5" 
                maxLength={1000}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="> 비교 평가할 프롬프트를 입력하세요 (예: 클라우드 컴퓨팅의 장단점을 3가지로 요약해줘)..."
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
              {isLoading ? 'Executing Parallel Evaluation...' : isCooldown ? '잠시 후 재시도 가능 (과금 방지 쿨다운 10초)...' : 'Run Evaluation'}
            </button>

            {isLoading ? (
              <div className="results-grid" style={{ marginTop: '2rem' }}>
                {selectedModels.map((modelId, index) => (
                  <div key={index} className="result-card skeleton-box" style={{ background: '#0d1117', border: '1px solid #30363d', padding: '1.5rem', borderRadius: '8px' }}>
                    <div className="skeleton-pulse" style={{ height: '24px', width: '50%', background: '#21262d', marginBottom: '1.2rem', borderRadius: '4px' }}></div>
                    <div className="skeleton-pulse" style={{ height: '16px', width: '70%', background: '#21262d', marginBottom: '1.5rem', borderRadius: '4px' }}></div>
                    <div className="skeleton-pulse" style={{ height: '180px', width: '100%', background: '#21262d', borderRadius: '4px' }}></div>
                  </div>
                ))}
              </div>
            ) : results.length > 0 ? (
              <div className="results-grid" style={{ marginTop: '2rem' }}>
                {results.map((res, index) => (
                  <div key={index} className="result-card" style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #21262d', paddingBottom: '0.8rem', marginBottom: '1rem' }}>
                      <h3 style={{ margin: 0, color: '#58a6ff', fontSize: '1.15rem' }}>{res.model_name}</h3>
                      <span style={{ fontSize: '0.8rem', color: '#8b949e', background: '#161b22', padding: '0.2rem 0.6rem', borderRadius: '4px', border: '1px solid #30363d' }}>
                        Task #{res.id}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '0.8rem', marginBottom: '1rem' }}>
                      <div style={{ flex: 1, background: '#161b22', padding: '0.6rem', borderRadius: '6px', border: '1px solid #21262d', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.75rem', color: '#8b949e', marginBottom: '0.2rem' }}>Latency</div>
                        <div style={{ color: '#d2a8ff', fontWeight: 'bold', fontSize: '1rem' }}>{res.processing_time_ms} ms</div>
                      </div>
                      <div style={{ flex: 1, background: '#161b22', padding: '0.6rem', borderRadius: '6px', border: '1px solid #21262d', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.75rem', color: '#8b949e', marginBottom: '0.2rem' }}>Token Usage</div>
                        <div style={{ color: '#79c0ff', fontWeight: 'bold', fontSize: '1rem' }}>{res.token_count} tokens</div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
                      <span style={{ fontSize: '0.85rem', color: '#8b949e', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                        Model Output:
                      </span>
                      <div style={{ background: '#010409', color: '#e6edf3', padding: '1rem', borderRadius: '6px', border: '1px solid #30363d', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: '1.65', fontSize: '0.95rem', flexGrow: 1, maxHeight: '420px', overflowY: 'auto' }}>
                        {res.response}
                      </div>
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
              <h2 style={{ margin: 0 }}>Evaluation History (프롬프트별 비교 묶음)</h2>
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
                  <div key={groupIndex} className="history-group-card" style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '1.5rem', textAlign: 'left' }}>
                    <div className="prompt-header" style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid #21262d' }}>
                      <span style={{ color: '#8b949e', fontSize: '0.85rem' }}>💡 입력 프롬프트</span>
                      <div style={{ marginTop: '0.5rem', fontSize: '1.1rem', color: '#f0f6fc', fontWeight: 'bold', wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                        "{group.prompt}"
                      </div>
                    </div>

                    <div className="evaluations-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                      {group.evaluations.map((evalData, evalIndex) => (
                        <div key={evalIndex} className="eval-card" style={{ background: '#161b22', padding: '1rem', borderRadius: '6px', borderLeft: '4px solid #1f6feb', display: 'flex', flexDirection: 'column' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                            <h4 style={{ margin: 0, color: '#58a6ff' }}>{evalData.model_name}</h4>
                            <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>#{evalData.id}</span>
                          </div>
                          
                          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', marginBottom: '0.8rem', background: '#0d1117', padding: '0.5rem 0.8rem', borderRadius: '4px' }}>
                            <div><span style={{ color: '#8b949e' }}>Latency: </span> <span style={{ color: '#d2a8ff', fontWeight: 'bold' }}>{evalData.processing_time_ms} ms</span></div>
                            <div><span style={{ color: '#8b949e' }}>Tokens: </span> <span style={{ color: '#79c0ff', fontWeight: 'bold' }}>{evalData.token_count}</span></div>
                          </div>

                          <div style={{ fontSize: '0.9rem', color: '#e6edf3', background: '#010409', padding: '0.8rem', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: '1.6', maxHeight: '220px', overflowY: 'auto', flexGrow: 1 }}>
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

export default Dashboard;