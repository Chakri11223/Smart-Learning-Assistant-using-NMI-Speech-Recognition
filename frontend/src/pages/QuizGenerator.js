import React, { useState, useRef } from 'react';
import axios from 'axios';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  TextField,
  Paper,
  Grid,
  Container,
  Alert,
  Chip,
  Stack,
  Divider,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Fade
} from '@mui/material';
import {
  AttachFile,
  Send,
  Download,
  Quiz,
  Description
} from '@mui/icons-material';

const ensureId = (item = {}) => {
  if (item.id) return item;
  let id;
  try {
    id =
      typeof window !== 'undefined' &&
        window.crypto &&
        typeof window.crypto.randomUUID === 'function'
        ? window.crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  } catch (e) {
    console.warn('Failed to generate secure id:', e);
    id = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }
  return { ...item, id };
};

const sanitizeItems = (arr, safeText) => {
  if (!Array.isArray(arr)) return [];
  return arr.map((it, index) => {
    if (!it || typeof it !== 'object') return null;

    const sanitizedItem = {
      id: it?.id || `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
      question: safeText(it?.question),
      options: Array.isArray(it?.options)
        ? it.options.map(o => safeText(o)).filter(Boolean)
        : [],
      correctAnswer: Number.isInteger(it?.correctAnswer) ? it.correctAnswer : 0
    };

    if (!sanitizedItem.question) sanitizedItem.question = `Question ${index + 1}`;
    if (sanitizedItem.options.length === 0) {
      sanitizedItem.options = ['Option A', 'Option B', 'Option C', 'Option D'];
    }

    return sanitizedItem;
  }).filter(Boolean);
};

const extractErrorMessage = (err, fallback) => {
  if (err?.response?.data?.error?.message) return err.response.data.error.message;
  if (err?.message) return err.message;
  return fallback;
};

function QuizGenerator() {
  const navigate = useNavigate();
  const location = useLocation();
  const [pdfFile, setPdfFile] = useState(null);

  // Pre-fill text from location state if available
  const [text, setText] = useState(() => {
    if (location.state?.topic) {
      return `Generate a quiz about ${location.state.topic}`;
    }
    if (location.state?.text) {
      return location.state.text;
    }
    return '';
  });

  const [numQuestions, setNumQuestions] = useState('5');
  const [items, setItems] = useState([]);
  const [generatedTitle, setGeneratedTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fileInputRef = useRef(null);

  const safeText = (val) => {
    if (val == null) return '';
    if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') return String(val);
    return '';
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    setItems([]);
    try {
      const count = Math.max(1, Math.min(20, parseInt(numQuestions || '5', 10) || 5));
      let res;
      if (pdfFile) {
        const form = new FormData();
        form.append('pdf', pdfFile);
        form.append('numQuestions', String(count));
        res = await axios.post('http://localhost:5000/api/generate-quiz', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000 // 60 seconds timeout
        });
      } else {
        res = await axios.post('http://localhost:5000/api/generate-quiz', {
          text,
          numQuestions: count
        }, { timeout: 60000 });
      }

      const rawItems = Array.isArray(res.data.items) ? res.data.items.map(ensureId) : [];
      const received = sanitizeItems(rawItems, safeText);
      setItems(received);

      // Store the AI-generated title if available
      if (res.data.title) {
        setGeneratedTitle(res.data.title);
      }

      if (!received.length) setError('No items were returned.');
    } catch (e) {
      const message = extractErrorMessage(e, 'Failed to generate quiz.');
      setError(message);
    }
    setLoading(false);
  };

  const handleDownloadPdf = async () => {
    if (!items.length) return;
    try {
      const res = await axios.post(
        'http://localhost:5000/api/generate-pdf',
        { items, title: 'Generated Quiz' },
        { responseType: 'blob' }
      );
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'quiz.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to download PDF.'));
    }
  };

  const handleDownloadAnswerKey = async () => {
    if (!items.length) return;
    try {
      const res = await axios.post(
        'http://localhost:5000/api/generate-answer-key',
        { items, title: 'Quiz Answer Key' },
        { responseType: 'blob' }
      );
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'answer_key.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to download answer key.'));
    }
  };

  const handleTakeQuiz = () => {
    if (items.length > 0) {
      let title = "Generated Quiz";

      if (generatedTitle) {
        title = generatedTitle;
      } else if (pdfFile) {
        title = pdfFile.name.replace(/\.pdf$/i, "");
      } else if (text) {
        title = text.slice(0, 30) + (text.length > 30 ? "..." : "");
      }
      navigate('/take-quiz', { state: { questions: items, title } });
    }
  };

  return (
    <Box sx={{
      height: 'calc(100vh - 160px)',
      bgcolor: 'background.default',
      overflow: 'auto' // Enable scrolling
    }}>
      <Container maxWidth="xl" sx={{ minHeight: '100%', pb: 4 }}>
        <Grid container spacing={3} sx={{ minHeight: '100%' }}>
          {/* Left Panel: Input Source */}
          <Grid item xs={12} md={7} sx={{ height: '100%' }}>
            <Paper
              elevation={0}
              sx={{
                height: '100%',
                p: 4,
                borderRadius: 4,
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden' // Prevent panel scroll
              }}
            >
              <Typography variant="h5" fontWeight="800" gutterBottom sx={{ color: 'primary.main', mb: 3 }}>
                1. Add Content
              </Typography>

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                  Upload Document
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<AttachFile />}
                  onClick={() => fileInputRef.current?.click()}
                  fullWidth
                  sx={{
                    height: 70,
                    borderStyle: 'dashed',
                    borderWidth: 2,
                    borderRadius: 3,
                    bgcolor: 'action.hover'
                  }}
                >
                  {pdfFile ? (
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <Description color="primary" />
                      <Typography fontWeight="600">{pdfFile.name}</Typography>
                    </Stack>
                  ) : 'Click to upload PDF'}
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  style={{ display: 'none' }}
                  onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                />
                {pdfFile && (
                  <Chip
                    label="Remove File"
                    onDelete={() => setPdfFile(null)}
                    color="error"
                    size="small"
                    variant="outlined"
                    sx={{ mt: 1 }}
                  />
                )}
              </Box>

              <Divider sx={{ mb: 3 }}>
                <Chip label="OR PASTE TEXT" size="small" sx={{ fontWeight: 600 }} />
              </Divider>

              <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                  Text Content
                </Typography>
                <TextField
                  multiline
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  fullWidth
                  placeholder="Paste your study notes, article, or content here..."
                  sx={{
                    flexGrow: 1,
                    '& .MuiOutlinedInput-root': {
                      height: '100%',
                      alignItems: 'flex-start',
                      overflow: 'auto' // Scroll only inside the text field
                    }
                  }}
                />
              </Box>
            </Paper>
          </Grid>

          {/* Right Panel: Settings & Actions */}
          <Grid item xs={12} md={5} sx={{ height: '100%' }}>
            <Stack spacing={3} sx={{ height: '100%' }}>
              {/* Settings Card */}
              <Paper
                elevation={0}
                sx={{
                  p: 4,
                  borderRadius: 4,
                  bgcolor: 'background.paper',
                  border: '1px solid',
                  borderColor: 'divider'
                }}
              >
                <Typography variant="h5" fontWeight="800" gutterBottom sx={{ color: 'primary.main', mb: 3 }}>
                  2. Configure Quiz
                </Typography>

                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Number of Questions
                </Typography>
                <TextField
                  type="number"
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(e.target.value)}
                  inputProps={{ min: 1, max: 20 }}
                  fullWidth
                  size="medium"
                  sx={{ mb: 3 }}
                />

                <Button
                  variant="contained"
                  size="large"
                  onClick={handleGenerate}
                  disabled={loading || (!pdfFile && !text.trim())}
                  fullWidth
                  sx={{
                    height: 56,
                    fontSize: '1.1rem',
                    fontWeight: 'bold',
                    boxShadow: 4
                  }}
                >
                  {loading ? <CircularProgress size={24} color="inherit" /> : 'Generate Quiz'}
                </Button>

                {error && (
                  <Alert severity="error" sx={{ mt: 2, borderRadius: 2 }}>
                    {error}
                  </Alert>
                )}
              </Paper>

              {/* Results Card */}
              {items.length > 0 && (
                <Paper
                  elevation={0}
                  sx={{
                    flexGrow: 1,
                    p: 4,
                    borderRadius: 4,
                    bgcolor: 'primary.main',
                    color: 'primary.contrastText',
                    border: '1px solid',
                    borderColor: 'primary.main',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    textAlign: 'center',
                    transition: 'all 0.3s ease'
                  }}
                >
                  <Fade in>
                    <Box width="100%">
                      <Stack spacing={2} width="100%">
                        <Button
                          variant="contained"
                          color="secondary"
                          size="large"
                          onClick={handleTakeQuiz}
                          startIcon={<Quiz />}
                          fullWidth
                          sx={{
                            bgcolor: 'white',
                            color: 'primary.main',
                            '&:hover': { bgcolor: 'grey.100' },
                            py: 2,
                            fontSize: '1.1rem',
                            fontWeight: 'bold'
                          }}
                        >
                          Start Quiz Now
                        </Button>
                      </Stack>
                    </Box>
                  </Fade>
                </Paper>
              )}
            </Stack >
          </Grid >
        </Grid >


      </Container >
    </Box >
  );
}

export default QuizGenerator;
