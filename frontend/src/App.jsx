import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState(['Claude-3-Sonnet']);
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

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
      // 변경된 백엔드 스키마에 맞게 배열(models)로 전송
      const response = await axios.post('http://127.0.0.1:8000/mock-bedrock-eval/', {
        models: selectedModels,
        prompt: prompt
      });
      // 백엔드에서 배열 형태로 반환된 결과를 저장
      setResults(response.data);
    } catch (error) {
      console.error('API 호출 에러:', error);
      alert('데이터 통신에 실패했습니다. 백엔드 서버 상태를 확인하세요.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Multi-LLM Evaluation Console</h1>
        <p>Amazon Bedrock API 기반 대형언어모델 성능 비교 플랫폼</p>
      </header>
      
      <main>
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

        {/* 결과값이 있을 경우 그리드 형태로 렌더링 */}
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
      </main>
    </div>
  );
}

export default App;