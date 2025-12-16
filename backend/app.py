from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS
import io
import base64
import os
import json
import uuid
import tempfile
import requests
from dotenv import load_dotenv
from openai import OpenAI
from fpdf import FPDF
import pdfplumber
from youtubesearchpython import VideosSearch
import yt_dlp
import whisper
from typing import List
import shutil
import subprocess
from gtts import gTTS
import random
import re
from collections import Counter, defaultdict
import time
import random
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import feedparser
from models import db, User, QuizScore, ChatHistory, ChatSession, Document, FocusAreaDismissal, LearningPath, LearningPathStep, FeynmanScore, VideoSummary, CommunityTopic, CommunityComment

# --- Simple in-memory analytics store (for backward compatibility) ---
ANALYTICS = {
    'overall': {
        'quizzesSubmitted': 0,
        'questionsAnswered': 0,
        'correctAnswers': 0
    },
    'users': {}
}

load_dotenv()

# Initialize NVIDIA API configuration
# Prefer NVIDIA_* env vars, but keep compatibility with OPENAI_* if set
NVIDIA_API_KEY = (
    os.getenv('NVIDIA_API_KEY')
    or os.getenv('OPENAI_API_KEY')
)
NVIDIA_API_BASE = os.getenv('NVIDIA_API_BASE', 'https://integrate.api.nvidia.com/v1')
NVIDIA_MODEL = os.getenv('NVIDIA_MODEL', 'meta/llama-3.1-8b-instruct')
SMTP_HOST = os.getenv('SMTP_HOST')

client = OpenAI(
    base_url=NVIDIA_API_BASE,
    api_key=NVIDIA_API_KEY
)
SMTP_PORT = int(os.getenv('SMTP_PORT', '0') or 0)
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
SMTP_FROM = os.getenv('SMTP_FROM') or SMTP_USER

app = Flask(__name__)
CORS(app)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/smart_learning')
if not DATABASE_URL.startswith('postgresql://'):
    # Handle DATABASE_URL format from services like Heroku
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return jsonify({'message': 'Smart Learning Assistant Backend is running.'})

@app.route('/api/test', methods=['POST'])
def test_endpoint():
    print("DEBUG: test endpoint hit")
    return jsonify({'status': 'ok'})

@app.route('/api/news', methods=['GET'])
def get_news():
    try:
        # Use a reputable RSS feed (e.g., BBC World News)
        feed_url = 'http://feeds.bbci.co.uk/news/world/rss.xml'
        feed = feedparser.parse(feed_url)
        
        articles = []
        # Get random 6 headlines from the available entries
        entries = feed.entries
        if entries:
            # Shuffle to show different news on refresh
            random.shuffle(entries)
            selected_entries = entries[:6]
        else:
            selected_entries = []

        for entry in selected_entries:
            articles.append({
                'title': entry.title,
                'link': entry.link,
                'summary': entry.summary,
                'published': entry.published if hasattr(entry, 'published') else ''
            })
            
        return jsonify({'articles': articles})
    except Exception as e:
        print(f"Error fetching news: {e}")
        return jsonify({'error': 'Failed to fetch news'}), 500

def _generate_verification_code() -> str:
    return f"{random.randint(100000, 999999)}"

def _send_verification_email(recipient: str, code: str) -> bool:
    if not SMTP_HOST or not SMTP_PORT or not SMTP_USER or not SMTP_PASS:
        print("SMTP is not fully configured; skipping email send.")
        return False

    msg = EmailMessage()
    msg['Subject'] = 'Your Smart Learning Assistant verification code'
    msg['From'] = SMTP_FROM or SMTP_USER
    msg['To'] = recipient
    msg.set_content(
        f"Hi,\n\nUse the code {code} to verify your Smart Learning Assistant account. "
        "This code expires in 15 minutes.\n\nIf you did not request this, please ignore this email."
    )

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        return True
    except Exception as exc:
        print(f"Failed to send verification email: {exc}")
        return False

def _queue_verification(email: str) -> bool:
    code = _generate_verification_code()
    user = User.query.filter_by(email=email).first()
    if user:
        user.verification_code = code
        user.verification_expires = datetime.utcnow() + timedelta(minutes=15)
        user.verified = False
        db.session.commit()
    sent = _send_verification_email(email, code)
    # ALWAYS print the code for debugging purposes
    print(f"DEBUG: Verification code for {email}: {code}")
    return sent

def _issue_token(email: str) -> str:
    """Generate a token for authentication (stored in session or can be JWT in future)"""
    # For now, return a simple token. In production, use JWT or store in Redis
    token = uuid.uuid4().hex
    # Note: In production, you might want to store tokens in Redis or use JWT
    return token

def _auth_user_payload(email: str) -> dict:
    user = User.query.filter_by(email=email).first()
    if not user:
        return {}
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'verified': user.verified
    }

def _get_user_from_token(token: str) -> User:
    """Extract user from token. For now, we'll use a simple approach."""
    # In production, decode JWT or lookup in Redis
    # For now, we'll need to pass user_id or email in the request
    # This is a simplified version - you may want to use JWT tokens
    return None

def _extract_token_from_header() -> str:
    header = request.headers.get('Authorization', '')
    if not header:
        return ''
    if header.lower().startswith('bearer '):
        return header.split(' ', 1)[1].strip()
    return header.strip()

def _get_current_user():
    """Get current user from token or user_id in request"""
    # Try to get user_id from request headers (frontend can send it)
    user_id = request.headers.get('X-User-Id')
    if user_id:
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            pass
    
    # Try to get user_id from JSON body if it's a POST request
    if request.method == 'POST' and request.is_json:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        if user_id:
            try:
                return User.query.get(int(user_id))
            except (ValueError, TypeError):
                pass
    
    # Fallback: try to get from token (simplified - in production use JWT)
    # For now, we'll need user_id in the request
    # In production, decode JWT token to get user_id
    return None

@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required.'}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'Email already registered. Please log in instead.'}), 409

    # Create new user
    user = User(
        email=email,
        name=name,
        verified=False
    )
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        email_sent = _queue_verification(email)
        return jsonify({
            'message': 'Account created. We sent a verification code to your email.',
            'emailSent': email_sent
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create account: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    if not user.verified:
        return jsonify({'error': 'Email not verified. Please check your inbox for the code.'}), 403

    token = _issue_token(email)
    return jsonify({
        'message': 'Login successful.',
        'token': token,
        'user': _auth_user_payload(email)
    })

@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({'user': _auth_user_payload(user.email)})

@app.route('/api/auth/verify-code', methods=['POST'])
def auth_verify_code():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Account not found.'}), 404

    if user.verified:
        token = _issue_token(email)
        return jsonify({
            'message': 'Account already verified.',
            'token': token,
            'user': _auth_user_payload(email)
        })

    if not user.verification_code or not user.verification_expires:
        return jsonify({'error': 'Verification code expired. Please request a new one.'}), 410

    if datetime.utcnow() > user.verification_expires:
        return jsonify({'error': 'Verification code expired. Please request a new one.'}), 410

    if code != str(user.verification_code):
        return jsonify({'error': 'Invalid verification code.'}), 400

    user.verified = True
    user.verification_code = None
    user.verification_expires = None
    
    try:
        db.session.commit()
        token = _issue_token(email)
        return jsonify({
            'message': 'Email verified successfully.',
            'token': token,
            'user': _auth_user_payload(email)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to verify: {str(e)}'}), 500

@app.route('/api/auth/resend-code', methods=['POST'])
def auth_resend_code():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Account not found.'}), 404

    if user.verified:
        return jsonify({'message': 'Account already verified.'})

    email_sent = _queue_verification(email)
    return jsonify({
        'message': 'A new verification code has been sent.',
        'emailSent': email_sent
    })

def _send_reset_email(recipient: str, code: str) -> bool:
    if not SMTP_HOST or not SMTP_PORT or not SMTP_USER or not SMTP_PASS:
        print("SMTP is not fully configured; skipping email send.")
        return False

    msg = EmailMessage()
    msg['Subject'] = 'Reset your Smart Learning Assistant password'
    msg['From'] = SMTP_FROM or SMTP_USER
    msg['To'] = recipient
    msg.set_content(
        f"Hi,\n\nUse the code {code} to reset your password. "
        "This code expires in 15 minutes.\n\nIf you did not request this, please ignore this email."
    )

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        return True
    except Exception as exc:
        print(f"Failed to send reset email: {exc}")
        return False

def _queue_reset_code(email: str) -> bool:
    code = _generate_verification_code()
    user = User.query.filter_by(email=email).first()
    if user:
        user.verification_code = code
        user.verification_expires = datetime.utcnow() + timedelta(minutes=15)
        # We do NOT un-verify the user here, just set the code
        db.session.commit()
    
    sent = _send_reset_email(email, code)
    if not sent:
        print(f"Reset code for {email}: {code}")
    return sent

@app.route('/api/auth/forgot-password', methods=['POST'])
def auth_forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        # Return success even if user not found to prevent enumeration
        # But for this dev/demo app, maybe explicit error is better? 
        # Let's stick to standard practice: return success but don't send email.
        # Actually, for debugging, the user might prefer to know.
        # Given the user's request "it should ask for email verification", let's be helpful.
        return jsonify({'error': 'Account not found.'}), 404

    email_sent = _queue_reset_code(email)
    return jsonify({
        'message': 'Password reset code sent to your email.',
        'emailSent': email_sent
    })

@app.route('/api/auth/reset-password', methods=['POST'])
def auth_reset_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()
    new_password = data.get('newPassword') or ''

    if not new_password:
        return jsonify({'error': 'New password is required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Account not found.'}), 404

    if not user.verification_code or not user.verification_expires:
        return jsonify({'error': 'Invalid or expired reset code.'}), 400

    if datetime.utcnow() > user.verification_expires:
        return jsonify({'error': 'Reset code expired. Please request a new one.'}), 410

    if code != str(user.verification_code):
        return jsonify({'error': 'Invalid reset code.'}), 400

    # Reset password
    user.set_password(new_password)
    user.verification_code = None
    user.verification_expires = None
    # If they successfully reset password via email code, they are effectively verified
    user.verified = True 
    
    try:
        db.session.commit()
        return jsonify({'message': 'Password reset successfully. You can now login.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to reset password: {str(e)}'}), 500

# --- Robust PDF text extraction helpers ---
def _looks_mangled(text: str) -> bool:
    """Heuristic to detect poor PDF extraction: no spaces, many cid artifacts, long alnum runs."""
    if not text:
        return True
    no_space_ratio = (len(text.replace(' ', '')) / max(1, len(text)))
    has_cid = '(cid:' in text
    long_run = any(len(tok) > 40 for tok in text.split())
    return no_space_ratio > 0.97 or has_cid or long_run

def _reconstruct_text_from_words(words: List[dict]) -> str:
    """Rebuild lines from pdfplumber extract_words output, inserting spaces sensibly."""
    if not words:
        return ''
    # Group words by y (line) using a tolerance
    words_sorted = sorted(words, key=lambda w: (round(w.get('top', 0) / 2), w.get('x0', 0)))
    lines = []
    current_top = None
    current_line: List[str] = []
    last_x1 = None
    for w in words_sorted:
        top = round(w.get('top', 0) / 2)
        x0 = w.get('x0', 0)
        x1 = w.get('x1', 0)
        text = w.get('text', '')
        if current_top is None:
            current_top = top
        if top != current_top:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = []
            current_top = top
            last_x1 = None
        # Insert space if there is a notable gap
        if last_x1 is not None and (x0 - last_x1) > 3:
            current_line.append(text)
        else:
            current_line.append(text)
        last_x1 = x1
    if current_line:
        lines.append(' '.join(current_line))
    rebuilt = '\n'.join(line.strip() for line in lines if line.strip())
    return rebuilt

def extract_text_from_pdf_stream(file_stream) -> str:
    """Attempt to extract high-quality text from a PDF stream using multiple strategies."""
    collected: List[str] = []
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages[:10]:
            txt = page.extract_text(x_tolerance=2, y_tolerance=3) or ''
            if not txt or _looks_mangled(txt):
                words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
                txt = _reconstruct_text_from_words(words)
            if txt and len(txt.strip()) > 30:
                collected.append(txt.strip())
    import re
    source_text = '\n'.join(collected)
    # Normalize whitespace and remove obvious artifacts like (cid:xxx)
    source_text = re.sub(r'\(cid:\d+\)', ' ', source_text)
    source_text = re.sub(r'\s+', ' ', source_text)
    return source_text.strip()

# ---------------- Video Summarization Helpers -----------------
def _chunk_text_by_chars(text: str, max_chunk_chars: int = 3500) -> List[str]:
    if not text:
        return []
    text = str(text)
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chunk_chars, len(text))
        # try to cut at sentence boundary if possible
        period = text.rfind('.', start, end)
        if period != -1 and period > start + 100:
            end = period + 1
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]

def _summarize_text_with_llm(source_text: str, max_words: int = 250) -> dict:
    """Summarize long text via chunked LLM calls, then meta-summarize."""
    import math
def _summarize_text_with_llm(text, max_words=250):
    try:
        # Check if max_words is "balanced" or similar string
        if isinstance(max_words, str) and max_words.lower() == 'balanced':
            limit_instruction = "Provide a comprehensive and balanced summary that covers all key points of the video, regardless of length. Do not be too brief, but avoid unnecessary fluff."
        else:
            try:
                limit = int(max_words)
            except:
                limit = 250
            limit_instruction = f"Keep the summary under approximately {limit} words."

        prompt = f"""
You are an expert video summarizer.
Your task is to create a clear, structured summary of the following video transcript.

TRANSCRIPT:
{text[:15000]}... (truncated if too long)

INSTRUCTIONS:
1. Capture the main topic and purpose of the video.
2. Bullet point the key takeaways and important details.
3. {limit_instruction}
4. Format with clear headings and bullet points using Markdown.
"""
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes videos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return {'summary': response.choices[0].message.content}
    except Exception as e:
        print(f"LLM Summarization failed: {e}")
        return {'summary': "Failed to generate summary.", 'error': str(e)}

    # Meta-summarize
    combined = '\n\n'.join(partial_summaries)[:6000]
    meta_prompt = (
        f"You are an academic summarizer. Create a final summary under {max_words} words. "
        "Return ONLY paragraphs without bullets or numbered lists."
    )
    meta_format = ""
    try:
        final_text = _nvidia_chat([
            {"role": "system", "content": meta_prompt + ' ' + meta_format},
            {"role": "user", "content": combined}
        ], temperature=0.3, max_tokens=700)
    except Exception:
        final_text = combined[:min(len(combined), max_words*6)]

    # remove common bullet characters if the model returned them
    cleaned = []
    for line in final_text.splitlines():
        if line.strip().startswith(('-', '*', '•', '1.', '2.', '3.')):
            cleaned.append(line.lstrip('-*• 0123456789.'))
        else:
            cleaned.append(line)
    final_text = '\n'.join(cleaned).strip()

    return {
        'summary': final_text.strip(),
        'bullets': [],
        'keywords': [],
        'chunks': len(chunks) if chunks else 1
    }

# --------- Enhanced Content Analysis for Quiz Generation ---------
def _analyze_content_for_quiz(text: str) -> str:
    """Analyze text content to provide context for better quiz generation."""
    if not text or len(text.strip()) < 100:
        return "Content too short for meaningful analysis."
    
    # Extract key information
    sentences = _split_sentences(text)
    key_terms = _key_terms(text, top_k=15)
    
    # Identify content type and structure
    content_type = _identify_content_type(text)
    
    # Extract specific details
    numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', text)
    dates = re.findall(r'\b(?:19|20)\d{2}\b', text)
    names = re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', text)
    
    # Identify main topics and concepts
    topics = _extract_main_topics(text, key_terms)
    
    # Create analysis summary
    analysis_parts = [
        f"CONTENT TYPE: {content_type}",
        f"MAIN TOPICS: {', '.join(topics[:5])}",
        f"KEY TERMS: {', '.join(key_terms[:8])}",
    ]
    
    if numbers:
        analysis_parts.append(f"NUMERICAL DATA: {', '.join(set(numbers[:5]))}")
    if dates:
        analysis_parts.append(f"DATES MENTIONED: {', '.join(set(dates[:3]))}")
    if names:
        analysis_parts.append(f"PEOPLE/ENTITIES: {', '.join(set(names[:3]))}")
    
    analysis_parts.append(f"TOTAL SENTENCES: {len(sentences)}")
    analysis_parts.append(f"CONTENT LENGTH: {len(text)} characters")
    
    return " | ".join(analysis_parts)

def _identify_content_type(text: str) -> str:
    """Identify the type of content for better question generation."""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['algorithm', 'programming', 'code', 'function', 'variable']):
        return "Technical/Programming"
    elif any(word in text_lower for word in ['theory', 'concept', 'principle', 'framework']):
        return "Theoretical/Academic"
    elif any(word in text_lower for word in ['history', 'timeline', 'chronological', 'century']):
        return "Historical"
    elif any(word in text_lower for word in ['business', 'market', 'economy', 'financial']):
        return "Business/Economic"
    elif any(word in text_lower for word in ['science', 'research', 'experiment', 'study']):
        return "Scientific/Research"
    elif any(word in text_lower for word in ['step', 'process', 'procedure', 'method']):
        return "Procedural/How-to"
    else:
        return "General Educational"

def _extract_main_topics(text: str, key_terms: List[str]) -> List[str]:
    """Extract main topics by analyzing sentence patterns and key terms."""
    sentences = _split_sentences(text)
    topic_scores = {}
    
    for term in key_terms:
        score = 0
        for sentence in sentences:
            if term.lower() in sentence.lower():
                # Higher score for sentences that define or explain the term
                if any(word in sentence.lower() for word in ['is', 'are', 'means', 'refers', 'defined']):
                    score += 3
                elif any(word in sentence.lower() for word in ['important', 'key', 'main', 'primary']):
                    score += 2
                else:
                    score += 1
        topic_scores[term] = score
    
    # Return top-scoring terms as main topics
    sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
    return [topic for topic, score in sorted_topics[:8] if score > 0]

# --------- Quiz helper utilities (fallback path) ---------
_STOPWORDS = set([
    'the','and','for','that','with','from','this','have','will','were','been','they','them','then','than','into','over','under','between','among',
    'your','you','our','their','there','about','also','such','most','more','very','just','some','what','when','where','which','who','whom','whose',
    'because','although','while','before','after','since','until','against','within','without','across','through','during','above','below','each',
    'can','could','would','should','may','might','must','is','are','was','be','being','been','of','in','on','to','a','an','as','it','its'
])

def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text.lower())

