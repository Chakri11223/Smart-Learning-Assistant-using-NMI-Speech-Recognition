import React, { useState, useEffect, useRef } from 'react';
import {
    Box,
    Container,
    Typography,
    Paper,
    TextField,
    Button,
    Grid,
    Card,
    CardContent,
    Avatar,
    CircularProgress,
    List,
    ListItem,
    ListItemText,
    ListItemAvatar,
    Divider,
    Chip,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    IconButton
} from '@mui/material';
import {
    School as SchoolIcon,
    Send as SendIcon,
    Psychology as PsychologyIcon,
    EmojiObjects as IdeaIcon,
    RecordVoiceOver as VoiceIcon,
    Stop as StopIcon,
    Assessment as AssessmentIcon,
    Mic as MicIcon,
    VolumeUp as VolumeUpIcon,
    VolumeOff as VolumeOffIcon
} from '@mui/icons-material';
import { Tabs, Tab } from '@mui/material'; // Added Tabs and Tab
import axios from 'axios';
import Community from './Community';

const FeynmanBoard = () => {
    // State for session management
    const [step, setStep] = useState('setup'); // 'setup', 'teaching', 'report'
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Setup State
    const [topic, setTopic] = useState('');
    const [persona, setPersona] = useState('Curious 5-Year-Old');

    // Chat State
    const [sessionId, setSessionId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const messagesEndRef = useRef(null);

    // Voice State
    const [isListening, setIsListening] = useState(false);
    const [voiceEnabled, setVoiceEnabled] = useState(true);
    const [interimText, setInterimText] = useState(''); // For real-time feedback
    const recognitionRef = useRef(null);
    const isListeningRef = useRef(false); // Ref for closure access
    const synthRef = useRef(window.speechSynthesis);

    // Report State
    const [report, setReport] = useState(null);

    const personas = [
        'Curious 5-Year-Old',
        'Skeptical College Student',
        'Confused Grandmother',
        'Strict Professor',
        'Lazy Teenager'
    ];

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
        // Auto-speak last assistant message if voice enabled
        if (voiceEnabled && messages.length > 0) {
            const lastMsg = messages[messages.length - 1];
            if (lastMsg.role === 'assistant') {
                speakText(lastMsg.content);
            }
        }
    }, [messages]);

    const speakText = (text) => {
        if (!voiceEnabled || !synthRef.current) return;
        synthRef.current.cancel(); // Stop previous
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        synthRef.current.speak(utterance);
    };

    const toggleListening = () => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    };

    const startListening = () => {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Speech recognition is not supported in this browser.');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            setIsListening(true);
            isListeningRef.current = true;
        };

        recognition.onend = () => {
            // Auto-restart if we are still supposed to be listening
            if (isListeningRef.current) {
                try {
                    recognition.start();
                } catch (e) {
                    console.error("Voice restart failed", e);
                    setIsListening(false);
                    isListeningRef.current = false;
                }
            } else {
                setIsListening(false);
                setInterimText('');
            }
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error", event.error);
            if (event.error === 'not-allowed') {
                setIsListening(false);
                isListeningRef.current = false;
                alert("Microphone access denied.");
            }
        };

        recognition.onresult = (event) => {
            let finalTranscript = '';
            let currentInterim = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + ' ';
                } else {
                    currentInterim += event.results[i][0].transcript;
                }
            }

            if (finalTranscript) {
                setInputMessage(prev => prev + finalTranscript);
            }
            setInterimText(currentInterim);
        };

        recognitionRef.current = recognition;
        isListeningRef.current = true;
        recognition.start();
    };

    const stopListening = () => {
        isListeningRef.current = false; // Stop the loop
        if (recognitionRef.current) {
            recognitionRef.current.stop();
        }
        setIsListening(false);
        setInterimText('');
    };

    const handleStartSession = async () => {
        if (!topic.trim()) return;
        setLoading(true);
        setError(null);

        try {
            const authUser = localStorage.getItem('authUser');
            const user = authUser ? JSON.parse(authUser) : null;

            if (!user || !user.id) {
                setError('User not authenticated. Please login.');
                setLoading(false);
                return;
            }

            const response = await axios.post('http://localhost:5000/api/feynman/start', {
                topic,
                persona,
                user_id: user.id
            });
            setSessionId(response.data.session_id);
            setMessages([{
                role: 'assistant',
                content: response.data.greeting
            }]);
            setStep('teaching');
        } catch (err) {
            setError('Failed to start session. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSendMessage = async () => {
        if (!inputMessage.trim()) return;

        const authUser = localStorage.getItem('authUser');
        const user = authUser ? JSON.parse(authUser) : null;

        if (!user || !user.id) {
            setMessages(prev => [...prev, { role: 'error', content: 'User not authenticated.' }]);
            return;
        }

        const userMsg = inputMessage;
        setInputMessage('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);

        try {
            const response = await axios.post('http://localhost:5000/api/feynman/chat', {
                session_id: sessionId,
                message: userMsg,
                topic,
                persona,
                user_id: user.id
            });

            setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: 'error', content: 'Failed to get response.' }]);
        }
    };

    const handleEvaluate = async () => {
        setLoading(true);
        try {
            const authUser = localStorage.getItem('authUser');
            const user = authUser ? JSON.parse(authUser) : null;

            const response = await axios.post('http://localhost:5000/api/feynman/evaluate', {
                session_id: sessionId,
                topic,
                persona,
                user_id: user ? user.id : null
            });
            setReport(response.data);
            setStep('report');
        } catch (err) {
            setError('Failed to generate report.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const renderSetup = () => (
        <Container maxWidth="md" sx={{ mt: 8 }}>
            <Paper elevation={3} sx={{ p: 6, borderRadius: 4, textAlign: 'center', background: 'linear-gradient(145deg, #ffffff 0%, #f5f7fa 100%)' }}>
                <Avatar sx={{ width: 80, height: 80, margin: '0 auto', bgcolor: 'primary.main', mb: 2 }}>
                    <SchoolIcon sx={{ fontSize: 40 }} />
                </Avatar>
                <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold', color: '#1a237e' }}>
                    Explain & Learn
                </Typography>
                <Typography variant="h6" color="textSecondary" paragraph>
                    "If you can't explain it simply, you don't understand it well enough."
                </Typography>
                <Typography variant="body1" paragraph sx={{ mb: 4 }}>
                    Choose a topic and a persona to teach. The AI will test your understanding by asking probing questions.
                </Typography>

                <Box sx={{ maxWidth: 500, margin: '0 auto' }}>
                    <TextField
                        fullWidth
                        label="What do you want to teach?"
                        variant="outlined"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        sx={{ mb: 3 }}
                        placeholder="e.g., Quantum Entanglement, The French Revolution, Recursion"
                    />

                    <FormControl fullWidth sx={{ mb: 4 }}>
                        <InputLabel>Choose your Student Persona</InputLabel>
                        <Select
                            value={persona}
                            label="Choose your Student Persona"
                            onChange={(e) => setPersona(e.target.value)}
                        >
                            {personas.map(p => (
                                <MenuItem key={p} value={p}>{p}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <Button
                        variant="contained"
                        size="large"
                        fullWidth
                        onClick={handleStartSession}
                        disabled={!topic || loading}
                        sx={{
                            py: 1.5,
                            fontSize: '1.1rem',
                            borderRadius: 2,
                            textTransform: 'none',
                            boxShadow: '0 4px 14px 0 rgba(0,118,255,0.39)'
                        }}
                    >
                        {loading ? <CircularProgress size={24} color="inherit" /> : 'Start Teaching Session'}
                    </Button>
                    {error && (
                        <Typography color="error" sx={{ mt: 2 }}>
                            {error}
                        </Typography>
                    )}
                </Box>

                <Divider sx={{ my: 4 }} />

                <Box sx={{ mt: 2 }}>
                    <Typography variant="h6" gutterBottom color="primary">
                        Need inspiration or help?
                    </Typography>
                    <Typography variant="body2" color="textSecondary" paragraph>
                        Join the community discussion to share topics or ask questions.
                    </Typography>
                    <Button
                        variant="outlined"
                        color="secondary"
                        href="/community" // Using href for simple navigation or use useNavigate
                        sx={{ borderRadius: 2 }}
                    >
                        Visit Community
                    </Button>
                </Box>
            </Paper>
        </Container>
    );

    const renderChat = () => (
        <Container maxWidth="lg" sx={{ mt: 4, height: '85vh', display: 'flex', flexDirection: 'column' }}>
            <Paper elevation={2} sx={{ p: 2, mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderRadius: 2 }}>
                <Box display="flex" alignItems="center">
                    <Avatar sx={{ bgcolor: 'secondary.main', mr: 2 }}>
                        <PsychologyIcon />
                    </Avatar>
                    <Box>
                        <Typography variant="h6">Teaching: {topic}</Typography>
                        <Typography variant="body2" color="textSecondary">Student: {persona}</Typography>
                    </Box>
                </Box>
                <Box>
                    <IconButton onClick={() => setVoiceEnabled(!voiceEnabled)} color={voiceEnabled ? 'primary' : 'default'} sx={{ mr: 1 }}>
                        {voiceEnabled ? <VolumeUpIcon /> : <VolumeOffIcon />}
                    </IconButton>
                    <Button
                        variant="outlined"
                        color="success"
                        startIcon={<AssessmentIcon />}
                        onClick={handleEvaluate}
                    >
                        Finish & Evaluate
                    </Button>
                </Box>
            </Paper>

            <Paper elevation={3} sx={{ flexGrow: 1, mb: 2, p: 3, overflowY: 'auto', borderRadius: 2, bgcolor: '#f8f9fa' }}>
                <List>
                    {messages.map((msg, index) => (
                        <ListItem key={index} alignItems="flex-start" sx={{ flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                            <ListItemAvatar>
                                <Avatar sx={{ bgcolor: msg.role === 'user' ? 'primary.main' : 'secondary.main' }}>
                                    {msg.role === 'user' ? 'Me' : <SchoolIcon />}
                                </Avatar>
                            </ListItemAvatar>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    maxWidth: '70%',
                                    borderRadius: 2,
                                    bgcolor: msg.role === 'user' ? '#e3f2fd' : '#ffffff',
                                    ml: msg.role === 'user' ? 0 : 2,
                                    mr: msg.role === 'user' ? 2 : 0
                                }}
                            >
                                <Typography variant="body1">{msg.content}</Typography>
                            </Paper>
                        </ListItem>
                    ))}
                    <div ref={messagesEndRef} />
                </List>
            </Paper>

            <Paper elevation={3} sx={{ p: 2, borderRadius: 2 }}>
                <Box display="flex" gap={2}>
                    <TextField
                        fullWidth
                        variant="outlined"
                        placeholder="Explain the concept..."
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        multiline
                        maxRows={4}
                    />
                    {/* Interim Text Display */}
                    {isListening && interimText && (
                        <Typography variant="caption" color="textSecondary" sx={{ position: 'absolute', bottom: -20, left: 16 }}>
                            Listening: {interimText}...
                        </Typography>
                    )}
                    <IconButton
                        color={isListening ? 'error' : 'default'}
                        onClick={toggleListening}
                        sx={{
                            animation: isListening ? 'pulse 1.5s infinite' : 'none',
                            '@keyframes pulse': {
                                '0%': { boxShadow: '0 0 0 0 rgba(255, 0, 0, 0.7)' },
                                '70%': { boxShadow: '0 0 0 10px rgba(255, 0, 0, 0)' },
                                '100%': { boxShadow: '0 0 0 0 rgba(255, 0, 0, 0)' }
                            }
                        }}
                    >
                        {isListening ? <StopIcon /> : <MicIcon />}
                    </IconButton>
                    <IconButton color="primary" onClick={handleSendMessage} disabled={!inputMessage.trim()}>
                        <SendIcon fontSize="large" />
                    </IconButton>
                </Box>
            </Paper>
        </Container>
    );

    const renderReport = () => (
        <Container maxWidth="md" sx={{ mt: 4 }}>
            <Paper elevation={3} sx={{ p: 4, borderRadius: 4 }}>
                <Typography variant="h4" gutterBottom align="center" sx={{ fontWeight: 'bold', mb: 4 }}>
                    Mastery Report
                </Typography>

                <Grid container spacing={3} sx={{ mb: 4 }}>
                    <Grid item xs={12} md={4}>
                        <Card sx={{ textAlign: 'center', p: 2, bgcolor: '#e8f5e9' }}>
                            <Typography variant="h6" color="textSecondary">Overall Score</Typography>
                            <Typography variant="h2" color="success.main" sx={{ fontWeight: 'bold' }}>
                                {report.score}
                            </Typography>
                        </Card>
                    </Grid>
                    <Grid item xs={6} md={4}>
                        <Card sx={{ textAlign: 'center', p: 2 }}>
                            <Typography variant="subtitle1" color="textSecondary">Clarity</Typography>
                            <CircularProgress variant="determinate" value={report.clarity_score} size={60} thickness={4} color="primary" />
                            <Typography variant="h5" sx={{ mt: 1 }}>{report.clarity_score}%</Typography>
                        </Card>
                    </Grid>
                    <Grid item xs={6} md={4}>
                        <Card sx={{ textAlign: 'center', p: 2 }}>
                            <Typography variant="subtitle1" color="textSecondary">Depth</Typography>
                            <CircularProgress variant="determinate" value={report.depth_score} size={60} thickness={4} color="secondary" />
                            <Typography variant="h5" sx={{ mt: 1 }}>{report.depth_score}%</Typography>
                        </Card>
                    </Grid>
                </Grid>

                <Divider sx={{ my: 3 }} />

                <Typography variant="h6" gutterBottom>
                    <IdeaIcon sx={{ verticalAlign: 'middle', mr: 1, color: 'orange' }} />
                    Feedback & Insights
                </Typography>
                <Paper elevation={0} sx={{ p: 3, bgcolor: '#fff3e0', borderRadius: 2 }}>
                    <Typography variant="body1" style={{ whiteSpace: 'pre-line' }}>
                        {report.feedback}
                    </Typography>
                </Paper>

                <Box sx={{ mt: 4, textAlign: 'center' }}>
                    <Button
                        variant="contained"
                        size="large"
                        onClick={() => {
                            setStep('setup');
                            setTopic('');
                            setMessages([]);
                            setReport(null);
                        }}
                    >
                        Start New Session
                    </Button>
                </Box>
            </Paper>
        </Container>
    );

    const [tab, setTab] = useState(0);

    const handleTabChange = (event, newValue) => {
        setTab(newValue);
    };

    return (
        <Box sx={{ minHeight: '100vh', bgcolor: '#f4f6f8', pb: 4 }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'white', mb: 0 }}>
                <Container maxWidth="lg">
                    <Tabs value={tab} onChange={handleTabChange} centered>
                        <Tab label="Teaching Session" sx={{ fontWeight: 'bold' }} />
                        <Tab label="Community Discussion" sx={{ fontWeight: 'bold' }} />
                    </Tabs>
                </Container>
            </Box>

            {tab === 0 && (
                <>
                    {step === 'setup' && renderSetup()}
                    {step === 'teaching' && renderChat()}
                    {step === 'report' && renderReport()}
                </>
            )}

            {tab === 1 && (
                <Container maxWidth="lg" sx={{ mt: 4 }}>
                    <Community />
                </Container>
            )}
        </Box>
    );
};

export default FeynmanBoard;
