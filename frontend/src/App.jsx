import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState(['Claude-3-Sonnet']);
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // [신규 추가] 탭 상태 및 히스토리 데이터 상태 관리
  const [activeTab, setActiveTab] = useState('evaluation'); // 'evaluation' 또는 'history'
  const [historyData, setHistoryData] = useState([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  // 평가 가능한 모델 리스트
  const availableModels = [
    { id: 'Claude-3-Sonnet', label: 'Anthropic : Claude 3 Sonnet' },
    { id: 'Claude-3-Haiku', label: 'Anthropic : Claude 3 Haiku' },
    { id: 'Llama-3', label: 'Meta : Llama 3' }
  ];

  // 체크박스 토글 핸들러
  const handleModelToggle = (modelId) => {
    setSelectedModels(prev => 
      prev.includes(modelId)
        ? prev.filter(id => id !== modelId) // 이미 있으면 제거
        : [...prev, modelId] // 없으면 추가
    );
  };

  // 평가 요청 실행
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
    setResults([]); // 기존 결과 초기화

    try {
      const response = await axios.post('http://54.227.82.12:8000/mock-bedrock-eval/', {
        models: selectedModels,
        prompt: prompt
      });
      setResults(response.data);
    } catch (error) {
      console.error('API 호출 에러:', error);
      alert('데이터 통신에 실패했습니다. 백엔드 서버 상태를 확인하세요.');
    } finally {
      setIsLoading(false);
    }
  };

  // [신규 추가] 백엔드에서 과거 평가 기록 호출
  const fetchHistory = async () => {
    setIsHistoryLoading(true);
    try {
      const response = await axios.get('http://54.227.82.12:8000/evaluations/');
      // 가장 최근 데이터가 상단에 오도록 ID 기준 내림차순 정렬
      const sortedData = response.data.sort((a, b) => b.id - a.id);
      setHistoryData(sortedData);
    } catch (error) {
      console.error('히스토리 로드 에러:', error);
      alert('평가 기록을 불러오는데 실패했습니다.');
    } finally {
      setIsHistoryLoading(false);
    }
  };

  // [신규 추가] '과거 평가 기록' 탭으로 전환될 때만 데이터 로드
  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab]);

  return (
    <div className="app-container">
      <header className="header">
        <h1>Multi-LLM Evaluation Console</h1>
        <p>Amazon Bedrock API 기반 대형언어모델 성능 비교 플랫폼</p>
      </header>
      
      {/* [신규 추가] 탭 네비게이션 바 */}
      <div className="tabs" style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '1px solid #30363d', paddingBottom: '1rem' }}>
        <button 
          style={{ 
            padding: '0.6rem 1.2rem', 
            background: activeTab === 'evaluation' ? '#2ea043' : 'transparent', 
            color: activeTab === 'evaluation' ? 'white' : '#c9d1d9', 
            border: activeTab === 'evaluation' ? 'none' : '1px solid #30363d', 
            borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' 
          }}
          onClick={() => setActiveTab('evaluation')}
        >
          새 평가 실행
        </button>
        <button 
          style={{ 
            padding: '0.6rem 1.2rem', 
            background: activeTab === 'history' ? '#1f6feb' : 'transparent', 
            color: activeTab === 'history' ? 'white' : '#c9d1d9', 
            border: activeTab === 'history' ? 'none' : '1px solid #30363d', 
            borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' 
          }}
          onClick={() => setActiveTab('history')}
        >
          과거 평가 기록
        </button>
      </div>

      <main>
        {/* 기존 평가 실행 렌더링 영역 */}
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
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="> Enter your test prompt here..."
              />
            </div>

            <button 
              className="submit-btn"
              onClick={handleEvaluate} 
              disabled={isLoading}
            >
              {isLoading ? 'Executing Parallel Evaluation...' : 'Run Evaluation'}
            </button>

            {results.length > 0 && (
              <div className="results-grid">
                {results.map((res, index) => (
                  <div key={index} className="result-card">
                    <h3>{res.model_name}</h3>
                    
                    <div className="result-item">
                      <span className="result-label">Task ID:</span> 
                      <strong>#{res.id}</strong>
                    </div>
                    
                    <div className="result-item">
                      <span className="result-label">Score:</span> 
                      <span style={{ color: '#2ea043', fontWeight: 'bold' }}>{res.evaluation_score} / 100</span>
                    </div>

                    <div className="result-item">
                      <span className="result-label">Latency:</span> 
                      <span style={{ color: '#d2a8ff' }}>{res.processing_time_ms} ms</span>
                    </div>

                    <div className="result-item">
                      <span className="result-label">Tokens:</span> 
                      <span style={{ color: '#79c0ff' }}>{res.token_count}</span>
                    </div>

                    <div className="result-item" style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
                      <span className="result-label" style={{ marginBottom: '0.5rem' }}>Response:</span> 
                      <div className="result-response">
                        {res.response}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* [신규 추가] 히스토리 내역 렌더링 영역 */}
        {activeTab === 'history' && (
          <div className="history-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0 }}>Evaluation History</h2>
              <button 
                onClick={fetchHistory} 
                style={{ padding: '0.4rem 0.8rem', background: '#30363d', color: 'white', border: '1px solid #8b949e', borderRadius: '6px', cursor: 'pointer' }}
                disabled={isHistoryLoading}
              >
                {isHistoryLoading ? 'Loading...' : '🔄 새로고침'}
              </button>
            </div>
            
            {historyData.length === 0 && !isHistoryLoading ? (
              <div style={{ padding: '2rem', textAlign: 'center', background: '#161b22', borderRadius: '8px', border: '1px solid #30363d' }}>
                저장된 평가 기록이 없습니다.
              </div>
            ) : (
              <div className="results-grid">
                {historyData.map((res, index) => (
                  <div key={index} className="result-card" style={{ borderLeft: '4px solid #1f6feb' }}>
                    <h3>{res.model_name} <span style={{ fontSize: '0.8rem', color: '#8b949e', fontWeight: 'normal', marginLeft: '0.5rem' }}>#{res.id}</span></h3>
                    
                    <div className="result-item" style={{ marginBottom: '0.8rem', alignItems: 'flex-start' }}>
                      <span className="result-label" style={{ minWidth: '60px', marginTop: '0.2rem' }}>Prompt:</span>
                      <div style={{ background: '#0d1117', padding: '0.5rem', borderRadius: '4px', fontSize: '0.9rem', color: '#c9d1d9', flexGrow: 1, wordBreak: 'break-all' }}>
                        {res.prompt.length > 60 ? res.prompt.substring(0, 60) + '...' : res.prompt}
                      </div>
                    </div>

                    <div className="result-item">
                      <span className="result-label">Score:</span> 
                      <span style={{ color: '#2ea043', fontWeight: 'bold' }}>{res.evaluation_score} / 100</span>
                    </div>

                    <div className="result-item">
                      <span className="result-label">Latency:</span> 
                      <span style={{ color: '#d2a8ff' }}>{res.processing_time_ms} ms</span>
                    </div>

                    <div className="result-item" style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
                      <span className="result-label" style={{ marginBottom: '0.5rem' }}>Response:</span> 
                      <div className="result-response" style={{ maxHeight: '120px', overflowY: 'auto' }}>
                        {res.response}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;