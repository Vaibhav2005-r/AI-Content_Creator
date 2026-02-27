import { useState } from 'react';

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [language, setLanguage] = useState('hindi');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);

  const generateContent = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/content/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, language, tone: 'casual' })
      });
      const data = await response.json();
      setContent(data.content);
    } catch (error) {
      console.error('Error:', error);
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Bharat Content AI</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <label>Language:</label>
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="hindi">Hindi</option>
          <option value="tamil">Tamil</option>
          <option value="telugu">Telugu</option>
          <option value="bengali">Bengali</option>
        </select>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <textarea
          placeholder="Enter your prompt..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          style={{ width: '100%', height: '100px', padding: '10px' }}
        />
      </div>

      <button onClick={generateContent} disabled={loading}>
        {loading ? 'Generating...' : 'Generate Content'}
      </button>

      {content && (
        <div style={{ marginTop: '20px', padding: '15px', background: '#f5f5f5' }}>
          <h3>Generated Content:</h3>
          <p>{content}</p>
        </div>
      )}
    </div>
  );
}