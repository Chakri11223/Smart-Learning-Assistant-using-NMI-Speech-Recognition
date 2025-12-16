import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from 'react-markdown';
import axios from "axios";
import {
  Box,
  Typography,
  Paper,
  IconButton,
  InputBase,
  Container,
  CircularProgress,
  Avatar,
  Stack,
  Tooltip,
  Fade,
  useTheme,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  Button,
  useMediaQuery,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Switch
} from "@mui/material";
import {
  Send as SendIcon,
  Mic as MicIcon,
  Stop as StopIcon,
  AttachFile as AttachFileIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  ContentCopy as CopyIcon,
  Add as AddIcon,
  Chat as ChatIcon,
  Menu as MenuIcon,
  Delete as DeleteIcon,
  RecordVoiceOver as InterviewIcon,
  Fullscreen as FullscreenIcon,
  FullscreenExit as FullscreenExitIcon,
  Settings as SettingsIcon,
  ChevronLeft as ChevronLeftIcon
} from "@mui/icons-material";
import SafeText from "../components/SafeText";

const DEFAULT_DEV_API =
  typeof window !== "undefined" && window.location && window.location.port === "3000"
    ? "http://localhost:5000"
    : "";
const API_BASE = (process.env.REACT_APP_API_BASE_URL || DEFAULT_DEV_API || "").replace(/\/$/, "");
const withBase = (path) => (API_BASE ? `${API_BASE}${path}` : path);

