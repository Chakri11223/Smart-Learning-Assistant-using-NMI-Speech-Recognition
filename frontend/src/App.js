import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link, Outlet, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Card,
  CardContent,
  Grid,
  Button,
  Paper,
  CssBaseline,
  IconButton,
  Stack,
  Avatar,
  Menu,
  MenuItem,
  ListItemIcon,
  Divider,
  Tooltip,
  GlobalStyles
} from '@mui/material';
import Settings from '@mui/icons-material/Settings';
import Logout from '@mui/icons-material/Logout';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import VoiceQA from './pages/VoiceQA';

import QuizGenerator from './pages/QuizGenerator';
import VideoSummarizer from './pages/VideoSummarizer';
import LearningPath from './pages/LearningPath';
import QuizTaker from './pages/QuizTaker';
import Analytics from './pages/Analytics';
import Login from './pages/Login';
import Signup from './pages/Signup';
import VerifyEmail from './pages/VerifyEmail';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import FeynmanBoard from './pages/FeynmanBoard';
import SettingsPage from './pages/Settings';
import ErrorBoundary from './components/ErrorBoundary';
import RequireAuth from './components/RequireAuth';
import AppLayout from './components/AppLayout';

function App() {
  const prefersDark =
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-color-scheme: dark)').matches;

  const savedTheme = (() => {
    try {
      return localStorage.getItem('theme');
    } catch {
      return null;
    }
  })();

  const initialMode = savedTheme ? savedTheme : prefersDark ? 'dark' : 'light';
  const [themeMode, setThemeMode] = React.useState(
    initialMode === 'dark' ? 'dark' : 'light'
  );
  const [fontSize, setFontSize] = React.useState('medium'); // small, medium, large
  const [authUser, setAuthUser] = React.useState(() => {
    try {
      const savedUser = localStorage.getItem('authUser');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });


  const [news, setNews] = React.useState([]);

  React.useEffect(() => {
    fetch('http://127.0.0.1:5000/api/news')
      .then((res) => res.json())
      .then((data) => {
        if (data.articles) {
          setNews(data.articles);
        }
      })
      .catch((err) => console.error('Failed to fetch news:', err));
  }, []);





  const theme = React.useMemo(
    () =>
      createTheme({
        palette: {
          mode: themeMode,
          ...(themeMode === 'dark'
            ? {
              primary: { main: '#3B82F6', light: '#60A5FA', dark: '#2563EB' }, // Blue 500
              secondary: { main: '#94A3B8', light: '#CBD5E1', dark: '#64748B' }, // Slate 400
              background: { default: '#0F172A', paper: '#1E293B' }, // Slate 900/800
              text: { primary: '#F1F5F9', secondary: '#94A3B8' }, // Slate 100/400
              divider: 'rgba(148, 163, 184, 0.12)',
            }
            : {
              primary: { main: '#2563EB', light: '#3B82F6', dark: '#1D4ED8' }, // Blue 600
              secondary: { main: '#475569', light: '#64748B', dark: '#334155' }, // Slate 600
              background: { default: '#F8FAFC', paper: '#FFFFFF' }, // Slate 50
              text: { primary: '#0F172A', secondary: '#64748B' }, // Slate 900/500
              divider: 'rgba(0, 0, 0, 0.06)',
            }),
        },
        typography: {
          fontFamily: "'Inter', sans-serif",
          fontSize: fontSize === 'small' ? 12 : fontSize === 'large' ? 16 : 14,
          h1: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, letterSpacing: '-0.025em' },
          h2: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, letterSpacing: '-0.025em' },
          h3: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, letterSpacing: '-0.025em', fontSize: '2rem' },
          h4: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 600, letterSpacing: '-0.025em', fontSize: '1.75rem' },
          h5: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 600, fontSize: '1.25rem' },
          h6: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 600, fontSize: '1.1rem' },
          subtitle1: { fontFamily: "'Inter', sans-serif", fontSize: '1rem', letterSpacing: '-0.01em' },
          body1: { fontFamily: "'Inter', sans-serif", fontSize: '1rem', lineHeight: 1.6 },
          button: { fontFamily: "'Inter', sans-serif", fontWeight: 600, letterSpacing: '0.01em', textTransform: 'none' },
        },
        shape: {
          borderRadius: 12, // Modern, softer corners
        },
        components: {
          MuiButton: {
            defaultProps: {
              disableElevation: true,
            },
            styleOverrides: {
              root: {
                padding: '10px 24px',
                borderRadius: '10px',
                transition: 'all 0.2s ease-in-out',
              },
              containedPrimary: {
                background: themeMode === 'dark'
                  ? 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)'
                  : 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                '&:hover': {
                  boxShadow: '0 4px 12px rgba(37, 99, 235, 0.2)',
                  transform: 'translateY(-1px)',
                }
              },
            },
          },
          MuiAppBar: {
            styleOverrides: {
              root: {
                backgroundColor: themeMode === 'dark' ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(12px)',
                borderBottom: `1px solid ${themeMode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'}`,
                color: themeMode === 'dark' ? '#F1F5F9' : '#0F172A',
                boxShadow: 'none',
              },
            },
          },
          MuiCard: {
            styleOverrides: {
              root: {
                borderRadius: '16px',
                boxShadow: themeMode === 'dark'
                  ? '0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3)'
                  : '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
                border: `1px solid ${themeMode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'}`,
                backgroundImage: 'none',
              },
            },
          },
          MuiPaper: {
            styleOverrides: {
              root: {
                backgroundImage: 'none',
              },
            },
          },
          MuiTextField: {
            styleOverrides: {
              root: {
                '& .MuiOutlinedInput-root': {
                  borderRadius: '12px',
                  '& fieldset': {
                    borderColor: themeMode === 'dark' ? 'rgba(148, 163, 184, 0.2)' : 'rgba(148, 163, 184, 0.3)',
                  },
                  '&:hover fieldset': {
                    borderColor: themeMode === 'dark' ? '#60A5FA' : '#3B82F6',
                  },
                }
              }
            }
          }
        },
      }),
    [themeMode, fontSize]
  );

  const handleAuthSuccess = (user) => {
    setAuthUser(user);
  };

  const handleLogout = () => {
    setAuthUser(null);
    try {
      localStorage.removeItem('authToken');
      localStorage.removeItem('authUser');
    } catch (err) {
      console.warn('Failed to clear auth storage', err);
    }
  };



  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ErrorBoundary>
        <Router>
          <Routes>
            <Route element={
              <RequireAuth user={authUser}>
                <AppLayout
                  authUser={authUser}
                  themeMode={themeMode}
                  toggleTheme={() => {
                    const next = themeMode === 'dark' ? 'light' : 'dark';
                    setThemeMode(next);
                    try {
                      localStorage.setItem('theme', next);
                    } catch {
                      /* noop */
                    }
                  }}
                  onLogout={handleLogout}
                />
              </RequireAuth>
            }>
              <Route path="/voice-qa" element={<VoiceQA />} />
              <Route path="/quiz-generator" element={<QuizGenerator />} />
              <Route path="/video" element={<VideoSummarizer />} />
              <Route path="/learning" element={<LearningPath />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/feynman" element={<FeynmanBoard />} />

              <Route path="/settings" element={
                <SettingsPage
                  authUser={authUser}
                  themeMode={themeMode}
                  toggleTheme={() => setThemeMode(prev => prev === 'dark' ? 'light' : 'dark')}
                  fontSize={fontSize}
                  setFontSize={setFontSize}
                />
              } />
              <Route
                path="/"
                element={
                  <Box>
                    <Typography
                      variant="h4"
                      component="h1"
                      gutterBottom
                      align="center"
                      sx={{
                        color: '#1976d2',
                        mb: 4,
                        fontWeight: 'bold',
                        fontSize: { xs: '1.6rem', md: '2.1rem' },
                      }}
                    >
                      Welcome to Smart Learning Assistant
                    </Typography>
                    <Typography
                      variant="body1"
                      align="center"
                      sx={{
                        mb: 4,
                        color: '#666',
                        fontSize: { xs: '0.95rem', md: '1.05rem' },
                        lineHeight: 1.5,
                      }}
                    >
                      Your AI-powered companion for enhanced learning and education
                    </Typography>

                    <Grid container spacing={3}>
                      <Grid item xs={12} md={3}>
                        <Card
                          sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            boxShadow: 4,
                            borderRadius: 3,
                            transition: 'transform 0.3s ease-in-out',
                            '&:hover': {
                              transform: 'translateY(-8px)',
                              boxShadow: 8,
                            },
                          }}
                        >
                          <CardContent sx={{ flexGrow: 1, p: 2.5, display: 'flex', flexDirection: 'column' }}>
                            <Typography
                              variant="h4"
                              component="h2"
                              gutterBottom
                              sx={{
                                color: '#1976d2',
                                fontWeight: 'bold',
                                mb: 3,
                              }}
                            >
                              Voice Q&A
                            </Typography>
                            <Typography
                              variant="h6"
                              paragraph
                              sx={{
                                lineHeight: 1.8,
                                color: '#555',
                                mb: 4,
                                flexGrow: 1
                              }}
                            >
                              Ask questions using your voice and get instant AI-powered answers. Perfect for hands-free learning
                              and accessibility.
                            </Typography>
                            <Link to="/voice-qa" style={{ textDecoration: 'none', marginTop: 'auto' }}>
                              <Button
                                variant="contained"
                                size="small"
                                sx={{
                                  width: '100%',
                                  height: '36px',
                                  fontSize: '14px',
                                  fontWeight: 'bold',
                                  borderRadius: 2,
                                }}
                              >
                                Try Voice Q&A
                              </Button>
                            </Link>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <Card
                          sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            boxShadow: 4,
                            borderRadius: 3,
                            transition: 'transform 0.3s ease-in-out',
                            '&:hover': {
                              transform: 'translateY(-8px)',
                              boxShadow: 8,
                            },
                          }}
                        >
                          <CardContent sx={{ flexGrow: 1, p: 2.5, display: 'flex', flexDirection: 'column' }}>
                            <Typography
                              variant="h4"
                              component="h2"
                              gutterBottom
                              sx={{
                                color: '#1976d2',
                                fontWeight: 'bold',
                                mb: 3,
                                fontSize: '1.5rem'
                              }}
                            >
                              PDF Quiz Generator
                            </Typography>
                            <Typography
                              variant="h6"
                              paragraph
                              sx={{
                                lineHeight: 1.8,
                                color: '#555',
                                mb: 4,
                                flexGrow: 1
                              }}
                            >
                              Upload PDF documents and automatically generate quizzes to test your knowledge and track your
                              progress.
                            </Typography>
                            <Link to="/quiz-generator" style={{ textDecoration: 'none', marginTop: 'auto' }}>
                              <Button
                                variant="contained"
                                size="small"
                                sx={{
                                  width: '100%',
                                  height: '36px',
                                  fontSize: '14px',
                                  fontWeight: 'bold',
                                  borderRadius: 2,
                                }}
                              >
                                Open Quiz Generator
                              </Button>
                            </Link>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <Card
                          sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            boxShadow: 4,
                            borderRadius: 3,
                            transition: 'transform 0.3s ease-in-out',
                            '&:hover': {
                              transform: 'translateY(-8px)',
                              boxShadow: 8,
                            },
                          }}
                        >
                          <CardContent sx={{ flexGrow: 1, p: 2.5, display: 'flex', flexDirection: 'column' }}>
                            <Typography
                              variant="h4"
                              component="h2"
                              gutterBottom
                              sx={{
                                color: '#1976d2',
                                fontWeight: 'bold',
                                mb: 3,
                              }}
                            >
                              Video Summarizer
                            </Typography>
                            <Typography
                              variant="h6"
                              paragraph
                              sx={{
                                lineHeight: 1.8,
                                color: '#555',
                                mb: 4,
                                flexGrow: 1
                              }}
                            >
                              Upload lecture videos and get AI-generated summaries and key points for efficient learning.
                            </Typography>
                            <Button
                              variant="contained"
                              size="small"
                              component={Link}
                              to="/video"
                              sx={{
                                marginTop: 'auto',
                                width: '100%',
                                height: '36px',
                                fontSize: '14px',
                                fontWeight: 'bold',
                                borderRadius: 2,
                              }}
                            >
                              Open Summarizer
                            </Button>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <Card
                          sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            boxShadow: 4,
                            borderRadius: 3,
                            transition: 'transform 0.3s ease-in-out',
                            '&:hover': {
                              transform: 'translateY(-8px)',
                              boxShadow: 8,
                            },
                          }}
                        >
                          <CardContent sx={{ flexGrow: 1, p: 2.5, display: 'flex', flexDirection: 'column' }}>
                            <Typography
                              variant="h4"
                              component="h2"
                              gutterBottom
                              sx={{
                                color: '#1976d2',
                                fontWeight: 'bold',
                                mb: 3,
                              }}
                            >
                              Explain & Learn
                            </Typography>
                            <Typography
                              variant="h6"
                              paragraph
                              sx={{
                                lineHeight: 1.8,
                                color: '#555',
                                mb: 4,
                                flexGrow: 1
                              }}
                            >
                              Teach a concept to an AI persona to test your understanding and get a mastery score.
                            </Typography>
                            <Button
                              variant="contained"
                              size="small"
                              component={Link}
                              to="/feynman"
                              sx={{
                                marginTop: 'auto',
                                width: '100%',
                                height: '36px',
                                fontSize: '14px',
                                fontWeight: 'bold',
                                borderRadius: 2,
                              }}
                            >
                              Start Teaching
                            </Button>
                          </CardContent>
                        </Card>
                      </Grid>
                    </Grid>

                    {/* Daily News Headlines Section */}
                    <Box sx={{ mt: 8, mb: 4 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                        <Typography
                          variant="h4"
                          component="h2"
                          sx={{
                            color: '#1976d2',
                            fontWeight: 'bold',
                            fontSize: '1.8rem',
                          }}
                        >
                          Daily News Headlines
                        </Typography>
                        <Tooltip title="Refresh Headlines" arrow>
                          <IconButton
                            onClick={() => {
                              setNews([]);
                              fetch('http://127.0.0.1:5000/api/news')
                                .then((res) => res.json())
                                .then((data) => {
                                  if (data.articles) setNews(data.articles);
                                })
                                .catch((err) => console.error('Failed to refresh news:', err));
                            }}
                            sx={{
                              color: 'primary.main',
                              bgcolor: themeMode === 'dark' ? 'rgba(25, 118, 210, 0.1)' : 'rgba(25, 118, 210, 0.05)',
                              transition: 'all 0.4s ease',
                              '&:hover': {
                                bgcolor: themeMode === 'dark' ? 'rgba(25, 118, 210, 0.2)' : 'rgba(25, 118, 210, 0.1)',
                                transform: 'rotate(180deg)'
                              }
                            }}
                            aria-label="refresh news"
                          >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M23 4v6h-6"></path>
                              <path d="M1 20v-6h6"></path>
                              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                            </svg>
                          </IconButton>
                        </Tooltip>
                      </Box>

                      <Stack spacing={2} sx={{ width: '100%' }}>
                        {news.length === 0 ? (
                          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                            <Typography color="text.secondary">Updating news feed...</Typography>
                          </Box>
                        ) : (
                          news.map((article, index) => (
                            <Card
                              key={index}
                              sx={{
                                display: 'flex',
                                flexDirection: 'column',
                                background: themeMode === 'dark'
                                  ? 'rgba(255, 255, 255, 0.03)'
                                  : 'rgba(255, 255, 255, 0.6)',
                                backdropFilter: 'blur(12px)',
                                boxShadow: '0 4px 30px rgba(0, 0, 0, 0.05)',
                                border: '1px solid',
                                borderColor: themeMode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(255, 255, 255, 0.3)',
                                borderRadius: '16px',
                                transition: 'all 0.3s ease',
                                '&:hover': {
                                  transform: 'translateX(8px)',
                                  background: themeMode === 'dark'
                                    ? 'rgba(255, 255, 255, 0.06)'
                                    : 'rgba(255, 255, 255, 0.9)',
                                  boxShadow: '0 8px 30px rgba(0, 0, 0, 0.08)',
                                  borderColor: 'primary.main',
                                },
                              }}
                            >
                              <CardContent sx={{ px: 3, py: 2.5 }}>
                                <Typography variant="h6" component="div" sx={{ fontSize: '1.1rem', fontWeight: 700, mb: 1, letterSpacing: '-0.01em' }}>
                                  <a
                                    href={article.link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ textDecoration: 'none', color: themeMode === 'dark' ? '#E2E8F0' : '#1E293B' }}
                                  >
                                    {article.title}
                                  </a>
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, lineHeight: 1.6 }}>
                                  {article.summary}
                                </Typography>
                                {article.published && (
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: 'primary.main', opacity: 0.6 }} />
                                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500, opacity: 0.8 }}>
                                      {new Date(article.published).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}
                                    </Typography>
                                  </Box>
                                )}
                              </CardContent>
                            </Card>
                          ))
                        )}
                      </Stack>
                    </Box>
                  </Box>
                }
              />
            </Route>
            <Route path="/login" element={<Login onAuthSuccess={handleAuthSuccess} />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/verify-email" element={<VerifyEmail onAuthSuccess={handleAuthSuccess} />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/take-quiz" element={<RequireAuth user={authUser}><QuizTaker /></RequireAuth>} />
          </Routes>
        </Router>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