def _key_terms(text: str, top_k: int = 15) -> List[str]:
    words = [w for w in _tokenize_words(text) if w not in _STOPWORDS]
    counts = Counter(words)
    return [w for w, _ in counts.most_common(top_k)]

def _split_sentences(text: str) -> List[str]:
    # simple sentence splitter
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    # normalize & dedupe
    seen = set()
    sentences = []
    for s in raw:
        ss = s.strip()
        if len(ss) < 30:
            continue
        key = re.sub(r"\s+", " ", ss.lower())
        if key in seen:
            continue
        seen.add(key)
        sentences.append(ss)
    return sentences[:200]

def _best_sentence_for_term(term: str, sentences: List[str]) -> str:
    # pick the sentence with most occurrences and reasonable length
    scored = []
    for s in sentences:
        score = s.lower().count(term.lower())
        if score > 0:
            penalty = abs(len(s) - 120) / 120.0
            scored.append((score - 0.3*penalty, s))
    if not scored:
        return ''
    scored.sort(reverse=True)
    return scored[0][1]

def _make_mcq(term: str, context_sentence: str, pool_terms: List[str]) -> dict:
    stem = f"Which statement best describes {term}?"
    if context_sentence:
        # correct answer is a trimmed paraphrase based on the sentence
        correct = context_sentence.strip()
        if len(correct) > 120:
            correct = correct[:117] + '...'
    else:
        correct = f"{term.title()} refers to a key concept discussed in the material."

    distractors = []
    # use other high-frequency terms to craft plausible distractors
    for t in pool_terms:
        if t == term:
            continue
        distractors.append(f"Focuses primarily on {t} and unrelated details")
        if len(distractors) >= 3:
            break
    while len(distractors) < 3:
        fillers = [
            "Presents background information without defining the idea",
            "Describes an example case but not the concept itself",
            "Highlights a tangential point rather than the main concept",
        ]
        distractors.append(fillers[len(distractors) % len(fillers)])

    options = [correct] + distractors[:3]
    import random
    random.shuffle(options)
    correct_index = options.index(correct)
    return {
        'id': str(uuid.uuid4()),
        'question': stem,
        'options': options,
        'correctAnswer': correct_index
    }