const VoiceQA = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [audioFile, setAudioFile] = useState(null);

  // History State
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(!isMobile);

  // Document State
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [isInterviewMode, setIsInterviewMode] = useState(false);

  // Interview State
  const [showSetup, setShowSetup] = useState(false);
  const [jobRole, setJobRole] = useState("");
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [silenceTimer, setSilenceTimer] = useState(null);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const docInputRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch sessions and documents on mount
  useEffect(() => {
    fetchSessions();
    fetchDocuments();
  }, []);

  const getAuthHeaders = () => {
    try {
      const userStr = localStorage.getItem('authUser');
      const user = userStr ? JSON.parse(userStr) : null;
      if (user && user.id) {
        return { 'X-User-Id': user.id };
      }
    } catch (e) {
      console.error("Error parsing auth user", e);
    }
    return {};
  };

  const fetchSessions = async () => {
    try {
      const res = await axios.get(withBase("/api/chat/sessions"), {
        headers: getAuthHeaders()
      });
      setSessions(res.data.sessions || []);
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await axios.get(withBase("/api/documents"), {
        headers: getAuthHeaders()
      });
      setDocuments(res.data.documents || []);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    }
  };

  const handleDocUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingDoc(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post(withBase("/api/documents"), formData, {
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'multipart/form-data'
        }
      });
      setDocuments(prev => [res.data, ...prev]);
      setSelectedDocId(res.data.id);
      addMessage("ai", `I've analyzed "${file.name}". You can now ask me questions about it!`);
    } catch (err) {
      console.error("Upload failed", err);
      addMessage("error", "Failed to upload document: " + (err.response?.data?.error || err.message));
    }
    setUploadingDoc(false);
  };

  const loadSession = async (sessionId) => {
    try {
      setLoading(true);
      const res = await axios.get(withBase(`/api/chat/sessions/${sessionId}`), {
        headers: getAuthHeaders()
      });

      const flatMessages = [];
      res.data.messages.forEach(m => {
        flatMessages.push({ type: 'user', content: m.user_message, timestamp: m.created_at });
        flatMessages.push({ type: 'ai', content: m.ai_response, timestamp: m.created_at });
      });

      setMessages(flatMessages);
      setCurrentSessionId(sessionId);
      setLoading(false);
      if (isMobile) setDrawerOpen(false);
    } catch (err) {
      console.error("Failed to load session", err);
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null);
    setQuestion("");
    setSelectedDocId("");
    if (isMobile) setDrawerOpen(false);
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this chat?")) return;

    try {
      await axios.delete(withBase(`/api/chat/sessions/${sessionId}`), {
        headers: getAuthHeaders()
      });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        handleNewChat();
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  const handleAudioChange = (e) => {
    const file = e.target.files?.[0] || null;
    if (file) {
      setAudioFile(file);
      setQuestion(`[Audio File: ${file.name}]`);
    }
  };

  const addMessage = (type, content) => {
    setMessages((prev) => [...prev, { type, content, timestamp: new Date() }]);
  };

  const fallbackToNonStreaming = async (currentQuestion) => {
    try {
      const payload = {
        question: currentQuestion,
        tts: false,
        session_id: currentSessionId,
        document_id: selectedDocId || undefined,
        mode: isInterviewMode ? 'interview' : 'chat',
        tts: isInterviewMode // Request TTS in interview mode
      };

      const res = await axios.post(withBase("/api/voice-qa"), payload, {
        headers: getAuthHeaders()
      });
      addMessage("ai", res.data.answer || "No response received");

      if (res.data.session_id) {
        if (currentSessionId !== res.data.session_id) {
          setCurrentSessionId(res.data.session_id);
          fetchSessions(); // Refresh list to show new title
        }
      }

      // Handle Audio Playback
      if (res.data.audioBase64) {
        const audio = document.getElementById('interview-audio');
        if (audio) {
          audio.src = `data:${res.data.audioMime || 'audio/mpeg'};base64,${res.data.audioBase64}`;
          audio.play().catch(e => console.error("Audio play failed", e));
        }
      }
    } catch (fallbackErr) {
      const axiosError = fallbackErr;
      addMessage("error", "Error: " + (axiosError.response?.data?.error || axiosError.message));
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if ((!question.trim() && !audioFile) || loading) return;

    const currentQuestion = question;
    const currentAudio = audioFile;

    // Clear input
    setQuestion("");
    setAudioFile(null);

    if (currentAudio) {
      // Handle Audio Upload
      addMessage("user", `Uploaded Audio: ${currentAudio.name}`);
      setLoading(true);

      const formData = new FormData();
      formData.append("audio", currentAudio);
      if (currentSessionId) {
        formData.append("session_id", currentSessionId);
      }
      if (selectedDocId) {
        formData.append("document_id", selectedDocId);
      }
      if (isInterviewMode) {
        formData.append("mode", "interview");
        formData.append("tts", "true");
      }

      try {
        const headers = {
          "Content-Type": "multipart/form-data",
          ...getAuthHeaders()
        };

        const res = await axios.post(withBase("/api/voice-qa"), formData, {
          headers: headers
        });

        addMessage("ai", res.data.answer || "AI response received");

        if (res.data.session_id) {
          if (currentSessionId !== res.data.session_id) {
            setCurrentSessionId(res.data.session_id);
            fetchSessions();
          }
        }

        // Handle Audio Playback
        if (res.data.audioBase64) {
          const audio = document.getElementById('interview-audio');
          if (audio) {
            audio.src = `data:${res.data.audioMime || 'audio/mpeg'};base64,${res.data.audioBase64}`;
            audio.play().catch(e => console.error("Audio play failed", e));
          }
        }
      } catch (err) {
        const axiosError = err;
        addMessage("error", "Error: " + (axiosError.response?.data?.error || axiosError.message));
      }
      setLoading(false);
      return;
    }

    // Handle Text Question
    addMessage("user", currentQuestion);
    setLoading(true);

    // For now, use non-streaming to ensure session ID handling is robust
    // Or update streaming to handle session ID?
    // The streaming endpoint currently doesn't save history or return session ID.
    // So we should use non-streaming for history persistence for now, 
    // OR update streaming endpoint.
    // Given the user request "save like in chatgpt", persistence is key.
    // The current streaming implementation in app.py does NOT save to DB.
    // So I will switch to non-streaming by default to ensure history is saved,
    // or I'd need to update the streaming endpoint significantly.
    // Let's use non-streaming for now to guarantee history saving.

    await fallbackToNonStreaming(currentQuestion);
  };

  const startRecording = () => {
    const typedWindow = window;
    const SpeechRecognition = typedWindow.SpeechRecognition || typedWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      addMessage("error", "Speech recognition is not supported in this browser. Try Chrome.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true; // Keep listening
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join('');
      setQuestion(transcript);

      // Reset silence timer on speech
      if (silenceTimer) clearTimeout(silenceTimer);
      const timer = setTimeout(() => {
        stopRecording();
      }, 10000); // 10 seconds silence timeout
      setSilenceTimer(timer);
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      if (event.error === 'no-speech') {
        // Ignore no-speech error in continuous mode
        return;
      }
      setIsRecording(false);
    };

    recognition.onend = () => {
      // If we are still recording (not manually stopped), restart?
      // For now, let's just stop to be safe, or rely on silence timer.
      // Actually, if user stops speaking, we want to wait 10s.
      // If the browser stops recognition automatically, we should respect that 
      // UNLESS we want "always on".
      // The user said "wait for 10sec and turnoff automatically".
      // If the browser stops early, we might lose that logic.
      // But usually continuous mode stays open.
      if (isRecording) {
        // Optionally restart here if we want truly continuous
        // recognition.start(); 
        // But let's stick to simple state update for now.
        setIsRecording(false);
      }
    };

    recognitionRef.current = recognition;
    setIsRecording(true);
    recognition.start();

    // Initial silence timer
    const timer = setTimeout(() => {
      stopRecording();
    }, 10000);
    setSilenceTimer(timer);
  };

  const stopRecording = () => {
    if (silenceTimer) clearTimeout(silenceTimer);
    const rec = recognitionRef.current;
    if (rec) {
      try {
        rec.stop();
      } catch { }
    }
    setIsRecording(false);
  };



  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
  };

  // Full Screen Interview UI
  if (isInterviewMode && isFullScreen) {
    return (
      <Box sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        bgcolor: '#1a1a2e', // Deep dark blue background
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        p: 4
      }}>
        {/* Header */}
        <Box sx={{ position: 'absolute', top: 20, left: 20, right: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" fontWeight="bold" sx={{ color: '#4db6ac' }}>
            Mock Interview Mode
          </Typography>
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              color="inherit"
              startIcon={<FullscreenExitIcon />}
              onClick={() => setIsFullScreen(false)}
              sx={{ borderRadius: 20, textTransform: 'none', borderColor: 'rgba(255,255,255,0.3)' }}
            >
              Exit Full Screen
            </Button>
            <Button
              variant="outlined"
              color="error"
              onClick={() => {
                setIsInterviewMode(false);
                stopRecording();
              }}
              sx={{ borderRadius: 20, textTransform: 'none' }}
            >
              End Interview
            </Button>
          </Stack>
        </Box>

        {/* Central Visual */}
        <Box sx={{ position: 'relative', mb: 8, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          {/* Pulsing Rings */}
          <Box sx={{
            position: 'absolute',
            width: 300,
            height: 300,
            borderRadius: '50%',
            border: '2px solid rgba(77, 182, 172, 0.3)',
            animation: loading ? 'pulse 2s infinite' : 'none',
            '@keyframes pulse': {
              '0%': { transform: 'scale(0.8)', opacity: 0.5 },
              '100%': { transform: 'scale(1.5)', opacity: 0 }
            }
          }} />
          <Box sx={{
            position: 'absolute',
            width: 200,
            height: 200,
            borderRadius: '50%',
            border: '2px solid rgba(77, 182, 172, 0.5)',
            animation: loading ? 'pulse 2s infinite 0.5s' : 'none'
          }} />

          {/* Avatar */}
          <Avatar sx={{ width: 120, height: 120, bgcolor: '#4db6ac', boxShadow: '0 0 40px rgba(77, 182, 172, 0.6)' }}>
            <InterviewIcon sx={{ fontSize: 60, color: '#fff' }} />
          </Avatar>
        </Box>

        {/* Status Text */}
        <Typography variant="h5" align="center" sx={{ mb: 4, maxWidth: 800, minHeight: 80 }}>
          {loading ? "Thinking..." : (messages.length > 0 && messages[messages.length - 1].type === 'ai' ? messages[messages.length - 1].content : "I'm listening...")}
        </Typography>

        {/* Controls */}
        <Stack direction="row" spacing={4} alignItems="center">
          <IconButton
            onClick={isRecording ? stopRecording : startRecording}
            sx={{
              width: 80,
              height: 80,
              bgcolor: isRecording ? '#f44336' : '#4db6ac',
              '&:hover': { bgcolor: isRecording ? '#d32f2f' : '#009688' },
              boxShadow: '0 0 30px rgba(0,0,0,0.5)',
              transition: 'all 0.3s ease'
            }}
          >
            {isRecording ? <StopIcon sx={{ fontSize: 40, color: 'white' }} /> : <MicIcon sx={{ fontSize: 40, color: 'white' }} />}
          </IconButton>
        </Stack>

        <Typography variant="caption" sx={{ mt: 2, opacity: 0.7 }}>
          {isRecording ? "Tap to Stop" : "Tap to Speak"}
        </Typography>

        {/* Hidden Audio Element for Auto-play */}
        <audio id="interview-audio" style={{ display: 'none' }} />
      </Box>
    );
  }

  const startInterviewSession = async (role) => {
    setShowSetup(false);
    setIsInterviewMode(true);
    setIsFullScreen(true); // Enforce full screen
    setLoading(true);

    // Add system message
    addMessage("system", `Starting Mock Interview for ${role || "General Role"}...`);

    try {
      // Send initial trigger to AI
      const payload = {
        question: `I am ready for the interview. I am applying for the position of ${role}.`,
        session_id: currentSessionId,
        document_id: selectedDocId || undefined,
        mode: 'interview', // Explicitly set mode
        tts: true // Request TTS
      };

      const res = await axios.post(withBase("/api/voice-qa"), payload, {
        headers: getAuthHeaders()
      });

      addMessage("ai", res.data.answer || "Hello, let's start the interview.");

      if (res.data.session_id) {
        if (currentSessionId !== res.data.session_id) {
          setCurrentSessionId(res.data.session_id);
          fetchSessions();
        }
      }

      // Handle Audio Playback
      if (res.data.audioBase64) {
        const audio = document.getElementById('interview-audio');
        if (audio) {
          audio.src = `data:${res.data.audioMime || 'audio/mpeg'};base64,${res.data.audioBase64}`;
          audio.play().catch(e => console.error("Audio play failed", e));
        }
      }
    } catch (err) {
      console.error("Failed to start interview", err);
      addMessage("error", "Failed to start interview session.");
    }
    setLoading(false);
  };

  return (
    <Box sx={{
      height: 'calc(100vh - 64px)', // Adjusted for main layout
      display: 'flex',
      bgcolor: 'background.default',
      overflow: 'hidden'
    }}>
      {/* Sidebar Drawer */}
      <Drawer
        variant={isMobile ? "temporary" : "persistent"}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{
          width: drawerOpen && !isMobile ? 280 : 0,
          flexShrink: 0,
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          '& .MuiDrawer-paper': {
            width: 280,
            boxSizing: 'border-box',
            top: isMobile ? 0 : 64, // Below AppBar on desktop
            height: isMobile ? '100%' : 'calc(100% - 64px)',
            borderRight: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper'
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3, mt: 1 }}>
            <Typography variant="h6" fontWeight="bold" sx={{ color: theme.palette.primary.main, display: 'flex', alignItems: 'center', gap: 1 }}>
              <BotIcon /> Voice Q&A
            </Typography>
            <Tooltip title="Close Sidebar">
              <IconButton
                onClick={() => setDrawerOpen(false)}
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 2,
                  '&:hover': { bgcolor: 'action.hover', borderColor: 'primary.main', color: 'primary.main' }
                }}
              >
                <ChevronLeftIcon />
              </IconButton>
            </Tooltip>
          </Box>

          <Button
            fullWidth
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleNewChat}
            sx={{ borderRadius: 2, textTransform: 'none', py: 1, mb: 2 }}
          >
            New Chat
          </Button>

          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, px: 1 }}>
            Knowledge Base
          </Typography>
          <Button
            fullWidth
            variant="outlined"
            size="small"
            startIcon={uploadingDoc ? <CircularProgress size={16} /> : <AttachFileIcon />}
            onClick={() => docInputRef.current?.click()}
            disabled={uploadingDoc}
            sx={{ borderRadius: 2, textTransform: 'none', mb: 1 }}
          >
            {uploadingDoc ? "Uploading..." : "Upload PDF"}
          </Button>
          <input
            ref={docInputRef}
            type="file"
            accept="application/pdf"
            onChange={handleDocUpload}
            style={{ display: "none" }}
          />

          {documents.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', borderColor: '#e0e0e0' }}
              >
                <option value="">No Document Selected</option>
                {documents.map(doc => (
                  <option key={doc.id} value={doc.id}>
                    {doc.filename.length > 20 ? doc.filename.substring(0, 20) + '...' : doc.filename}
                  </option>
                ))}
              </select>
            </Box>
          )}
        </Box>
        <Divider />
        <Box sx={{ p: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, px: 1 }}>
            Features
          </Typography>
          <Button
            fullWidth
            variant={isInterviewMode ? "contained" : "outlined"}
            color={isInterviewMode ? "secondary" : "primary"}
            startIcon={<InterviewIcon />}
            onClick={() => {
              if (isInterviewMode) {
                setIsInterviewMode(false);
                stopRecording();
              } else {
                setShowSetup(true);
              }
            }}
            sx={{ borderRadius: 2, textTransform: 'none', mb: 1 }}
          >
            {isInterviewMode ? "End Mock Interview" : "Mock Interview"}
          </Button>
        </Box>
        <Divider />

        {/* Setup Dialog */}
        <Dialog open={showSetup} onClose={() => setShowSetup(false)}>
          <DialogTitle>Start Mock Interview</DialogTitle>
          <DialogContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Enter the job role you are applying for and upload your resume (optional) to get a personalized interview experience.
            </Typography>
            <TextField
              autoFocus
              margin="dense"
              label="Job Role (e.g., Python Developer)"
              fullWidth
              variant="outlined"
              value={jobRole}
              onChange={(e) => setJobRole(e.target.value)}
              sx={{ mb: 2 }}
            />
            <Button
              variant="outlined"
              component="label"
              startIcon={<AttachFileIcon />}
              fullWidth
              sx={{ mb: 2 }}
            >
              Upload Resume (PDF)
              <input
                type="file"
                hidden
                accept="application/pdf"
                onChange={handleDocUpload}
              />
            </Button>
            {selectedDocId && (
              <Chip label="Resume Uploaded" color="success" size="small" sx={{ mb: 2 }} />
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowSetup(false)}>Cancel</Button>
            <Button
              onClick={() => startInterviewSession(jobRole)}
              variant="contained"
              disabled={!jobRole.trim()}
            >
              Start Interview
            </Button>
          </DialogActions>
        </Dialog>
        <List sx={{ overflow: 'auto', flexGrow: 1 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ px: 3, py: 1 }}>
            Recent Chats
          </Typography>
          {sessions.map((session) => (
            <ListItem
              key={session.id}
              disablePadding
              secondaryAction={
                <IconButton edge="end" aria-label="delete" size="small" onClick={(e) => handleDeleteSession(e, session.id)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              }
            >
              <ListItemButton
                selected={currentSessionId === session.id}
                onClick={() => loadSession(session.id)}
                sx={{
                  borderRadius: 1,
                  mx: 1,
                  mb: 0.5,
                  '&.Mui-selected': {
                    bgcolor: 'primary.light',
                    color: 'primary.contrastText',
                    '&:hover': { bgcolor: 'primary.main' },
                    '& .MuiListItemIcon-root': { color: 'inherit' }
                  }
                }}
              >
                <ListItemText
                  primary={session.title || "New Chat"}
                  primaryTypographyProps={{
                    noWrap: true,
                    fontSize: '0.9rem',
                    fontWeight: currentSessionId === session.id ? 'bold' : 'normal'
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
          {sessions.length === 0 && (
            <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary' }}>
              <Typography variant="body2">No history yet</Typography>
            </Box>
          )}
        </List>
      </Drawer>

      {/* Main Chat Area */}
      <Box sx={{
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
        transition: theme.transitions.create('margin', {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.leavingScreen,
        }),
        marginLeft: 0,
      }}>
        {/* Toggle Sidebar Button (Mobile or when closed) */}
        {!drawerOpen && (
          <Tooltip title="Open Sidebar" placement="right">
            <Box
              onClick={() => setDrawerOpen(true)}
              sx={{
                position: 'absolute',
                top: 20,
                left: 0,
                zIndex: 10,
                bgcolor: 'background.paper',
                borderTopRightRadius: 50,
                borderBottomRightRadius: 50,
                boxShadow: 3,
                py: 1.5,
                pl: 1,
                pr: 2,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                transition: 'all 0.2s ease',
                '&:hover': {
                  pl: 2,
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText'
                }
              }}
            >
              <MenuIcon fontSize="small" />
            </Box>
          </Tooltip>
        )}

        {/* Messages */}
        <Box sx={{
          flexGrow: 1,
          overflow: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2
        }}>
          {messages.length === 0 && (
            <Box sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              opacity: 0.7
            }}>
              <Avatar sx={{ width: 80, height: 80, mb: 2, bgcolor: isInterviewMode ? 'secondary.main' : 'primary.main' }}>
                {isInterviewMode ? <InterviewIcon sx={{ fontSize: 40 }} /> : <BotIcon sx={{ fontSize: 40 }} />}
              </Avatar>
              <Typography variant="h5" gutterBottom fontWeight="bold">
                {isInterviewMode ? "Mock Interview Session" : "How can I help you today?"}
              </Typography>
              {isInterviewMode && (
                <Typography variant="body1" color="text.secondary">
                  Tell me the job role you are preparing for, and I will start the interview.
                </Typography>
              )}
              {selectedDocId && (
                <Chip
                  label="Document Context Active"
                  color="primary"
                  variant="outlined"
                  sx={{ mt: 1 }}
                />
              )}
            </Box>
          )}

          {messages.map((msg, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                justifyContent: msg.type === 'user' ? 'flex-end' : 'flex-start',
                width: '100%'
              }}
            >
              <Stack direction="row" spacing={1} maxWidth="80%">
                {msg.type === 'ai' && (
                  <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
                    <BotIcon fontSize="small" />
                  </Avatar>
                )}

                <Paper sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: msg.type === 'user' ? 'primary.main' : 'background.paper',
                  color: msg.type === 'user' ? 'primary.contrastText' : 'text.primary',
                  position: 'relative',
                  '&:hover .copy-btn': { opacity: 1 },
                  '& p': { m: 0 }, // Remove default margin from markdown paragraphs if needed
                  '& pre': { overflowX: 'auto' } // Handle code blocks
                }}>
                  {msg.type === 'ai' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    <SafeText variant="body1" sx={{ lineHeight: 1.6 }}>
                      {msg.content}
                    </SafeText>
                  )}
                  {msg.type === 'ai' && !msg.isStreaming && (
                    <IconButton
                      className="copy-btn"
                      size="small"
                      onClick={() => handleCopy(msg.content)}
                      sx={{
                        position: 'absolute',
                        bottom: -10,
                        right: -10,
                        opacity: 0,
                        transition: 'opacity 0.2s',
                        bgcolor: 'background.paper',
                        boxShadow: 1,
                        '&:hover': { bgcolor: 'grey.100' }
                      }}
                    >
                      <CopyIcon fontSize="small" />
                    </IconButton>
                  )}
                </Paper>

                {msg.type === 'user' && (
                  <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}>
                    <PersonIcon fontSize="small" />
                  </Avatar>
                )}
              </Stack>
            </Box>
          ))}
          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-start', width: '100%' }}>
              <Stack direction="row" spacing={1}>
                <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
                  <BotIcon fontSize="small" />
                </Avatar>
                <Paper sx={{ p: 2, borderRadius: 2, bgcolor: 'background.paper' }}>
                  <CircularProgress size={20} />
                </Paper>
              </Stack>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>

        {/* Input Area */}
        <Box sx={{ p: 2, bgcolor: 'background.default' }}>
          <Container maxWidth="md">
            <Paper
              component="form"
              onSubmit={handleSubmit}
              sx={{
                p: '2px 4px',
                display: 'flex',
                alignItems: 'center',
                borderRadius: 3,
                boxShadow: 3,
                border: '1px solid',
                borderColor: 'divider'
              }}
            >
              <Tooltip title="Upload Audio">
                <IconButton sx={{ p: '10px' }} aria-label="upload" onClick={() => fileInputRef.current?.click()}>
                  <AttachFileIcon />
                </IconButton>
              </Tooltip>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                onChange={handleAudioChange}
                style={{ display: "none" }}
              />

              <InputBase
                sx={{ ml: 1, flex: 1 }}
                placeholder={isRecording ? "Listening..." : "Message Voice Q&A..."}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading}
                multiline
                maxRows={4}
              />

              {question.trim() || audioFile ? (
                <IconButton type="submit" color="primary" sx={{ p: '10px' }} aria-label="send" disabled={loading}>
                  {loading ? <CircularProgress size={24} /> : <SendIcon />}
                </IconButton>
              ) : (
                <Tooltip title={isRecording ? "Stop Recording" : "Start Recording"}>
                  <IconButton
                    color={isRecording ? "error" : "primary"}
                    sx={{ p: '10px' }}
                    onClick={isRecording ? stopRecording : startRecording}
                  >
                    {isRecording ? <StopIcon /> : <MicIcon />}
                  </IconButton>
                </Tooltip>
              )}
            </Paper>
            <Typography variant="caption" display="block" align="center" sx={{ mt: 1, color: 'text.secondary' }}>
              Voice Q&A can make mistakes. Consider checking important information.
            </Typography>
          </Container>
        </Box>
      </Box>
    </Box>
  );
};

export default VoiceQA;
