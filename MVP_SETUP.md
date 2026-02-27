# MVP Setup Guide

## Quick Start

### Backend Setup (Python/FastAPI)

1. Navigate to backend:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
uvicorn app.main:app --reload
```

Backend will run on: http://localhost:8000

### Frontend Setup (Next.js)

1. Navigate to frontend:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run development server:
```bash
npm run dev
```

Frontend will run on: http://localhost:3000

## MVP Features

### Working Endpoints:

1. **Content Generation**
   - POST `/api/content/generate`
   - Body: `{ "prompt": "string", "language": "hindi", "tone": "casual" }`

2. **Translation**
   - POST `/api/translation/translate`
   - Body: `{ "text": "string", "source_language": "hindi", "target_language": "tamil", "tone": "neutral" }`

### Frontend Features:
- Simple content generation interface
- Language selector (Hindi, Tamil, Telugu, Bengali)
- Text input for prompts
- Display generated content

## Next Steps

To add real AI functionality:
1. Integrate OpenAI API or Hugging Face models
2. Add IndicTrans for proper translation
3. Implement database for storing content
4. Add user authentication
5. Implement social media scheduling