# ---------------- Video Upload/URL endpoints -----------------
def _safe_remove(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def _extract_audio_wav(video_path: str) -> str:
    """Extract mono 16k wav from video using ffmpeg-python. Returns wav path."""
    # Try to use imageio-ffmpeg bundled binary first
    print("=== FFmpeg Detection Debug ===")
    print(f"Current PATH: {os.environ.get('PATH', 'Not set')}")
    # Also check if FFmpeg is in the specific directory you mentioned
    ffmpeg_custom_path = r"C:\Users\Lakshmi Makkena\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
    if os.path.exists(ffmpeg_custom_path):
        print(f"Custom FFmpeg found at: {ffmpeg_custom_path}")
        os.environ['FFMPEG_BINARY'] = ffmpeg_custom_path
        print("Using custom FFmpeg path")
        # Do not return here; proceed to use ffmpeg below
    else:
        print(f"Custom FFmpeg not found at: {ffmpeg_custom_path}")
    
    try:
        import imageio_ffmpeg  # type: ignore
        print("imageio-ffmpeg imported successfully")
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"imageio-ffmpeg.get_ffmpeg_exe() returned: {ffmpeg_exe}")
        
        if ffmpeg_exe and os.path.exists(ffmpeg_exe):
            print(f"Bundled FFmpeg exists at: {ffmpeg_exe}")
            # Handle paths with spaces by wrapping in quotes for environment variable
            ffmpeg_exe_quoted = f'"{ffmpeg_exe}"' if ' ' in ffmpeg_exe else ffmpeg_exe
            os.environ['FFMPEG_BINARY'] = ffmpeg_exe_quoted
            print(f"Using bundled FFmpeg: {ffmpeg_exe}")
            print(f"FFMPEG_BINARY env var set to: {ffmpeg_exe_quoted}")
        else:
            print(f"Bundled FFmpeg path invalid or file doesn't exist: {ffmpeg_exe}")
            raise RuntimeError('imageio-ffmpeg did not provide a valid ffmpeg binary path')
    except Exception as e:
        print(f"imageio-ffmpeg fallback failed: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        # Fall back to system ffmpeg if available
        print("Trying system FFmpeg...")
        ffmpeg_path = shutil.which('ffmpeg')
        print(f"shutil.which('ffmpeg') returned: {ffmpeg_path}")
        
        if ffmpeg_path:
            os.environ['FFMPEG_BINARY'] = ffmpeg_path
            print(f"Using system FFmpeg: {ffmpeg_path}")
        else:
            print("System FFmpeg not found in PATH")
            raise RuntimeError(
                'FFmpeg not available. Install FFmpeg (https://www.gyan.dev/ffmpeg/builds/) and add to PATH, '
                'or ensure imageio-ffmpeg fallback can download the binary.'
            )

    import ffmpeg
    wav_fd, wav_path = tempfile.mkstemp(suffix='.wav')
    os.close(wav_fd)
    try:
        (
            ffmpeg
            .input(video_path)
            .output(wav_path, acodec='pcm_s16le', ac=1, ar='16000', vn=None)
            .overwrite_output()
            .run(quiet=True)
        )
        return wav_path
    except Exception as e:
        _safe_remove(wav_path)
        raise

def _transcribe_wav(wav_path: str) -> str:
    """Try local Whisper if available; otherwise return placeholder text."""
    try:
        import whisper  # type: ignore
        model = whisper.load_model("base")
        result = model.transcribe(wav_path, language=None)
        text = (result.get('text') or '').strip()
        if text:
            return text
    except Exception as _whisper_err:
        # Fall back to placeholder if whisper missing or fails
        pass
    return (
        "Transcription placeholder: speech-to-text is not configured. "
        "Install local Whisper to enable real transcription."
    )

@app.route('/api/video/save', methods=['POST'])
def save_video_summary():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        data = request.json
        title = data.get('title')
        summary_text = data.get('summary_text')
        video_url = data.get('video_url', '')

        if not title or not summary_text:
            return jsonify({'error': 'Title and summary are required'}), 400

        new_summary = VideoSummary(
            user_id=user_id,
            title=title,
            summary_text=summary_text,
            video_url=video_url
        )
        db.session.add(new_summary)
        if user:
            _update_user_streak(user)
        db.session.commit()

        return jsonify({'message': 'Summary saved successfully', 'id': new_summary.id})
    except Exception as e:
        print(f"Error saving summary: {e}")
        return jsonify({'error': 'Failed to save summary'}), 500

@app.route('/api/video/saved', methods=['GET'])
def get_saved_summaries():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        summaries = VideoSummary.query.filter_by(user_id=user_id).order_by(VideoSummary.created_at.desc()).all()
        return jsonify({'summaries': [s.to_dict() for s in summaries]})
    except Exception as e:
        print(f"Error fetching saved summaries: {e}")
        return jsonify({'error': 'Failed to fetch summaries'}), 500

@app.route('/api/tts', methods=['POST'])
def generate_tts():
    try:
        data = request.json
        text = data.get('text')
        if not text:
            return jsonify({'error': 'Text is required'}), 400

        # Truncate text if too long for simple TTS (optional limit)
        if len(text) > 5000:
            text = text[:5000]

        tts = gTTS(text=text, lang='en')
        
        # Save to memory buffer
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        return send_file(
            mp3_fp,
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="summary_audio.mp3"
        )
    except Exception as e:
        print(f"Error generating TTS: {e}")
        return jsonify({'error': 'Failed to generate audio'}), 500

@app.route('/api/summarize-video', methods=['POST'])
def summarize_video():
    try:
        print("=== Video Summarization Started ===")

        if not (request.content_type and 'multipart/form-data' in request.content_type):
            return jsonify({'error': 'Use multipart/form-data with field "video"'}), 400
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        max_words = int(request.form.get('maxWords', 250))
        video_file = request.files['video']
        print(f"Received video file: {video_file.filename}, size: {len(video_file.read())} bytes")
        video_file.seek(0)  # Reset file pointer after reading

        tmp_fd, tmp_video = tempfile.mkstemp(suffix='.mp4')
        os.close(tmp_fd)
        print(f"Created temp video file: {tmp_video}")
        video_file.save(tmp_video)
        print(f"Video saved to temp file, size: {os.path.getsize(tmp_video)} bytes")

        wav_path = None
        try:
            print("Extracting audio from video...")
            wav_path = _extract_audio_wav(tmp_video)
            print(f"Audio extracted to: {wav_path}")
            
            print("Transcribing audio...")
            transcript = _transcribe_wav(wav_path)
            print(f"Transcript length: {len(transcript)} characters")
            
            print("Generating summary with LLM...")
            result = _summarize_text_with_llm(transcript, max_words=max_words)
            result.update({'status': 'success', 'warnings': ['placeholder_transcript']})
            print("Video summarization completed successfully")
            return jsonify(result)
        finally:
            print(f"Cleaning up temp files...")
            _safe_remove(tmp_video)
            if wav_path:
                _safe_remove(wav_path)
    except Exception as e:
        print(f"Video summarization error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/summarize-url', methods=['POST'])
def summarize_url():
    try:
        # print("DEBUG: summarize_url endpoint hit", flush=True)
        data = request.get_json() or {}
        url = (data.get('url') or '').strip()
        max_words = int(data.get('maxWords', 250))
        if not url:
            return jsonify({'error': 'No url provided'}), 400

        # Check if it's a YouTube URL
        if 'youtube.com' in url or 'youtu.be' in url:
            try:
                # Extract video ID from YouTube URL
                video_id = None
                
                # Handle different YouTube URL formats
                if 'youtube.com/watch?v=' in url:
                    video_id = url.split('v=')[1].split('&')[0]
                elif 'youtu.be/' in url:
                    video_id = url.split('youtu.be/')[1].split('?')[0]
                
                if video_id:
                    # Attempt to fetch captions via yt-dlp (no download)
                    try:
                        ydl_opts = {
                            'quiet': True,
                            'no_warnings': True,
                            'skip_download': True,
                            'socket_timeout': 10,
                        }
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                        
                        captions_text = ''
                        # Prefer human subtitles; fallback to automatic captions
                        subtitle_sets = [
                            (info.get('subtitles') or {}),
                            (info.get('automatic_captions') or {})
                        ]
                        
                        def pick_lang(subs_dict):
                            for lang_key in ['en', 'en-US', 'en-GB']:
                                if lang_key in subs_dict:
                                    return subs_dict[lang_key]
                            # fallback: any language
                            if subs_dict:
                                first_key = next(iter(subs_dict.keys()))
                                return subs_dict[first_key]
                            return None
                            
                        picked = None
                        for s in subtitle_sets:
                            picked = pick_lang(s)
                            if picked:
                                break
                                
                        if picked:
                            # Find a URL (prefer vtt)
                            sub_url = None
                            for item in picked:
                                if item.get('ext') == 'vtt':
                                    sub_url = item.get('url')
                                    break
                            if not sub_url and picked:
                                sub_url = picked[0].get('url')
                            
                            if sub_url:
                                # fetch captions
                                cap_res = requests.get(sub_url, timeout=10)
                                if cap_res.status_code == 200:
                                    captions_text = cap_res.text
                                    # Simple cleanup of VTT
                                    lines = captions_text.splitlines()
                                    clean_lines = []
                                    for line in lines:
                                        if '-->' in line: continue
                                        if not line.strip(): continue
                                        if line.strip().isdigit(): continue
                                        if line.strip().startswith('WEBVTT'): continue
                                        clean_lines.append(line.strip())
                                    captions_text = ' '.join(clean_lines)
                        
                        if captions_text:
                            # Summarize captions
                            result = _summarize_text_with_llm(captions_text, max_words=max_words)
                            result.update({'video_id': video_id, 'url': url})
                            return jsonify({'status': 'success', **result})
                            
                    except Exception as e:
                        print(f"YouTube caption fetch failed: {e}")
                        # Fall through to normal processing (or error)
                        pass
        
                # Fallback: attempt audio download and local transcription using Whisper
                try:
                    print("DEBUG: Captions unavailable, attempting audio download...", flush=True)
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Configure yt-dlp to download audio
                        ydl_opts_audio = {
                            'format': 'bestaudio/best',
                            'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '192',
                            }],
                            'quiet': True,
                            'no_warnings': True,
                        }
                        
                        audio_path = None
                        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                            ydl.download([url])
                            # Find the downloaded file
                            for file in os.listdir(temp_dir):
                                if file.endswith('.mp3'):
                                    audio_path = os.path.join(temp_dir, file)
                                    break
                        
                        if audio_path and os.path.exists(audio_path):
                            print(f"DEBUG: Audio downloaded to {audio_path}, starting transcription...", flush=True)
                            # Load Whisper model (use 'base' for speed/accuracy balance)
                            model = whisper.load_model("base")
                            transcription_result = model.transcribe(audio_path)
                            transcript_text = transcription_result["text"]
                            
                            if transcript_text:
                                print("DEBUG: Transcription successful", flush=True)
                                result = _summarize_text_with_llm(transcript_text, max_words=max_words)
                                result.update({
                                    'status': 'success', 
                                    'warnings': ['generated_from_audio'],
                                    'video_id': video_id,
                                    'url': url
                                })
                                return jsonify(result)
                                
                except Exception as e:
                    print(f"Audio fallback failed: {e}", flush=True)
                    # If fallback fails, return the guidance message
                    pass

                # If we reach here, both captions and audio fallback failed
                transcript = (
                    f"This is a YouTube video (ID: {video_id}). "
                    "Captions were unavailable and audio transcription failed.\n\n"
                    "Please use the 'Upload Video' tab to upload the file, or paste the transcript in the 'Paste Transcript' tab."
                )
                # Return guidance directly without LLM summary to avoid conversational response
                result = {
                    'summary': transcript,
                    'bullets': [],
                    'keywords': [],
                    'chunks': 0
                }
                result.update({
                    'status': 'success', 
                    'warnings': ['youtube_fetch_limited', 'audio_fallback_failed'],
                    'video_id': video_id,
                    'url': url
                })
                return jsonify(result)

            except Exception as e:
                return jsonify({'error': f'Error processing YouTube URL: {str(e)}'}), 500
        else:
            # For non-YouTube URLs, provide guidance
            transcript = (
                f"URL provided: {url}\n\n"
                "This appears to be a non-YouTube URL. For video summarization, please:\n"
                "1. Use the 'Upload Video' tab to upload video files directly, OR\n"
                "2. Copy the transcript/captions and use the 'Paste Transcript' tab."
            )
            
            # Return guidance directly without LLM summary
            result = {
                'summary': transcript,
                'bullets': [],
                'keywords': [],
                'chunks': 0
            }
            result.update({
                'status': 'success', 
                'warnings': ['non_youtube_url', 'use_upload_or_transcript_tabs']
            })
            return jsonify(result)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _nvidia_chat(messages, temperature=0.7, max_tokens=1500):
    if not NVIDIA_API_KEY:
        raise RuntimeError('Missing NVIDIA_API_KEY environment variable')

    headers = {
        'Authorization': f'Bearer {NVIDIA_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': NVIDIA_MODEL,
        'messages': messages,
        'temperature': float(temperature),
        'max_tokens': int(max_tokens),
        'stream': False
    }

    response = requests.post(
        f"{NVIDIA_API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(f"NVIDIA API error: {response.status_code} - {response.text}")

    result = response.json()
    return result['choices'][0]['message']['content']


def _format_paragraphs(text: str) -> str:
    try:
        s = text or ''
        # Strip typical bullet/numbering prefixes at line starts
        lines = []
        for ln in s.splitlines():
            t = ln.lstrip()
            for prefix in ('- ', '* ', '• ', '1. ', '2. ', '3. ', '4. ', '5. '):
                if t.startswith(prefix):
                    t = t[len(prefix):]
                    break
            lines.append(t)
        s = '\n'.join(lines)
        # Collapse 3+ newlines -> 2, and single bullet-induced newlines -> spaces within paragraphs
        import re as _re
        s = _re.sub(r'\n{3,}', '\n\n', s)
        # If still no paragraph breaks, heuristically break after sentences
        if '\n\n' not in s and len(s) > 400:
            s = s.replace('. ', '.\n\n')
        return s.strip()
    except Exception:
        return text


@app.route('/api/chat/sessions', methods=['GET'])
def get_chat_sessions():
    user = _get_current_user()
    if not user:
        # For anonymous users, we might want to support local storage based sessions or just return empty
        # But for now, let's require auth for history or handle anonymous differently
        return jsonify({'sessions': []})
    
    sessions = ChatSession.query.filter_by(user_id=user.id).order_by(ChatSession.updated_at.desc()).all()
    return jsonify({'sessions': [s.to_dict() for s in sessions]})

@app.route('/api/chat/sessions/<session_id>', methods=['GET'])
def get_chat_session(session_id):
    user = _get_current_user()
    # Allow anonymous access if session exists? Maybe not for privacy.
    # But for now, let's check user ownership if logged in.
    
    if user:
        session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
    else:
        # If anonymous, maybe allow if they have the ID? 
        # But we don't store anonymous user_id easily.
        # Let's assume history is a logged-in feature for now.
        return jsonify({'error': 'Unauthorized'}), 401
        
    if not session:
        return jsonify({'error': 'Session not found'}), 404
        
    messages = ChatHistory.query.filter_by(session_id=session_id).order_by(ChatHistory.created_at.asc()).all()
    return jsonify({
        'session': session.to_dict(),
        'messages': [m.to_dict() for m in messages]
    })

@app.route('/api/chat/sessions', methods=['POST'])
def create_chat_session():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json(silent=True) or {}
    title = data.get('title', 'New Chat')
    
    session = ChatSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=title
    )
    db.session.add(session)
    db.session.commit()
    return jsonify(session.to_dict())

