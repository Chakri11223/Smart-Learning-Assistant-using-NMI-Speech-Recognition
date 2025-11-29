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
from fpdf import FPDF
import pdfplumber
from typing import List
import shutil
import subprocess
from gtts import gTTS
import re
from collections import Counter, defaultdict
import time
import random
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import db, User, QuizScore, ChatHistory

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
    if not sent:
        print(f"Verification code for {email}: {code}")
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
    source_text = (source_text or '').strip()
    if not source_text:
        raise ValueError('Empty transcript')

    chunks = _chunk_text_by_chars(source_text, 3500)
    partial_summaries: List[str] = []

    # Per-chunk prompt
    per_prompt = (
        "Summarize the following transcript segment for a student audience. "
        "Return ONLY well-formed paragraphs (no bullet points, no lists)."
    )

    for segment in chunks or [source_text]:
        try:
            text = _nvidia_chat([
                {"role": "system", "content": per_prompt},
                {"role": "user", "content": segment[:6000]}
            ], temperature=0.3, max_tokens=500)
            partial_summaries.append(text.strip())
        except Exception as e:
            # If LLM unavailable, collect raw truncated text as a fallback
            partial_summaries.append(segment[:500].strip())

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
                        import yt_dlp  # type: ignore
                        ydl_opts = {
                            'quiet': True,
                            'no_warnings': True,
                            'skip_download': True,
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
                            # picked is a list of dicts with 'url' and 'ext'
                            vtt = next((e for e in picked if e.get('ext') == 'vtt' and e.get('url')), None)
                            sub_entry = vtt or (picked[0] if picked else None)
                            if sub_entry and sub_entry.get('url'):
                                sub_url = sub_entry['url']
                            if sub_url:
                                resp = requests.get(sub_url, timeout=20)
                                raw = resp.text
                                # Parse WEBVTT into segments with timestamps
                                segments = []
                                current_times = None
                                for line in raw.splitlines():
                                    l = line.strip()
                                    if not l:
                                        continue
                                    if l.startswith('WEBVTT') or re.match(r'^\d+$', l):
                                        continue
                                    if '-->' in l:
                                        current_times = l
                                        continue
                                    # text line
                                    if current_times:
                                        try:
                                            start = current_times.split('-->')[0].strip()
                                            # convert HH:MM:SS.mmm to seconds
                                            def _to_secs(ts):
                                                parts = ts.split(':')
                                                h, m = int(parts[-3]), int(parts[-2])
                                                s = float(parts[-1].replace(',', '.'))
                                                return h*3600 + m*60 + s
                                            start_s = _to_secs(start)
                                        except Exception:
                                            start_s = 0.0
                                        segments.append({'start': round(start_s, 2), 'text': l})
                                        current_times = None
                                captions_text = re.sub(r'\s+', ' ', ' '.join(seg['text'] for seg in segments)).strip()
                                # Derive simple chapters by gaps between segment starts (> 60s) or every ~90s
                                chapters = []
                                last_cut = 0.0
                                buf = []
                                for seg in segments:
                                    if not buf:
                                        buf.append(seg)
                                        last_cut = seg['start']
                                        continue
                                    if seg['start'] - last_cut >= 90.0 or len(buf) >= 12:
                                        chap_text = ' '.join(b['text'] for b in buf)
                                        chapters.append({'start': buf[0]['start'], 'text': chap_text[:400]})
                                        buf = [seg]
                                        last_cut = seg['start']
                                    else:
                                        buf.append(seg)
                                if buf:
                                    chap_text = ' '.join(b['text'] for b in buf)
                                    chapters.append({'start': buf[0]['start'], 'text': chap_text[:400]})
                        if captions_text:
                            transcript = captions_text
                            result = _summarize_text_with_llm(transcript, max_words=max_words)
                            result.update({
                                'status': 'success',
                                'source': 'youtube_captions',
                                'video_id': video_id,
                                'url': url,
                                'segments': segments[:200],
                                'chapters': chapters[:20]
                            })
                            return jsonify(result)
                    except Exception as cap_err:
                        print(f"yt-dlp captions fetch failed: {cap_err}")

                    # Fallback: attempt audio download and local transcription (if Whisper available)
                    try:
                        import yt_dlp  # type: ignore
                        tmp_dir = tempfile.mkdtemp(prefix='yt_')
                        ydl_opts_dl = {
                            'quiet': True,
                            'no_warnings': True,
                            'format': 'bestaudio/best',
                            'paths': {'home': tmp_dir},
                            'outtmpl': '%(id)s.%(ext)s'
                        }
                        audio_path = None
                        with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                            info2 = ydl.extract_info(url, download=True)
                            # Try to locate downloaded file
                            # Newer yt-dlp may expose 'requested_downloads'
                            req = (info2.get('requested_downloads') or [])
                            if req and req[0].get('filepath'):
                                audio_path = req[0]['filepath']
                            else:
                                audio_path = info2.get('filepath') or None
                            if not audio_path:
                                # fallback: search tmp_dir
                                for root, _, files in os.walk(tmp_dir):
                                    for f in files:
                                        if f.startswith(video_id):
                                            audio_path = os.path.join(root, f)
                                            break
                                    if audio_path:
                                        break
                        transcript = None
                        wav_path = None
                        if audio_path and os.path.exists(audio_path):
                            try:
                                wav_path = _extract_audio_wav(audio_path)
                                transcript = _transcribe_wav(wav_path)
                            finally:
                                _safe_remove(wav_path)
                                _safe_remove(audio_path)
                                try:
                                    shutil.rmtree(tmp_dir, ignore_errors=True)
                                except Exception:
                                    pass
                        if transcript:
                            result = _summarize_text_with_llm(transcript, max_words=max_words)
                            result.update({
                                'status': 'success',
                                'source': 'youtube_audio_transcription',
                                'video_id': video_id,
                                'url': url
                            })
                            return jsonify(result)
                    except Exception as dl_err:
                        print(f"yt-dlp audio download/transcription failed: {dl_err}")

                    # Last resort: guidance message
                    transcript = (
                        f"This is a YouTube video (ID: {video_id}). "
                        "Captions were unavailable or could not be fetched automatically.\n\n"
                        "Please use the 'Upload Video' tab to upload the file, or paste the transcript in the 'Paste Transcript' tab."
                    )
                    result = _summarize_text_with_llm(transcript, max_words=max_words)
                    result.update({
                        'status': 'success', 
                        'warnings': ['youtube_fetch_limited'],
                        'video_id': video_id,
                        'url': url
                    })
                    return jsonify(result)
                else:
                    return jsonify({'error': 'Could not extract YouTube video ID from URL'}), 400
                    
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
            
            result = _summarize_text_with_llm(transcript, max_words=max_words)
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
        # Check if it's a text question or audio file
        want_tts = False
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Audio file upload
            if 'audio' not in request.files:
                return jsonify({'error': 'No audio file provided'}), 400
            
            audio_file = request.files['audio']
            want_tts = (request.form.get('tts') or 'false').lower() == 'true'
            
            # Save audio file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                audio_file.save(temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                # For now, we'll use a simple fallback for speech-to-text
                question = "What is artificial intelligence and how does it work?"
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
        
        # Use NVIDIA API for AI responses
        try:
            print(f"Attempting NVIDIA chat. Base={NVIDIA_API_BASE}, Model={NVIDIA_MODEL}")
            print(f"Key present: {bool(NVIDIA_API_KEY)}")
            answer = _nvidia_chat([
                {"role": "user", "content": question}
            ], max_tokens=1500)
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
            "OUTPUT STRICT JSON ONLY: {\"items\":[{\"id\":\"uuid\",\"question\":\"...\",\"options\":[\"...\",\"...\",\"...\",\"...\"],\"correctAnswer\":0}]}\n"
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
            if start != -1 and end != -1 and end > start:
                snippet = ai_text[start:end+1]
                try:
                    parsed = json.loads(snippet)
                    items = parsed.get('items') if isinstance(parsed, dict) else parsed
                except Exception:
                    items = []

            if not items or not isinstance(items, list):
                raise RuntimeError('Model did not return valid JSON items')

            # Normalize and ensure IDs exist; enforce exactly 4 options and 1 correct
            normalized = []
            for it in items:
                q = str(it.get('question', '')).strip()
                options = it.get('options', [])
                correct_answer = it.get('correctAnswer', 0)
                
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
                    'correctAnswer': correct_answer
                })

            if not normalized:
                raise RuntimeError('No valid items after normalization')

            return jsonify({'status': 'success', 'items': normalized, 'provider': 'nvidia'})

        except Exception as e:
            # 1) LLM JSON repair retry with stricter instruction
            try:
                repair_prompt = (
                    "CRITICAL: Return ONLY valid JSON in this exact format: "
                    "{\"items\":[{\"id\":\"uuid\",\"question\":\"specific content question\",\"options\":[\"option1\",\"option2\",\"option3\",\"option4\"],\"correctAnswer\":0}]}\n"
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
                    opts = [correct] + distractors[:3]
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
            topic = str(question.get('topic') or 'general').strip().lower() or 'general'
            
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
        user_id = user.id if user else None
        
        quiz_score = QuizScore(
            user_id=user_id,
            session_id=session_id if not user_id else None,
            quiz_title=quiz_title,
            total_questions=total_questions,
            correct_answers=correct_count,
            score_percentage=round(score_percentage, 1),
            answers_data=results
        )
        
        try:
            db.session.add(quiz_score)
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            print(f"Database error saving quiz score: {db_error}")

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
            'quizScoreId': quiz_score.id
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

@app.route('/api/analytics/user/<session_id>', methods=['GET'])
def analytics_user(session_id):
    try:
        stats = ANALYTICS['users'].get(session_id)
        if not stats:
            return jsonify({'status': 'success', 'message': 'No data for user', 'sessionId': session_id})
        return jsonify({'status': 'success', 'sessionId': session_id, **stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
            "You are a learning coach. Create a step-by-step plan for the given topic. "
            "Return ONLY paragraphs with numbered steps inline (e.g., 'Step 1: ...'). "
            "No bullet characters. Include suggested video search queries for each step."
        )
        user = (
            f"Topic: {topic}\nLevel: {level}\nDurationWeeks: {duration_weeks}\n"
            "Constraints: Focus on core concepts, practice, and assessment."
        )
        text = _nvidia_chat([
            {"role": "system", "content": prompt},
            {"role": "user", "content": user}
        ], temperature=0.4, max_tokens=1200)

        # sanitize to remove bullets if any slipped
        lines = []
        for ln in text.splitlines():
            if ln.strip().startswith(('-', '*', '•')):
                lines.append(ln.lstrip('-*• ').strip())
            else:
                lines.append(ln)
        plan = "\n".join(lines).strip()

        # naive suggestions: extract quoted phrases or use topic
        suggestions = []
        import re as _re
        for m in _re.findall(r'\"([^\"]{4,})\"', plan):
            suggestions.append(m)
        if not suggestions:
            suggestions = [f"{topic} tutorial", f"{topic} explained", f"{topic} practice exercises"]

        return jsonify({
            'status': 'success',
            'topic': topic,
            'level': level,
            'durationWeeks': duration_weeks,
            'plan': plan,
            'videoQueries': suggestions[:6]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/<session_id>', methods=['GET'])
def recommendations(session_id):
    try:
        stats = ANALYTICS['users'].get(session_id)
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
                'action': 'advance_level',
                'details': 'Attempt harder questions and real-world applications for this topic.'
            })
        if not recs:
            recs.append({
                'topic': 'general',
                'action': 'balanced_review',
                'details': 'Mix of review and new practice; no clear strengths/weaknesses yet.'
            })

        return jsonify({
            'status': 'success',
            'sessionId': session_id,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': recs
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
        # fall back to anonymous session-based tracking
        query = query.filter_by(session_id=session_id)

    # Order by created_at so "lastPracticedAt" is meaningful
    scores = query.order_by(QuizScore.created_at.asc()).all()

    topics = {}
    overall_questions = 0
    overall_correct = 0

    for score in scores:
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 