import os
import time
import google.generativeai as genai
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class GeminiContentGenerator:
    """Content generation using Google Gemini API"""
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
    def generate_content(
        self,
        prompt: str,
        language: str = "hindi",
        tone: str = "casual",
        content_type: str = "social_post",
        model: str = "gemini-pro",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate content using Google Gemini
        
        Args:
            prompt: User's content request
            language: Target language
            tone: Content tone
            content_type: Type of content
            model: gemini-pro
            max_tokens: Maximum tokens
            temperature: Creativity (0-1)
        
        Returns:
            Dict with generated content and metadata
        """
        start_time = time.time()
        
        # Build enhanced prompt
        enhanced_prompt = self._build_prompt(prompt, language, tone, content_type)
        
        try:
            # Generate content
            response = self.model.generate_content(
                enhanced_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            # Extract content
            content = response.text
            
            # Calculate metrics
            generation_time = int((time.time() - start_time) * 1000)
            
            # Token counts (approximate)
            input_tokens = len(enhanced_prompt.split())
            output_tokens = len(content.split())
            
            return {
                "content": content,
                "model_used": "gemini-2.5-flash",
                "model_name": "Google Gemini 2.5 Flash",
                "generation_time_ms": generation_time,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "stop_reason": "STOP",
            }
            
        except Exception as e:
            raise Exception(f"Gemini API Error: {str(e)}")
    
    def _build_prompt(
        self,
        prompt: str,
        language: str,
        tone: str,
        content_type: str
    ) -> str:
        """Build enhanced prompt with context"""
        
        language_map = {
            "hindi": "Hindi (हिंदी) using Devanagari script",
            "tamil": "Tamil (தமிழ்) using Tamil script",
            "telugu": "Telugu (తెలుగు) using Telugu script",
            "bengali": "Bengali (বাংলা) using Bengali script",
            "marathi": "Marathi (मराठी) using Devanagari script",
            "gujarati": "Gujarati (ગુજરાતી) using Gujarati script",
            "kannada": "Kannada (ಕನ್ನಡ) using Kannada script",
            "malayalam": "Malayalam (മലയാളം) using Malayalam script",
            "punjabi": "Punjabi (ਪੰਜਾਬੀ) using Gurmukhi script",
            "english": "English",
        }
        
        tone_descriptions = {
            "casual": "friendly, conversational, and relatable",
            "formal": "professional, polished, and respectful",
            "professional": "business-appropriate and authoritative",
            "friendly": "warm, approachable, and engaging",
            "humorous": "witty, entertaining, and light-hearted",
            "inspirational": "motivating, uplifting, and empowering",
            "educational": "informative, clear, and instructive",
        }
        
        content_instructions = {
            "social_post": "Create an engaging social media post with appropriate hashtags",
            "blog": "Write a comprehensive blog article with introduction, body, and conclusion",
            "article": "Compose a well-structured article with clear sections",
            "caption": "Write a concise, catchy caption",
            "script": "Create a video or audio script with natural flow",
            "email": "Draft a professional email with proper greeting and closing",
            "ad_copy": "Write persuasive advertising copy that drives action",
        }
        
        target_lang = language_map.get(language, language)
        tone_desc = tone_descriptions.get(tone, tone)
        content_inst = content_instructions.get(content_type, "Create engaging content")
        
        enhanced_prompt = f"""You are an expert content creator for Indian audiences, specializing in multilingual content.

Task: {content_inst}
Language: {target_lang}
Tone: {tone_desc}

User Request: {prompt}

Instructions:
1. Write ENTIRELY in {target_lang} (use native script)
2. Maintain a {tone_desc} tone throughout
3. Make it culturally relevant for Indian audiences
4. Include appropriate emojis if suitable for the platform
5. For social posts, suggest 3-5 relevant hashtags at the end
6. Keep it engaging and authentic

Generate the content now:"""
        
        return enhanced_prompt