@app.route('/api/chat/sessions/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
        
    db.session.delete(session)
    db.session.commit()
    return jsonify({'message': 'Session deleted'})

# --- Document Management Endpoints ---

@app.route('/api/documents', methods=['GET'])
def get_documents():
    user = _get_current_user()
    if not user:
        return jsonify({'documents': []})
    
    docs = Document.query.filter_by(user_id=user.id).order_by(Document.created_at.desc()).all()
    return jsonify({'documents': [d.to_dict() for d in docs]})

@app.route('/api/documents', methods=['POST'])
def upload_document():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400
        
    try:
        # Extract text from PDF
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        
        if not text.strip():
            return jsonify({'error': 'Could not extract text from PDF'}), 400
            
        # Save to database
        doc = Document(
            id=str(uuid.uuid4()),
            user_id=user.id,
            filename=file.filename,
            content=text
        )
        db.session.add(doc)
        db.session.commit()
        
        return jsonify(doc.to_dict())
        
    except Exception as e:
        print(f"PDF upload error: {e}")
        return jsonify({'error': 'Failed to process PDF'}), 500

@app.route('/api/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    doc = Document.query.filter_by(id=doc_id, user_id=user.id).first()
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
        
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document deleted'})

# --- Analytics Endpoints ---

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_analytics_dashboard():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    # Fetch all quiz scores for the user
    scores = QuizScore.query.filter_by(user_id=user.id).order_by(QuizScore.created_at.asc()).all()
    
    total_quizzes = len(scores)
    if total_quizzes == 0:
        return jsonify({
            'total_quizzes': 0,
            'average_score': 0,
            'recent_activity': [],
            'weak_areas': []
        })
        
    # Calculate Average Score
    total_score = sum(s.score_percentage for s in scores)
    average_score = round(total_score / total_quizzes, 1)
    
    # Prepare Recent Activity (Last 10)
    # Format for Recharts: { date: 'YYYY-MM-DD', score: 85 }
    recent_activity = []
    for s in scores[-10:]:
        recent_activity.append({
            'date': s.created_at.strftime('%Y-%m-%d'),
            'score': s.score_percentage,
            'title': s.quiz_title or 'Untitled Quiz'
        })
        
    # Fetch dismissed focus areas
    dismissed = FocusAreaDismissal.query.filter_by(user_id=user.id).all()
    dismissed_ids = {d.quiz_score_id for d in dismissed}

    # Identify Weak Areas (Score < 60%)
    weak_areas = []
    for s in scores:
        if s.score_percentage < 60 and s.id not in dismissed_ids:
            weak_areas.append({
                'id': s.id,
                'title': s.quiz_title or 'Untitled Quiz',
                'score': s.score_percentage,
                'date': s.created_at.strftime('%Y-%m-%d'),
                'video_suggestion_url': f"https://www.youtube.com/results?search_query=learn+{requests.utils.quote(s.quiz_title or 'general knowledge')}"
            })
    
    # Sort weak areas by date desc (most recent first)
    weak_areas.sort(key=lambda x: x['date'], reverse=True)

    # 3. Subject Mastery (Bar Chart Data)
    # Group scores by topic (using crude string matching or stored topic)
    topic_scores = defaultdict(list)
    for s in scores:
        t = (s.quiz_title or 'General').lower()
        # Clean up topic name a bit (remove "quiz on ", etc)
        t = t.replace('quiz on ', '').replace(' quiz', '').strip().title()
        topic_scores[t].append(s.score_percentage)
    
    mastery_distribution = []
    for t, vals in topic_scores.items():
        if len(vals) > 0:
            avg = sum(vals) / len(vals)
            mastery_distribution.append({'subject': t, 'score': round(avg, 1), 'count': len(vals)})
    
    # Sort by score desc and take top 5
    mastery_distribution.sort(key=lambda x: x['score'], reverse=True)
    mastery_distribution = mastery_distribution[:6]

    # 4. Activity Breakdown (Pie Chart Data)
    # Count different types of activities
    summaries_count = VideoSummary.query.filter_by(user_id=user.id).count()
    feynman_count = FeynmanScore.query.filter_by(user_id=user.id).count()
    
    activity_breakdown = [
        {'name': 'Quizzes', 'value': total_quizzes, 'color': '#0088FE'},
        {'name': 'Video Summaries', 'value': summaries_count, 'color': '#00C49F'},
        {'name': 'Teaching (Feynman)', 'value': feynman_count, 'color': '#FFBB28'}
    ]
    # Filter out zero values
    activity_breakdown = [x for x in activity_breakdown if x['value'] > 0]

    current_streak = user.current_streak
    max_streak = user.max_streak

    return jsonify({
        'total_quizzes': total_quizzes,
        'average_score': average_score,
        'recent_activity': recent_activity,
        'weak_areas': weak_areas[:5],
        'mastery_distribution': mastery_distribution,
        'activity_breakdown': activity_breakdown,
        'streak': {
            'current': current_streak,
            'max': max_streak,
            'last_activity': user.last_activity_date.isoformat() if user.last_activity_date else None
        }
    })


@app.route('/api/voice-qa-stream', methods=['GET'])
def voice_qa_stream():
    try:
        question = (request.args.get('question') or '').strip()
        if not question:
            return jsonify({'error': 'No question provided'}), 400

        def event_stream():
            try:
                print(f"Starting streaming for question: {question[:50]}...")
                answer = _nvidia_chat([
                    {"role": "user", "content": question}
                ], temperature=0.6, max_tokens=1500)
                answer = _format_paragraphs(answer)
                print(f"Got answer, length: {len(answer)}")
            except Exception as ai_error:
                print(f"AI error in streaming: {ai_error}")
                answer = (
                    "I'm unable to reach the AI service right now. Please try again, "
                    "or check your API configuration."
                )
            # naive word streaming to improve UX
            words = answer.split()
            buffer = []
            for i, w in enumerate(words):
                buffer.append(w)
                if len(buffer) >= 4 or i == len(words) - 1:
                    chunk = ' '.join(buffer)
                    print(f"Yielding chunk: {chunk[:30]}...")
                    yield f"data: {chunk}\n\n"
                    buffer = []
                    time.sleep(0.03)
            print("Streaming complete, sending [DONE]")
            yield "data: [DONE]\n\n"

        response = Response(event_stream(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Cache-Control'
        return response
    except Exception as e:
        print(f"Streaming endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/voice-qa', methods=['POST'])
def voice_qa():
    try:
        user = _get_current_user()
        
        # Check if it's a text question or audio file
        want_tts = False
        session_id = None
        document_id = None
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Audio file upload
            if 'audio' not in request.files:
                return jsonify({'error': 'No audio file provided'}), 400
            
            audio_file = request.files['audio']
            want_tts = (request.form.get('tts') or 'false').lower() == 'true'
            session_id = request.form.get('session_id')
            document_id = request.form.get('document_id')
            
            # Save audio file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                audio_file.save(temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                # For now, we'll use a simple fallback for speech-to-text
                # In a real app, use Whisper here
                question = "What is artificial intelligence and how does it work?"
                # If we had real transcription, we'd use it here
                # transcript = _transcribe_wav(temp_file_path)
                # if transcript: question = transcript
                
                print("Speech-to-text not implemented yet - using fallback")
                
                # Clean up temporary file
                os.unlink(temp_file_path)
                
            except Exception as whisper_error:
                # Fallback if speech-to-text fails
                question = "What is artificial intelligence and how does it work?"
                print(f"Speech-to-text error: {whisper_error}")
            
        else:
            # Text question
            data = request.get_json()
            if not data or 'question' not in data:
                return jsonify({'error': 'No question provided'}), 400
            
            question = data['question']
            want_tts = bool(data.get('tts', False))
            session_id = data.get('session_id')
            document_id = data.get('document_id')
        
        # Use NVIDIA API for AI responses
        try:
            print(f"Attempting NVIDIA chat. Base={NVIDIA_API_BASE}, Model={NVIDIA_MODEL}")
            
            messages = []
            mode = request.form.get('mode') if request.content_type and 'multipart/form-data' in request.content_type else (data.get('mode') if 'data' in locals() else None)

            # System Prompt Selection
            if mode == 'interview':
                system_prompt = (
                    "You are a professional technical interviewer. "
                    "Conduct a mock interview with the user for the role they specify. "
                    "Ask one question at a time. "
                    "Evaluate their answers briefly and then ask the next relevant question. "
                    "Be professional, encouraging, but rigorous. "
                    "Start by asking them what role they are applying for if they haven't said it yet."
                )
                messages.append({"role": "system", "content": system_prompt})
            
            # Inject Document Context if provided (can be combined with interview)
            if document_id and user:
                doc = Document.query.filter_by(id=document_id, user_id=user.id).first()
                if doc:
                    # Truncate content to avoid token limits (simple approach)
                    context_text = doc.content[:10000] 
                    if mode == 'interview':
                        messages.append({
                            "role": "system", 
                            "content": f"Use the following document as the resume or job description context for the interview.\n\nContext:\n{context_text}"
                        })
                    else:
                        messages.append({
                            "role": "system", 
                            "content": f"You are a helpful assistant. Use the following document content to answer the user's question. If the answer is not in the document, say so.\n\nDocument Content:\n{context_text}"
                        })
                    print(f"Using document context: {doc.filename}")
            
            messages.append({"role": "user", "content": question})
            
            answer = _nvidia_chat(messages, max_tokens=1500)
            provider = 'nvidia'
            print("Successfully got response from NVIDIA API")
        except Exception as ai_error:
            # Fallback to hardcoded responses if NVIDIA API fails
            print(f"NVIDIA API error: {ai_error}")
            provider = 'fallback'
            if 'artificial intelligence' in question.lower() or 'ai' in question.lower():
                answer = "Artificial Intelligence (AI) is a branch of computer science that aims to create systems capable of performing tasks that typically require human intelligence. These tasks include learning, reasoning, problem-solving, perception, and language understanding. AI works through various techniques including machine learning, deep learning, natural language processing, and computer vision."
            elif 'machine learning' in question.lower():
                answer = "Machine Learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed. It uses algorithms to identify patterns in data and make predictions or decisions. Common types include supervised learning, unsupervised learning, and reinforcement learning."
            elif 'python' in question.lower():
                answer = "Python is a high-level, interpreted programming language known for its simplicity and readability. It's widely used in data science, web development, AI, and automation. Python's extensive libraries like NumPy, Pandas, and TensorFlow make it ideal for machine learning and data analysis."
            elif 'javascript' in question.lower():
                answer = "JavaScript is a programming language primarily used for web development. It runs in browsers and enables interactive web pages. JavaScript is essential for frontend development and is also used in backend development with Node.js."
            elif 'react' in question.lower():
                answer = "React is a JavaScript library for building user interfaces, particularly single-page applications. It's maintained by Facebook and allows developers to create reusable UI components. React uses a virtual DOM for efficient rendering and is popular for modern web development."
            else:
                answer = f"I'm here to help with your learning questions! You asked: '{question}'. I can assist with topics like programming, artificial intelligence, machine learning, web development, and more. Feel free to ask me anything about these subjects."
        
        # Save to history if user is logged in
        if user:
            if not session_id:
                # Create new session
                # Generate a simple title from the first question
                title = question[:60] + "..." if len(question) > 60 else question
                session = ChatSession(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    title=title
                )
                db.session.add(session)
                session_id = session.id
            else:
                # Verify session exists and belongs to user
                session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
                if not session:
                    # If invalid session, create new one
                    title = question[:60] + "..." if len(question) > 60 else question
                    session = ChatSession(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        title=title
                    )
                    db.session.add(session)
                    session_id = session.id
                else:
                    session.updated_at = datetime.utcnow()
            
            # Save message
            history = ChatHistory(
                user_id=user.id,
                session_id=session_id,
                user_message=question,
                ai_response=answer,
                context='voice_qa'
            )
            db.session.add(history)
            db.session.commit()

        # Optionally synthesize answer to audio (MP3) when requested
        audio_b64 = None
        if want_tts and answer:
            try:
                tts = gTTS(text=answer, lang='en', slow=False)
                buf = io.BytesIO()
                tts.write_to_fp(buf)
                buf.seek(0)
                audio_b64 = base64.b64encode(buf.read()).decode('utf-8')
            except Exception as tts_err:
                print(f"TTS synthesis failed: {tts_err}")

        resp = {
            'question': question,
            'answer': answer,
            'status': 'success',
            'provider': provider,
            'session_id': session_id,
            'nvidia': {
                'base': NVIDIA_API_BASE,
                'model': NVIDIA_MODEL,
                'key_present': bool(NVIDIA_API_KEY)
            }
        }
        if audio_b64:
            resp.update({'audioBase64': audio_b64, 'audioMime': 'audio/mpeg'})
        return jsonify(resp)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json() or {}
        items = data.get('items')
        title = data.get('title', 'Smart Learning Assistant - Q&A')
        if not items:
            q = data.get('question')
            a = data.get('answer')
            if not q or not a:
                return jsonify({'error': 'Provide either items[] or question+answer'}), 400
            items = [{'question': q, 'answer': a}]
        # Build PDF
        pdf = FPDF()
        pdf.set_auto_page_break(True, margin=15)
        pdf.add_page()
        pdf.set_title(title)
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(4)
        for idx, item in enumerate(items, start=1):
            question_text = str(item.get('question', ''))
            options = item.get('options', [])
            correct_answer = item.get('correctAnswer', 0)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.multi_cell(0, 8, f"Q{idx}: {question_text}")
            pdf.set_font('Arial', '', 12)
            
            if options and len(options) == 4:
                for i, option in enumerate(options):
                    pdf.multi_cell(0, 8, f"   {chr(65+i)}. {option}")
            else:
                # Fallback for old format
                answer_text = str(item.get('answer', ''))
                pdf.multi_cell(0, 8, f"A{idx}: {answer_text}")
            
            pdf.ln(2)
        # Output to bytes
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='qa.pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-answer-key', methods=['POST'])
def generate_answer_key():
    try:
        data = request.get_json() or {}
        items = data.get('items')
        title = data.get('title', 'Quiz Answer Key')
        if not items:
            return jsonify({'error': 'No items provided'}), 400
        
        # Build PDF with answers
        pdf = FPDF()
        pdf.set_auto_page_break(True, margin=15)
        pdf.add_page()
        pdf.set_title(title)
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(4)
        
        for idx, item in enumerate(items, start=1):
            question_text = str(item.get('question', ''))
            options = item.get('options', [])
            correct_answer = item.get('correctAnswer', 0)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.multi_cell(0, 8, f"Q{idx}: {question_text}")
            pdf.set_font('Arial', '', 12)
            
            if options and len(options) == 4:
                for i, option in enumerate(options):
                    marker = "✓" if i == correct_answer else "○"
                    pdf.multi_cell(0, 8, f"   {chr(65+i)}. {option} {marker}")
            else:
                # Fallback for old format
                answer_text = str(item.get('answer', ''))
                pdf.multi_cell(0, 8, f"A{idx}: {answer_text}")
            
            pdf.ln(2)
        
        # Output to bytes
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='answer_key.pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'Smart Learning Assistant Backend (NVIDIA API)', 'nvidia': {
        'base': NVIDIA_API_BASE,
        'model': NVIDIA_MODEL,
        'key_present': bool(NVIDIA_API_KEY)
    }})


@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        num_questions = 5
        source_text = None
        # Accept either multipart/form-data with a PDF, or JSON with text
        if request.content_type and 'multipart/form-data' in request.content_type:
            num_questions = int(request.form.get('numQuestions', 5))
            if 'pdf' not in request.files:
                return jsonify({'error': 'No PDF file provided'}), 400
            pdf_file = request.files['pdf']
            # Extract text from PDF (robust)
            source_text = extract_text_from_pdf_stream(pdf_file.stream)
        else:
            data = request.get_json() or {}
            num_questions = int(data.get('numQuestions', 5))
            source_text = (data.get('text') or '').strip()

        if not source_text:
            return jsonify({'error': 'No text found to generate quiz from'}), 400
        
        # Debug: log the first 500 characters of extracted text
        print(f"Extracted text preview: {source_text[:500]}...", flush=True)
        print(f"Total text length: {len(source_text)} characters", flush=True)
        print("DEBUG: Starting content analysis...", flush=True)

        # Enhanced content analysis for better question generation
        content_analysis = _analyze_content_for_quiz(source_text)
        
        system_prompt = (
            "You are an expert assessment designer creating HIGHLY DIVERSE, content-specific multiple-choice questions.\n"
            "OUTPUT STRICT JSON ONLY: {\"title\": \"Short Descriptive Topic Title\", \"items\":[{\"id\":\"uuid\",\"topic\":\"Specific Concept\",\"question\":\"...\",\"options\":[\"...\",\"...\",\"...\",\"...\"],\"correctAnswer\":0}]}\n"
            "\n"
            "MAXIMUM DIVERSITY REQUIREMENTS:\n"
            "- Create EXTREMELY DIVERSE questions that test different cognitive levels\n"
            "- Each question must be COMPLETELY UNIQUE in structure, approach, and content focus\n"
            "- Vary question complexity: basic recall, comprehension, application, analysis, synthesis, evaluation\n"
            "- Use CREATIVE question formats and phrasings\n"
            "- Test different aspects: facts, concepts, processes, relationships, implications\n"
            "\n"
            "QUESTION TYPE VARIETY (use different types for each question):\n"
            "1. DEFINITION: 'What is the precise definition of [specific term] according to the text?'\n"
            "2. APPLICATION: 'In which scenario would [specific concept] be most effective?'\n"
            "3. CAUSE-EFFECT: 'What is the primary cause of [specific phenomenon] mentioned?'\n"
            "4. COMPARISON: 'How does [concept A] differ fundamentally from [concept B]?'\n"
            "5. ANALYSIS: 'What does the author suggest about [specific topic]?'\n"
            "6. SYNTHESIS: 'Based on the evidence presented, what conclusion can be drawn?'\n"
            "7. EVALUATION: 'Which statement best evaluates the effectiveness of [specific method]?'\n"
            "8. SCENARIO: 'If [specific situation] occurred, what would be the expected outcome?'\n"
            "9. SEQUENCE: 'What is the correct order of [specific process] steps?'\n"
            "10. IMPLICATION: 'What would happen if [specific condition] were changed?'\n"
            "\n"
            "CREATIVE QUESTION STRUCTURES:\n"
            "- Use varied sentence structures and question beginnings\n"
            "- Include scenario-based questions with specific contexts\n"
            "- Create 'best answer' vs 'correct answer' variations\n"
            "- Use 'according to the text' vs 'based on the information' variations\n"
            "- Include numerical, chronological, and categorical questions\n"
            "- Mix concrete facts with abstract concepts\n"
            "\n"
            "CONTENT-SPECIFIC REQUIREMENTS:\n"
            "- Reference SPECIFIC names, dates, numbers, percentages, or unique details\n"
            "- Use EXACT terminology and phrases from the source material\n"
            "- Create SMART distractors that are contextually plausible but factually incorrect\n"
            "- Ensure correct answers are DIRECTLY supported by the provided text\n"
            "- Test comprehension of DIFFERENT sections, concepts, and details\n"
            "- Include questions about specific examples, case studies, or data points\n"
            "- Assign a specific 'topic' tag to each question (e.g., 'History', 'Biology', 'Python')\n"
            "- GENERATE A SHORT, DESCRIPTIVE TITLE for the quiz based on the content (e.g., 'Introduction to Quantum Mechanics')\n"
            "\n"
            "TECHNICAL REQUIREMENTS:\n"
            "- Exactly 4 options, 1 correct answer\n"
            "- Options under 100 characters each for clarity\n"
            "- Questions 12-35 words long\n"
            "- NO repetitive question patterns or similar structures\n"
            "- NO generic or template-based questions\n"
            "- Each question must test a DIFFERENT aspect of the content\n"
            f"- Generate exactly {num_questions} HIGHLY DIVERSE items\n"
            "\n"
            f"CONTENT ANALYSIS SUMMARY:\n{content_analysis}\n"
            "\n"
            "Create questions that test comprehensive mastery through varied cognitive approaches and content focus."
        )

        try:
            print("DEBUG: Calling _nvidia_chat...", flush=True)
            ai_text = _nvidia_chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": source_text[:6000]}  # limit payload
            ], temperature=0.8, max_tokens=1500)  # Higher temperature for maximum diversity
            print("DEBUG: _nvidia_chat returned successfully.", flush=True)

            # Try to locate JSON in the response
            start = ai_text.find('{')
            end = ai_text.rfind('}')
            items = []
            generated_title = None
            
            if start != -1 and end != -1 and end > start:
                snippet = ai_text[start:end+1]
                try:
                    parsed = json.loads(snippet)
                    if isinstance(parsed, dict):
                        items = parsed.get('items')
                        generated_title = parsed.get('title')
                    else:
                        items = parsed
                except Exception:
                    items = []

            if not items or not isinstance(items, list):
                raise RuntimeError('Model did not return valid JSON items')

            # STRICTLY enforce the requested number of questions
            if len(items) > num_questions:
                print(f"DEBUG: Trimming generated items from {len(items)} to {num_questions}")
                items = items[:num_questions]

            # Normalize and ensure IDs exist; enforce exactly 4 options and 1 correct
            normalized = []
            for it in items:
                q = str(it.get('question', '')).strip()
                options = it.get('options', [])
                correct_answer = it.get('correctAnswer', 0)
                topic = str(it.get('topic') or 'General').strip()
                
                # Validate options
                if not q or not isinstance(options, list) or len(options) != 4:
                    continue
                
                # Ensure all options are strings
                options = [str(opt).strip() for opt in options if str(opt).strip()]
                if len(options) != 4:
                    continue
                
                # Validate correct answer index
                if not isinstance(correct_answer, int) or not (0 <= correct_answer <= 3):
                    continue
                # Extra guard: ensure uniqueness of correct option value
                if len(set(options)) != 4:
                    continue
                
                item_id = it.get('id') or str(uuid.uuid4())
                normalized.append({
                    'id': item_id, 
                    'question': q, 
                    'options': options,
                    'correctAnswer': correct_answer,
                    'topic': topic
                })

            if not normalized:
                raise RuntimeError('No valid items after normalization')

            return jsonify({
                'status': 'success', 
                'items': normalized, 
                'title': generated_title,
                'provider': 'nvidia'
            })

        except Exception as e:
            # 1) LLM JSON repair retry with stricter instruction
            try:
                repair_prompt = (
                    "CRITICAL: Return ONLY valid JSON in this exact format: "
                    "{\"title\": \"Topic Title\", \"items\":[{\"id\":\"uuid\",\"topic\":\"Topic\",\"question\":\"content question\",\"options\":[\"opt1\",\"opt2\",\"opt3\",\"opt4\"],\"correctAnswer\":0}]}\n"
                    "Each question must be UNIQUE and test different aspects of the content. "
                    "Use specific details, names, numbers, or concepts from the text. "
                    "No explanations, no extra text, just the JSON."
                )
                ai_text2 = _nvidia_chat([
                    {"role": "system", "content": system_prompt + "\n" + repair_prompt},
                    {"role": "user", "content": source_text[:6000]}
                ], temperature=0.5, max_tokens=1000)
                start2 = ai_text2.find('{')
                end2 = ai_text2.rfind('}')
                if start2 != -1 and end2 != -1 and end2 > start2:
                    snippet2 = ai_text2[start2:end2+1]
                    parsed2 = json.loads(snippet2)
                    items2 = parsed2.get('items') if isinstance(parsed2, dict) else parsed2
                    if isinstance(items2, list) and items2:
                        return jsonify({'status': 'success', 'items': items2, 'provider': 'nvidia'})
            except Exception:
                pass

            # 2) Smarter fallback MCQ generation from key terms and context, plus variety types
            cleaned_text = re.sub(r'\s+', ' ', source_text).strip()
            sentences = _split_sentences(cleaned_text)
            terms = _key_terms(cleaned_text, top_k=20)
            picked_terms = []
            used_questions = set()
            fallback_items = []
            for term in terms:
                if len(fallback_items) >= num_questions:
                    break
                ctx = _best_sentence_for_term(term, sentences)
                # Alternate between MCQ, Fill-in-the-blank, and Short-answer-as-MCQ
                kind = len(fallback_items) % 3
                if kind == 0:
                    mcq = _make_mcq(term, ctx, terms)
                elif kind == 1:
                    # Fill-in-the-blank style turned into MCQ options
                    base = ctx or f"{term.title()} is an important concept in the text."
                    blanked = re.sub(rf"\b{re.escape(term)}\b", "____", base, flags=re.IGNORECASE)
                    if blanked == base or len(blanked) < 30:
                        blanked = f"____ relates to a key concept discussed in the material."
                    correct = term.title()
                    distractors = []
                    for t in terms:
                        if t == term:
                            continue
                        distractors.append(t.title())
                        if len(distractors) >= 3:
                            break
                    while len(distractors) < 3:
                        distractors.append('Context')
                    opts = [correct] + distractors
                    import random
                    random.shuffle(opts)
                    mcq = {
                        'id': str(uuid.uuid4()),
                        'question': f"Fill in the blank: {blanked}",
                        'options': opts,
                        'correctAnswer': opts.index(correct)
                    }
                else:
                    # Short-answer styled but still MCQ for grading
                    stem = f"Briefly, what is {term}? Choose the best answer."
                    correct = ctx if ctx else f"{term.title()} is a core concept described in the text."
                    if len(correct) > 100:
                        correct = correct[:97] + '...'
                    distractors = [
                        f"A tangential note about {terms[1] if len(terms)>1 else 'another topic'}",
                        "A general background statement with no definition",
                        "An example unrelated to the definition"
                    ]
                    opts = [correct] + distractors
                    import random
                    random.shuffle(opts)
                    mcq = {
                        'id': str(uuid.uuid4()),
                        'question': stem,
                        'options': opts,
                        'correctAnswer': opts.index(correct)
                    }
                # de-duplicate by question stem
                key = mcq['question'].lower()
                if key in used_questions:
                    continue
                # enforce 4 unique options and valid correct index
                if not isinstance(mcq.get('options'), list) or len(mcq['options']) != 4 or len(set(mcq['options'])) != 4:
                    continue
                if not isinstance(mcq.get('correctAnswer'), int) or not (0 <= mcq['correctAnswer'] <= 3):
                    continue
                used_questions.add(key)
                fallback_items.append(mcq)

            if not fallback_items:
                # last resort: generic questions from diverse sentences
                for s in sentences[:num_questions]:
                    correct = s if len(s) <= 120 else s[:117] + '...'
                    opts = [correct, 'Paraphrase unrelated to topic', 'Irrelevant detail', 'Contradictory statement']
                    import random
                    random.shuffle(opts)
                    fallback_items.append({
                        'id': str(uuid.uuid4()),
                        'question': 'Which option best captures a main idea from the text?',
                        'options': opts,
                        'correctAnswer': opts.index(correct)
                    })

            return jsonify({'status': 'fallback', 'items': fallback_items})

    except Exception as e:
        print(f"DEBUG: generate_quiz failed with error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-quiz', methods=['POST'])
def submit_quiz():
    try:
        data = request.get_json()
        if not data or 'answers' not in data or 'questions' not in data:
            return jsonify({'error': 'Missing answers or questions data'}), 400
        
        questions = data['questions']
        user_answers = data['answers']
        session_id = str(data.get('sessionId') or 'anonymous')
        quiz_title = data.get('quizTitle', 'Untitled Quiz')
        
        if not isinstance(questions, list) or not isinstance(user_answers, dict):
            return jsonify({'error': 'Invalid data format'}), 400
        
        results = []
        correct_count = 0
        total_questions = len(questions)
        
        # Prepare per-topic counters for this submission
        per_topic_counts = {}
        
        for question in questions:
            question_id = question.get('id')
            correct_answer = question.get('correctAnswer', 0)
            user_answer = user_answers.get(question_id)
            
            # Topic extraction with fallback
            topic = str(question.get('topic') or 'general').strip()
            if topic.lower() == 'general' and quiz_title and quiz_title != 'Untitled Quiz':
                topic = quiz_title
            topic = topic.lower()
            
            is_correct = user_answer == correct_answer
            if is_correct:
                correct_count += 1
            
            results.append({
                'questionId': question_id,
                'question': question.get('question', ''),
                'userAnswer': user_answer,
                'correctAnswer': correct_answer,
                'isCorrect': is_correct,
                'options': question.get('options', []),
                'topic': topic
            })

            # Aggregate per-topic stats for this submission
            t = per_topic_counts.setdefault(topic, {'total': 0, 'correct': 0})
            t['total'] += 1
            if is_correct:
                t['correct'] += 1
        
        score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0

        # Save to database
        user = _get_current_user()
        user_id_to_save = user.id if user else data.get('user_id')
        
        print(f"DEBUG: submit_quiz user={user}, user_id_to_save={user_id_to_save}, headers={request.headers}")
        
        quiz_score_id = None
        # Allow saving if we have a user_id OR if we want to support anonymous sessions (if model allows)
        # Assuming we want to save if we have a user_id (even from body)
        if user_id_to_save:
            try:
                quiz_score = QuizScore(
                    user_id=user_id_to_save,
                    session_id=session_id,
                    quiz_title=quiz_title,
                    total_questions=total_questions,
                    correct_answers=correct_count,
                    score_percentage=round(score_percentage, 1),
                    answers_data=results
                )
                db.session.add(quiz_score)
                if user:
                    _update_user_streak(user)
                db.session.commit()
                quiz_score_id = quiz_score.id
                print(f"DEBUG: Saved QuizScore id={quiz_score_id} for user_id={user_id_to_save}")
            except Exception as db_error:
                db.session.rollback()
                print(f"Database error saving quiz score: {db_error}")
        else:
             # Fallback: Try to save with just session_id if user_id is missing (for anonymous users)
             # This depends on whether user_id is nullable in QuizScore. 
             # Based on previous code "skipping QuizScore DB save due to schema constraint", it implies user_id might be required.
             # But let's try to save with session_id if possible, or just log the warning.
             try:
                quiz_score = QuizScore(
                    user_id=None, # Explicitly None
                    session_id=session_id,
                    quiz_title=quiz_title,
                    total_questions=total_questions,
                    correct_answers=correct_count,
                    score_percentage=round(score_percentage, 1),
                    answers_data=results
                )
                db.session.add(quiz_score)
                db.session.commit()
                quiz_score_id = quiz_score.id
                print(f"DEBUG: Saved anonymous QuizScore id={quiz_score_id} with session_id={session_id}")
             except Exception as db_error:
                db.session.rollback()
                print(f"Database error saving anonymous quiz score (likely user_id required): {db_error}")

        # Update analytics (in-memory for backward compatibility)
        try:
            ANALYTICS['overall']['quizzesSubmitted'] += 1
            ANALYTICS['overall']['questionsAnswered'] += total_questions
            ANALYTICS['overall']['correctAnswers'] += correct_count
            user_stats = ANALYTICS['users'].setdefault(session_id, {
                'quizzesSubmitted': 0,
                'questionsAnswered': 0,
                'correctAnswers': 0,
                'lastScore': 0.0,
                'topics': {}
            })
            user_stats['quizzesSubmitted'] += 1
            user_stats['questionsAnswered'] += total_questions
            user_stats['correctAnswers'] += correct_count
            user_stats['lastScore'] = round(score_percentage, 1)

            # Merge per-topic counts into user_stats
            for topic, cnts in per_topic_counts.items():
                tstats = user_stats['topics'].setdefault(topic, {'total': 0, 'correct': 0})
                tstats['total'] += cnts['total']
                tstats['correct'] += cnts['correct']
        except Exception:
            pass
        
        return jsonify({
            'status': 'success',
            'results': results,
            'score': {
                'correct': correct_count,
                'total': total_questions,
                'percentage': round(score_percentage, 1)
            },
            'sessionId': session_id,
            'quizScoreId': quiz_score_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summarize-transcript', methods=['POST'])
def summarize_transcript():
    try:
        data = request.get_json() or {}
        transcript = str(data.get('transcript') or '').strip()
        max_words = int(data.get('maxWords', 250))
        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400

        result = _summarize_text_with_llm(transcript, max_words=max_words)
        return jsonify({'status': 'success', **result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/overall', methods=['GET'])
def analytics_overall():
    try:
        return jsonify({'status': 'success', **ANALYTICS['overall']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _get_analytics_for_session(session_id):
    # 1. Try to fetch from DB if session_id looks like a user_id
    try:
        user_id = int(session_id)
        scores = QuizScore.query.filter_by(user_id=user_id).all()
        if scores:
            # Filter out dismissed scores
            dismissed = FocusAreaDismissal.query.filter_by(user_id=user_id).all()
            dismissed_ids = {d.quiz_score_id for d in dismissed}
            
            filtered_scores = [s for s in scores if s.id not in dismissed_ids]
            
            # Aggregate stats
            stats = {
                'quizzesSubmitted': len(filtered_scores),
                'questionsAnswered': sum(s.total_questions for s in filtered_scores),
                'correctAnswers': sum(s.correct_answers for s in filtered_scores),
                'lastScore': filtered_scores[-1].score_percentage if filtered_scores else 0,
                'topics': {}
            }
            # Reconstruct topic stats
            for s in filtered_scores:
                if s.answers_data:
                    for q in s.answers_data:
                        topic = str(q.get('topic') or 'general').lower()
                        tstats = stats['topics'].setdefault(topic, {'total': 0, 'correct': 0})
                        tstats['total'] += 1
                        if q.get('isCorrect'):
                            tstats['correct'] += 1
            return stats
    except ValueError:
        pass
    
    # 2. Fallback to in-memory
    return ANALYTICS['users'].get(session_id)




def _get_youtube_video(query):
    """
    Search YouTube for the query and return the top result's details.
    """
    try:
        print(f"DEBUG: Searching YouTube for: {query}", flush=True)
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        print(f"DEBUG: YouTube results: {results}", flush=True)
        
        if results and results.get('result'):
            video = results['result'][0]
            return {
                'link': video.get('link'),
                'title': video.get('title'),
                'thumbnail': video.get('thumbnails')[0]['url'] if video.get('thumbnails') else None,
                'views': video.get('viewCount', {}).get('short')
            }
    except Exception as e:
        print(f"Error searching YouTube for '{query}': {e}")
    return None

def _get_coding_link(title, details):
    """
    Generate a coding practice link based on the step title and details.
    """
    keywords = ['practice', 'coding', 'implement', 'algorithm', 'structure', 'code', 'program', 'function', 'class']
    text = (title + " " + details).lower()
    
    if any(k in text for k in keywords):
        # Construct a search query for LeetCode or similar
        # For simplicity, we'll search LeetCode problems
        query = title.replace(' ', '+')
        return f"https://leetcode.com/problemset/all/?search={query}"
    return None

@app.route('/api/learning-path-plan', methods=['POST'])
def learning_path_plan():
    try:
        data = request.get_json() or {}
        topic = (data.get('topic') or '').strip()
        level = (data.get('level') or 'beginner').strip().lower()
        duration_weeks = int(data.get('durationWeeks', 2))
        if not topic:
            return jsonify({'error': 'Missing topic'}), 400

        prompt = (
            "You are a learning coach. Create a structured step-by-step plan for the given topic. "
            "Return a valid JSON array of objects, where each object represents a step/week. "
            "Format: [{\"step\": 1, \"title\": \"...\", \"details\": \"...\", \"videoQuery\": \"...\"}]. "
            "Do not include any markdown formatting or explanations outside the JSON."
        )
        user = (
            f"Topic: {topic}\nLevel: {level}\nDurationWeeks: {duration_weeks}\n"
            "Constraints: Focus on core concepts, practice, and assessment."
        )
        text = _nvidia_chat([
            {"role": "system", "content": prompt},
            {"role": "user", "content": user}
        ], temperature=0.4, max_tokens=1500)

        # Clean up potential markdown code blocks
        cleaned_text = text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        try:
            plan_data = json.loads(cleaned_text)
        except json.JSONDecodeError:
            # Fallback if JSON fails
            print(f"JSON Decode Error. Raw text: {text}")
            plan_data = [{"step": 1, "title": "Plan Generation Failed", "details": "Could not generate a structured plan. Please try again.", "videoQuery": topic}]
        
        # Enrich plan with YouTube links
        if isinstance(plan_data, list):
            for step in plan_data:
                query = step.get('videoQuery')
                if query:
                    video_info = _get_youtube_video(query)
                    if video_info:
                        step['videoLink'] = video_info['link']
                        step['videoTitle'] = video_info['title']
                        step['videoThumbnail'] = video_info['thumbnail']
                        step['videoViews'] = video_info['views']
                
                # Add coding link if applicable
                step['codingLink'] = _get_coding_link(step.get('title', ''), step.get('details', ''))

        return jsonify({
            'status': 'success',
            'topic': topic,
            'level': level,
            'durationWeeks': duration_weeks,
            'plan': plan_data, # Now a list of objects
            'videoQueries': [p.get('videoQuery') for p in plan_data if p.get('videoQuery')]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/<session_id>', methods=['GET'])
def recommendations(session_id):
    try:
        stats = _get_analytics_for_session(session_id)
        if not stats:
            return jsonify({'status': 'success', 'sessionId': session_id, 'message': 'No history yet', 'recommendations': []})

        topics = stats.get('topics', {})
        recs = []
        strengths = []
        weaknesses = []
        for topic, tstats in topics.items():
            total = max(1, int(tstats.get('total', 0)))
            correct = int(tstats.get('correct', 0))
            acc = round((correct / total) * 100, 1)
            if total >= 5 and acc >= 80:
                strengths.append({'topic': topic, 'accuracy': acc, 'total': total})
            if total >= 3 and acc <= 60:
                weaknesses.append({'topic': topic, 'accuracy': acc, 'total': total})

        # Simple rules for recommendations
        for w in sorted(weaknesses, key=lambda x: (x['accuracy'], -x['total']))[:3]:
            recs.append({
                'topic': w['topic'],
                'action': 'practice_quiz',
                'details': 'Generate a 5-question quiz focusing on fundamentals and common misconceptions.'
            })
        for s in sorted(strengths, key=lambda x: (-x['accuracy'], -x['total']))[:3]:
            recs.append({
                'topic': s['topic'],
                'action': 'advance',
                'details': 'Try intermediate/advanced questions or teach this topic to others.'
            })
        
        if not recs:
            recs.append({'topic': 'General', 'action': 'explore', 'details': 'Take more quizzes to get personalized recommendations.'})

        return jsonify({
            'status': 'success',
            'sessionId': session_id,
            'recommendations': recs,
            'strengths': strengths,
            'weaknesses': weaknesses
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _aggregate_skill_stats(user, session_id: str):
    """
    Aggregate per-topic/skill statistics from persisted QuizScore rows.

    This turns stored quiz answers into a stable backend source of truth
    for the adaptive learning path / skill map, instead of relying only
    on the in-memory ANALYTICS structure.
    """
    query = QuizScore.query
    if user:
        query = query.filter_by(user_id=user.id)
    else:
        # Try to interpret session_id as user_id if it's an integer
        try:
            possible_user_id = int(session_id)
            query = query.filter_by(user_id=possible_user_id)
        except ValueError:
            # fall back to anonymous session-based tracking
            query = query.filter_by(session_id=session_id)

    # Order by created_at so "lastPracticedAt" is meaningful
    scores = query.order_by(QuizScore.created_at.asc()).all()

    # Filter out dismissed topics
    dismissed_ids = set()
    if user:
        dismissed = FocusAreaDismissal.query.filter_by(user_id=user.id).all()
        dismissed_ids = {d.quiz_score_id for d in dismissed}
        print(f"DEBUG: _aggregate_skill_stats user={user.id}, dismissed_ids={dismissed_ids}", flush=True)
    else:
        print(f"DEBUG: _aggregate_skill_stats user=None, session_id={session_id}", flush=True)

    # The scores were already fetched by the 'query' object.
    # We will now iterate and filter them.
    
    print(f"DEBUG: Found {len(scores)} scores. Filtering...", flush=True)

    topics = {}
    overall_questions = 0
    overall_correct = 0

    for score in scores:
        if score.id in dismissed_ids:
            print(f"DEBUG: Skipping dismissed score {score.id}", flush=True)
            continue
        
        answers = score.answers_data or []
        if not isinstance(answers, list):
            continue
        for ans in answers:
            try:
                topic = str((ans.get('topic') or 'general')).strip().lower() or 'general'
            except Exception:
                topic = 'general'

            is_correct = bool(ans.get('isCorrect'))

            overall_questions += 1
            if is_correct:
                overall_correct += 1

            t = topics.setdefault(topic, {
                'questionsAnswered': 0,
                'questionsCorrect': 0,
                'quizCount': 0,
                'lastPracticedAt': None,
            })
            t['questionsAnswered'] += 1
            if is_correct:
                t['questionsCorrect'] += 1
            # Track last practiced timestamp per topic
            ts = score.created_at
            if ts is not None:
                if t['lastPracticedAt'] is None or ts > t['lastPracticedAt']:
                    t['lastPracticedAt'] = ts
            # naive quiz-count heuristic
            t['quizCount'] += 1

    # Convert to skill objects
    skills = []
    for topic, data in topics.items():
        qa = max(1, int(data.get('questionsAnswered') or 0))
        qc = int(data.get('questionsCorrect') or 0)
        mastery = round((qc / qa) * 100, 1)

        last_ts = data.get('lastPracticedAt')
        last_iso = last_ts.isoformat() if last_ts is not None else None

        # Simple banding and recommendation text
        if mastery >= 80:
            band = 'strong'
            rec = 'Move to advanced problems and real-world applications for this skill.'
        elif mastery >= 60:
            band = 'medium'
            rec = 'Do a balanced mix of review and new practice questions.'
        else:
            band = 'weak'
            rec = 'Revisit fundamentals and attempt a focused practice quiz on this topic.'

        skills.append({
            'id': topic,
            'name': topic.title(),
            'category': 'general',
            'masteryScore': mastery,
            'questionsAnswered': qa,
            'questionsCorrect': qc,
            'quizCount': int(data.get('quizCount') or 0),
            'lastPracticedAt': last_iso,
            'strengthBand': band,
            'recommendedNext': rec,
        })

    # Sort skills: weakest first, then by volume
    skills.sort(key=lambda s: (s['masteryScore'], -s['questionsAnswered']))

    overall_mastery = round((overall_correct / max(1, overall_questions)) * 100, 1)

    return {
        'skills': skills,
        'overall': {
            'questionsAnswered': overall_questions,
            'questionsCorrect': overall_correct,
            'masteryScore': overall_mastery,
        }
    }


@app.route('/api/learning-path/skills/<session_id>', methods=['GET'])
def learning_path_skills(session_id):
    """
    Return per-skill/topic mastery for use in the LearningPath UI.

    This endpoint is the backend source for the adaptive skill map:
    it analyzes all stored QuizScore rows for the current user or
    anonymous session and returns normalized skill objects.
    """
    try:
        user = _get_current_user()
        stats = _aggregate_skill_stats(user, session_id)

        return jsonify({
            'status': 'success',
            'sessionId': session_id,
            **stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.route('/api/learning-path/dismiss-topic', methods=['POST'])
def dismiss_topic():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    topic = data.get('topic')
    if not topic:
        return jsonify({'error': 'Topic required'}), 400
        
    # Find all scores for this topic and dismiss them
    scores = QuizScore.query.filter_by(user_id=user.id).all()
    count = 0
    print(f"DEBUG: dismiss_topic request for '{topic}' by user {user.id}. Found {len(scores)} total scores.", flush=True)
    
    for score in scores:
        answers = score.answers_data or []
        if not isinstance(answers, list): continue
        
        score_topic = 'general'
        if answers:
            # simple heuristic: take first answer's topic
            score_topic = str((answers[0].get('topic') or 'general')).strip().lower()
        
        print(f"DEBUG: Checking score {score.id} with topic '{score_topic}' against target '{topic.strip().lower()}'", flush=True)
            
        if score_topic == topic.strip().lower():
            # Check if already dismissed
            existing = FocusAreaDismissal.query.filter_by(user_id=user.id, quiz_score_id=score.id).first()
            if not existing:
                db.session.add(FocusAreaDismissal(user_id=user.id, quiz_score_id=score.id))
                count += 1
                print(f"DEBUG: Dismissing score {score.id}", flush=True)
                
    db.session.commit()
    print(f"DEBUG: Dismissed {count} scores.", flush=True)
    return jsonify({'message': f'Dismissed {count} scores for topic {topic}'})

@app.route('/api/learning-path/reset', methods=['POST'])
def reset_progress():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    # Delete all QuizScores for this user
    try:
        QuizScore.query.filter_by(user_id=user.id).delete()
        FocusAreaDismissal.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return jsonify({'message': 'Progress reset successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/tts', methods=['POST'])
def tts_generate():
    try:
        # Accept JSON or form-data
        text = None
        lang = 'en'
        slow = False

        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json() or {}
            text = (data.get('text') or '').strip()
            lang = (data.get('lang') or 'en').strip() or 'en'
            slow = bool(data.get('slow', False))
        else:
            text = (request.form.get('text') or '').strip()
            lang = (request.form.get('lang') or 'en').strip() or 'en'
            slow = (request.form.get('slow') or 'false').lower() == 'true'

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Generate MP3 to memory buffer
        tts = gTTS(text=text, lang=lang, slow=slow)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)

        # Use a deterministic filename hint for download
        filename = 'speech.mp3'
        return send_file(buffer, mimetype='audio/mpeg', as_attachment=False, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Chat History Endpoints
@app.route('/api/chat/save', methods=['POST'])
def save_chat_history():
    """Save a chat message and AI response to the database"""
    try:
        data = request.get_json() or {}
        user_message = data.get('user_message', '').strip()
        ai_response = data.get('ai_response', '').strip()
        context = data.get('context', 'general').strip()  # e.g., 'quiz_generator', 'voice_qa'
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not user_message or not ai_response:
            return jsonify({'error': 'user_message and ai_response are required'}), 400
        
        user = _get_current_user()
        user_id = user.id if user else None
        
        chat_entry = ChatHistory(
            user_id=user_id,
            session_id=session_id if not user_id else None,
            user_message=user_message,
            ai_response=ai_response,
            context=context
        )
        
        try:
            db.session.add(chat_entry)
            db.session.commit()
            return jsonify({
                'status': 'success',
                'id': chat_entry.id,
                'message': 'Chat history saved successfully'
            })
        except Exception as db_error:
            db.session.rollback()
            return jsonify({'error': f'Failed to save chat history: {str(db_error)}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """Retrieve chat history for the current user or session"""
    try:
        user = _get_current_user()
        session_id = request.args.get('session_id')
        context = request.args.get('context')  # Optional filter by context
        limit = int(request.args.get('limit', 50))
        
        query = ChatHistory.query
        
        if user:
            query = query.filter_by(user_id=user.id)
        elif session_id:
            query = query.filter_by(session_id=session_id)
        else:
            return jsonify({'error': 'User authentication or session_id required'}), 401
        
        if context:
            query = query.filter_by(context=context)
        
        chat_history = query.order_by(ChatHistory.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'status': 'success',
            'count': len(chat_history),
            'history': [entry.to_dict() for entry in chat_history]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quiz/scores', methods=['GET'])
def get_quiz_scores():
    """Retrieve quiz scores for the current user or session"""
    try:
        user = _get_current_user()
        session_id = request.args.get('session_id')
        limit = int(request.args.get('limit', 50))
        
        query = QuizScore.query
        
        if user:
            query = query.filter_by(user_id=user.id)
        elif session_id:
            query = query.filter_by(session_id=session_id)
        else:
            return jsonify({'error': 'User authentication or session_id required'}), 401
        
        scores = query.order_by(QuizScore.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'status': 'success',
            'count': len(scores),
            'scores': [score.to_dict() for score in scores]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Analytics Endpoints ---

@app.route('/api/analytics/dashboard', methods=['GET'])
def analytics_dashboard():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # 1. Calculate total quizzes and average score
    scores = QuizScore.query.filter_by(user_id=user.id).all()
    total_quizzes = len(scores)
    
    if total_quizzes == 0:
        return jsonify({
            'total_quizzes': 0,
            'average_score': 0,
            'recent_activity': [],
            'weak_areas': []
        })

    avg_score = sum(s.score_percentage for s in scores) / total_quizzes
    
    # 2. Recent activity (last 10 quizzes)
    recent_scores = QuizScore.query.filter_by(user_id=user.id)\
        .order_by(QuizScore.created_at.desc())\
        .limit(10).all()
    
    recent_activity = []
    for s in reversed(recent_scores): # Show oldest to newest in chart
        recent_activity.append({
            'date': s.created_at.strftime('%Y-%m-%d'),
            'score': s.score_percentage
        })

    # 3. Identify weak areas (score < 60%) excluding dismissed ones
    # Get dismissed IDs
    dismissed = FocusAreaDismissal.query.filter_by(user_id=user.id).all()
    dismissed_ids = set(d.quiz_score_id for d in dismissed)
    
    weak_areas = []
    # We'll look at the last 20 quizzes to find weak areas
    recent_20 = QuizScore.query.filter_by(user_id=user.id)\
        .order_by(QuizScore.created_at.desc())\
        .limit(20).all()
        
    for s in recent_20:
        if s.score_percentage < 60 and s.id not in dismissed_ids:
            weak_areas.append({
                'id': s.id,
                'title': s.quiz_title or 'Untitled Quiz',
                'date': s.created_at.strftime('%Y-%m-%d'),
                'score': s.score_percentage,
                # For now, we don't have a direct video link in QuizScore, 
                # but we could add logic to suggest one based on the title.
                # Leaving it null or adding a placeholder if needed.
                'video_suggestion_url': None 
            })
            
    # 4. Get Streak Data
    current_streak = user.current_streak or 0
    max_streak = user.max_streak or 0
    
    # Check if streak is broken (i.e. last activity was before yesterday)
    # But strictly speaking, today's activity might not have happened yet.
    # If last_activity_date < yesterday, streak is effectively 0 for display until they do something today?
    # Or we display the stored streak?
    # Usually apps display the streak from yesterday if today hasn't happened yet, but if they miss today it resets tomorrow.
    # Let's just return what's in DB. The update logic handles the reset.

    return jsonify({
        'total_quizzes': total_quizzes,
        'average_score': round(avg_score, 1),
        'recent_activity': recent_activity,
        'weak_areas': weak_areas,
        'streak': {
            'current': current_streak,
            'max': max_streak,
            'last_activity': user.last_activity_date.isoformat() if user.last_activity_date else None
        }
    })

def _update_user_streak(user):
    """
    Updates the user's streak based on activity (called when they do something significant).
    """
    now = datetime.utcnow().date()
    # last_activity_date is db.Date, so it's already a date object (or None)
    last = user.last_activity_date 
    
    if last == now:
        return # Already counted for today
        
    if last == now - timedelta(days=1):
        # Consecutive day
        user.current_streak = (user.current_streak or 0) + 1
    else:
        # Broken streak or first time
        user.current_streak = 1
        
    # Update max
    if (user.current_streak or 0) > (user.max_streak or 0):
        user.max_streak = user.current_streak
        
    user.last_activity_date = now # Assign date object, not datetime
    db.session.commit()

@app.route('/api/analytics/focus-area/<int:id>', methods=['DELETE'])
def delete_focus_area(id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    # Verify the quiz score belongs to the user
    score = QuizScore.query.get(id)
    if not score or score.user_id != user.id:
        return jsonify({'error': 'Focus area not found'}), 404
        
    # Check if already dismissed
    existing = FocusAreaDismissal.query.filter_by(user_id=user.id, quiz_score_id=id).first()
    if existing:
        return jsonify({'message': 'Already dismissed'})
        
    dismissal = FocusAreaDismissal(user_id=user.id, quiz_score_id=id)
    db.session.add(dismissal)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Focus area dismissed'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/learning-path/save', methods=['POST'])
def save_learning_path():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        topic = data.get('topic')
        level = data.get('level')
        plan = data.get('plan')
        
        if not topic or not plan:
            return jsonify({'error': 'Missing data'}), 400
            
        # Create LearningPath
        lp = LearningPath(
            user_id=user.id,
            topic=topic,
            level=level,
            total_steps=len(plan),
            completed_steps=0
        )
        db.session.add(lp)
        db.session.flush() # Get ID
        
        # Create Steps
        for step in plan:
            s = LearningPathStep(
                learning_path_id=lp.id,
                step_number=step.get('step'),
                title=step.get('title'),
                details=step.get('details'),
                video_query=step.get('videoQuery'),
                video_link=step.get('videoLink'),
                video_title=step.get('videoTitle'),
                video_thumbnail=step.get('videoThumbnail'),
                video_views=step.get('videoViews'),
                coding_link=step.get('codingLink')
            )
            db.session.add(s)
            
        db.session.commit()
        return jsonify({'status': 'success', 'id': lp.id, 'message': 'Learning path saved'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/learning-paths', methods=['GET'])
def get_learning_paths():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        paths = LearningPath.query.filter_by(user_id=user.id).order_by(LearningPath.created_at.desc()).all()
        return jsonify({
            'status': 'success',
            'paths': [p.to_dict() for p in paths]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/learning-path/<int:path_id>', methods=['GET'])
def get_learning_path_details(path_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        lp = LearningPath.query.filter_by(id=path_id, user_id=user.id).first()
        if not lp:
            return jsonify({'error': 'Not found'}), 404
            
        steps = LearningPathStep.query.filter_by(learning_path_id=lp.id).order_by(LearningPathStep.step_number.asc()).all()
        
        data = lp.to_dict()
        data['steps'] = [s.to_dict() for s in steps]
        
        return jsonify({'status': 'success', 'path': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/learning-path/step/<int:step_id>/toggle', methods=['POST'])
def toggle_step_progress(step_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        step = LearningPathStep.query.join(LearningPath).filter(
            LearningPathStep.id == step_id,
            LearningPath.user_id == user.id
        ).first()
        
        if not step:
            return jsonify({'error': 'Not found'}), 404
            
        step.is_completed = not step.is_completed
        
        # Update parent progress
        lp = step.learning_path
        completed_count = LearningPathStep.query.filter_by(learning_path_id=lp.id, is_completed=True).count()
        lp.completed_steps = completed_count
        
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'is_completed': step.is_completed,
            'video_watched': step.video_watched,
            'code_practiced': step.code_practiced,
            'path_progress': lp.to_dict()['progress']
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/learning-path/<int:path_id>', methods=['DELETE'])
def delete_learning_path(path_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        lp = LearningPath.query.filter_by(id=path_id, user_id=user.id).first()
        if not lp:
            return jsonify({'error': 'Not found'}), 404
            
        db.session.delete(lp)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# --- Feynman Mode Endpoints ---

@app.route('/api/feynman/start', methods=['POST'])
def start_feynman_session():
    print("DEBUG: start_feynman_session hit", flush=True)
    try:
        user = _get_current_user()
        print(f"DEBUG: User retrieved: {user}", flush=True)
        if not user:
            print("DEBUG: No user found, returning 401", flush=True)
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json()
        print(f"DEBUG: Request data: {data}", flush=True)
        topic = data.get('topic')
        persona = data.get('persona', 'Curious 5-Year-Old')

        if not topic:
            print("DEBUG: No topic provided", flush=True)
            return jsonify({'error': 'Topic is required'}), 400

        session_id = str(uuid.uuid4())
        title = f"Teaching: {topic} ({persona})"
        
        print(f"DEBUG: Creating session {session_id}", flush=True)
        session = ChatSession(
            id=session_id,
            user_id=user.id,
            title=title,
            mode='feynman'
        )
        db.session.add(session)
        print("DEBUG: Session added to db session", flush=True)
        
        db.session.commit()
        print("DEBUG: Database commit successful", flush=True)
        
        greeting = f"I'm ready to learn about {topic}! I'm a {persona}, so please explain it simply."
        
        # Save greeting to history
        init_msg = ChatHistory(
            session_id=session_id,
            user_id=user.id,
            user_message=f"I want to teach you about {topic}.",
            ai_response=greeting,
            context='feynman'
        )
        db.session.add(init_msg)
        db.session.commit()
        print("DEBUG: Greeting saved to history", flush=True)
        
        return jsonify({
            'session_id': session_id,
            'title': title,
            'greeting': greeting
        })
    except Exception as e:
        print(f"ERROR in start_feynman_session: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/feynman/chat', methods=['POST'])
def feynman_chat():
    print("DEBUG: feynman_chat hit", flush=True)
    try:
        user = _get_current_user()
        if not user:
            print("DEBUG: Unauthorized in chat", flush=True)
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json()
        session_id = data.get('session_id')
        user_message = data.get('message')
        topic = data.get('topic')
        persona = data.get('persona')
        
        print(f"DEBUG: Chat request for session {session_id}", flush=True)

        if not session_id or not user_message:
            return jsonify({'error': 'Missing session_id or message'}), 400

        # Fetch chat history
        # Ensure ChatHistory is imported or available
        print("DEBUG: Fetching history", flush=True)
        history = ChatHistory.query.filter_by(session_id=session_id).order_by(ChatHistory.created_at.asc()).all()
        
        messages = []
        # System Prompt
        messages.append({
            "role": "system", 
            "content": f"You are a {persona}. The user is teaching you about {topic}. "
                       f"You know NOTHING about the topic beforehand. "
                       f"Only ask questions based on what the user explicitly said. "
                       f"Do not introduce new terms or concepts unless the user mentioned them. "
                       f"If the explanation is vague, ask for clarification on the words used."
        })
        
        for h in history:
            messages.append({"role": "user", "content": h.user_message})
            messages.append({"role": "assistant", "content": h.ai_response})
        
        messages.append({"role": "user", "content": user_message})

        print("DEBUG: Calling LLM", flush=True)
        ai_text = _nvidia_chat(messages, temperature=0.7, max_tokens=300)
        print("DEBUG: LLM response received", flush=True)

        # Save to history
        chat_entry = ChatHistory(
            session_id=session_id,
            user_id=user.id,
            user_message=user_message,
            ai_response=ai_text,
            context='feynman'
        )
        db.session.add(chat_entry)
        db.session.commit()
        print("DEBUG: Chat saved", flush=True)

        return jsonify({'response': ai_text})

    except Exception as e:
        print(f"Error in feynman chat: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/feynman/evaluate', methods=['POST'])
def evaluate_feynman_session():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    session_id = data.get('session_id')
    topic = data.get('topic')
    persona = data.get('persona')

    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400

    history = ChatHistory.query.filter_by(session_id=session_id).order_by(ChatHistory.created_at.asc()).all()
    
    if not history:
        return jsonify({'error': 'No history to evaluate'}), 400

    transcript = ""
    for h in history:
        transcript += f"User: {h.user_message}\\nAI ({persona}): {h.ai_response}\\n"

    evaluation_prompt = f"""
    Analyze the following teaching session where a user tried to teach '{topic}' to a '{persona}'.
    
    Transcript:
    {transcript}
    
    Evaluate the user on:
    1. Clarity (0-100)
    2. Depth of Understanding (0-100)
    3. Overall Mastery Score (0-100)
    
    Provide constructive feedback on what they explained well and what they missed.
    
    Return valid JSON ONLY. No markdown. No explanations.
    Format:
    {{
        "clarity_score": <number 0-100>,
        "depth_score": <number 0-100>,
        "overall_score": <number 0-100>,
        "feedback": "<string>"
    }}
    """

    try:
        print("DEBUG: Calling LLM for evaluation", flush=True)
        eval_text = _nvidia_chat(
            [{"role": "user", "content": evaluation_prompt}],
            temperature=0.2,
            max_tokens=500
        )
        print(f"DEBUG: Eval response: {eval_text}", flush=True)
        
        # Parse JSON from response
        import json
        import re
        try:
            # Remove markdown code blocks if present
            clean_text = re.sub(r'```json\s*|\s*```', '', eval_text).strip()
            
            # Try to find JSON block if there's extra text
            start = clean_text.find('{')
            end = clean_text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = clean_text[start:end]
                eval_data = json.loads(json_str)
            else:
                # If no braces found, try loading the whole string
                eval_data = json.loads(clean_text)
        except Exception as parse_err:
            print(f"ERROR parsing eval JSON: {parse_err}", flush=True)
            # Fallback: try to extract numbers using regex if JSON fails
            clarity = re.search(r'clarity_score"?\s*:\s*(\d+)', eval_text)
            depth = re.search(r'depth_score"?\s*:\s*(\d+)', eval_text)
            overall = re.search(r'overall_score"?\s*:\s*(\d+)', eval_text)
            
            eval_data = {
                "clarity_score": int(clarity.group(1)) if clarity else 0,
                "depth_score": int(depth.group(1)) if depth else 0,
                "overall_score": int(overall.group(1)) if overall else 0,
                "feedback": "Could not parse detailed feedback. " + eval_text[:100] + "..."
            }

        # Save Score
        score_entry = FeynmanScore(
            user_id=user.id,
            session_id=session_id,
            topic=topic,
            persona=persona,
            score=eval_data.get('overall_score', 0),
            clarity_score=eval_data.get('clarity_score', 0),
            depth_score=eval_data.get('depth_score', 0),
            feedback=eval_data.get('feedback', '')
        )
        db.session.add(score_entry)
        db.session.commit()
        
        return jsonify(score_entry.to_dict())

    except Exception as e:
        print(f"Error evaluating session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/user/<user_id>', methods=['GET'])
def analytics_user(user_id):
    try:
        user = _get_current_user()
        # If user_id is passed in URL, we might want to verify it matches current user or allow admin access
        # For now, we'll use the logic in _aggregate_skill_stats which handles user/session lookup
        stats = _aggregate_skill_stats(user, user_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/<user_id>', methods=['GET'])
def recommendations_user(user_id):
    try:
        user = _get_current_user()
        stats = _aggregate_skill_stats(user, user_id)
        
        # Extract strengths and weaknesses
        skills = stats.get('skills', [])
        strengths = [s for s in skills if s['strengthBand'] == 'strong']
        weaknesses = [s for s in skills if s['strengthBand'] == 'weak']
        
        # Generate recommendations based on weaknesses
        recs = []
        for w in weaknesses[:3]:
            recs.append({
                'topic': w['topic'],
                'action': 'Review core concepts',
                'details': f"Your mastery is {w['masteryScore']}%. Try more practice quizzes."
            })
            
        if not recs and skills:
             # If no weaknesses, recommend advancing in strongest areas
            for s in skills[:3]:
                recs.append({
                    'topic': s['topic'],
                    'action': 'Advance to next level',
                    'details': f"You are doing great in {s['topic']}! Try advanced topics."
                })

        return jsonify({
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': recs
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/learning-path-plan', methods=['POST'])
def generate_learning_path_plan():
    print("DEBUG: generate_learning_path_plan hit", flush=True)
    try:
        data = request.get_json()
        topic = data.get('topic')
        level = data.get('level')
        duration_weeks = data.get('durationWeeks', 2)
        
        if not topic or not level:
            return jsonify({'error': 'Topic and level are required'}), 400
            
        prompt = (
            f"Create a detailed {duration_weeks}-week learning path for '{topic}' at {level} level. "
            "Return a JSON object with a 'plan' key containing a list of steps. "
            "Each step should have: 'step' (number), 'title', 'details', 'videoQuery' (search query for video), 'codingLink' (optional). "
            "Do not include any markdown formatting, just raw JSON."
        )
        
        response_text = _nvidia_chat([{"role": "user", "content": prompt}], temperature=0.7, max_tokens=2000)
        
        # Clean up response if it contains markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        plan_data = json.loads(response_text)
        
        # Add video queries and fetch video details
        for step in plan_data.get('plan', []):
            if 'videoQuery' not in step:
                step['videoQuery'] = f"{topic} {step['title']} tutorial"
            
            # Fetch video details
            video_details = _get_youtube_video(step['videoQuery'])
            if video_details:
                step['videoLink'] = video_details.get('link')
                step['videoTitle'] = video_details.get('title')
                step['videoThumbnail'] = video_details.get('thumbnail')
                step['videoViews'] = video_details.get('views')
                
        return jsonify({
            'topic': topic,
            'level': level,
            'plan': plan_data.get('plan', []),
            'videoQueries': [s['videoQuery'] for s in plan_data.get('plan', [])][:5]
        })
        
    except Exception as e:
        print(f"Error generating plan: {e}")
        return jsonify({'error': str(e)}), 500








# --- Community Endpoints ---

@app.route('/api/community/topics', methods=['GET'])
def get_community_topics():
    try:
        topics = CommunityTopic.query.order_by(CommunityTopic.created_at.desc()).all()
        return jsonify({
            'status': 'success',
            'topics': [t.to_dict() for t in topics]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/community/topics', methods=['POST'])
def create_community_topic():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    
    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400
        
    try:
        topic = CommunityTopic(
            user_id=user.id,
            title=title,
            content=content
        )
        db.session.add(topic)
        _update_user_streak(user)
        db.session.commit()
        return jsonify({'status': 'success', 'topic': topic.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/community/topics/<int:topic_id>', methods=['GET'])
def get_community_topic_details(topic_id):
    try:
        topic = CommunityTopic.query.get(topic_id)
        if not topic:
            return jsonify({'error': 'Topic not found'}), 404
            
        topic_data = topic.to_dict()
        # Include comments
        topic_data['comments'] = [c.to_dict() for c in topic.comments]
        return jsonify(topic_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/community/topics/<int:topic_id>/comments', methods=['POST'])
def add_community_comment(topic_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    content = (data.get('content') or '').strip()
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
        
    try:
        topic = CommunityTopic.query.get(topic_id)
        if not topic:
            return jsonify({'error': 'Topic not found'}), 404
            
        comment = CommunityComment(
            topic_id=topic.id,
            user_id=user.id,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        return jsonify({'status': 'success', 'comment': comment.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/community/topics/<int:topic_id>/like', methods=['POST'])
def like_community_topic(topic_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        topic = CommunityTopic.query.get(topic_id)
        if not topic:
            return jsonify({'error': 'Topic not found'}), 404
            
        # Simple like increment for now (user can like multiple times? Maybe restriction needed in future)
        # Ideally we'd have a Likes table to prevent dupes. For now just increment.
        topic.likes += 1
        db.session.commit()
        return jsonify({'status': 'success', 'likes': topic.likes})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@app.route('/api/community/topics/<int:topic_id>', methods=['DELETE'])
def delete_community_topic(topic_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        topic = CommunityTopic.query.get(topic_id)
        if not topic:
            return jsonify({'error': 'Topic not found'}), 404
            
        if topic.user_id != user.id:
            return jsonify({'error': 'You can only delete your own topics'}), 403
            
        db.session.delete(topic)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Topic deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@app.route('/api/learning-path/step/<int:step_id>/action', methods=['POST'])
def toggle_step_action(step_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        action = data.get('action') # 'video', 'code', 'complete'
        
        step = LearningPathStep.query.get(step_id)
        if not step:
            return jsonify({'error': 'Step not found'}), 404
            
        # Verify ownership via path
        path = LearningPath.query.get(step.learning_path_id)
        if path.user_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        if action == 'video':
            step.video_watched = not step.video_watched
        elif action == 'code':
            step.code_practiced = not step.code_practiced
        elif action == 'complete':
             step.is_completed = not step.is_completed
             if step.is_completed:
                 step.video_watched = True
                 if step.coding_link:
                     step.code_practiced = True
        
        # Check auto-complete
        has_video = bool(step.video_link)
        has_code = bool(step.coding_link)
        
        is_video_done = not has_video or step.video_watched
        is_code_done = not has_code or step.code_practiced
        
        if is_video_done and is_code_done:
             step.is_completed = True
        elif action != 'complete':
             # If we toggled a subtask off and it wasn't a 'complete' action, we might need to uncomplete
             if step.is_completed:
                 step.is_completed = False

        db.session.commit()
        
        # Update path progress
        total = len(path.steps)
        completed = sum(1 for s in path.steps if s.is_completed)
        path.completed_steps = completed
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'step': step.to_dict(),
            'path_progress': path.to_dict()['progress']
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

