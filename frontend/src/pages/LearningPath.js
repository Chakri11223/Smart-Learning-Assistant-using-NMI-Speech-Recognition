import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Stack,
  Alert,
  Button,
  TextField,
  MenuItem,
  LinearProgress,
  IconButton,
  Tooltip,
  Grid,
  Container,
  CircularProgress
} from "@mui/material";
import { Search, Quiz, PlayArrow, CheckCircle, RadioButtonUnchecked, Code } from "@mui/icons-material";
import { Checkbox, FormControlLabel, CircularProgress as MuiCircularProgress } from '@mui/material';

const LearningPath = () => {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(() => {
    try {
      const userStr = localStorage.getItem('authUser');
      const user = userStr ? JSON.parse(userStr) : null;
      return user && user.id ? String(user.id) : "demo";
    } catch (e) {
      console.error("Error parsing auth user", e);
      return "demo";
    }
  });
  const [stats, setStats] = useState(null);
  const [recs, setRecs] = useState(null);
  const [skills, setSkills] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [topic, setTopic] = useState("Data Structures");
  const [level, setLevel] = useState("beginner");
  const [durationWeeks, setDurationWeeks] = useState(2);
  const [plan, setPlan] = useState(null);
  const [savedPaths, setSavedPaths] = useState([]);
  const [activeTab, setActiveTab] = useState(0); // 0: Generate, 1: Saved

  const load = async () => {
    setError("");
    setLoading(true);
    try {
      const headers = {};
      if (sessionId !== "demo") {
        headers['X-User-Id'] = sessionId;
      }

      const [statsResponse, recsResponse, skillsResponse, pathsResponse] = await Promise.all([
        axios.get(`http://localhost:5000/api/analytics/user/${encodeURIComponent(sessionId)}`, { headers }),
        axios.get(
          `http://localhost:5000/api/recommendations/${encodeURIComponent(sessionId)}`, { headers }
        ),
        axios.get(
          `http://localhost:5000/api/learning-path/skills/${encodeURIComponent(sessionId)}`, { headers }
        ),
        axios.get('http://localhost:5000/api/learning-paths', { headers })
      ]);
      setStats(statsResponse.data);
      setRecs(recsResponse.data);
      setSkills(skillsResponse.data);
      setSavedPaths(pathsResponse.data.paths || []);
    } catch (e) {
      const axiosError = e;
      setError(axiosError.response?.data?.error || axiosError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [sessionId]);

  const handlePlanGenerate = async () => {
    setError("");
    setPlan(null);
    try {
      const res = await axios.post("http://localhost:5000/api/learning-path-plan", {
        topic,
        level,
        durationWeeks
      });
      setPlan(res.data);
    } catch (e) {
      const axiosError = e;
      setError(axiosError.response?.data?.error || axiosError.message);
    }
  };

  const handleSavePlan = async () => {
    if (!plan) return;
    try {
      const headers = {};
      if (sessionId !== "demo") {
        headers['X-User-Id'] = sessionId;
      }
      await axios.post("http://localhost:5000/api/learning-path/save", {
        topic: plan.topic,
        level: plan.level,
        plan: plan.plan
      }, { headers });
      alert("Roadmap saved successfully!");
      load(); // Refresh saved paths
      setActiveTab(1); // Switch to saved tab
    } catch (e) {
      console.error("Failed to save plan", e);
      alert("Failed to save roadmap.");
    }
  };

  const handleStepAction = async (pathId, stepId, action) => {
    try {
      const headers = {};
      if (sessionId !== "demo") {
        headers['X-User-Id'] = sessionId;
      }

      const res = await axios.post(`http://localhost:5000/api/learning-path/step/${stepId}/action`, { action }, { headers });

      // Update local state
      // For saved paths list
      setSavedPaths(prev => prev.map(p => {
        if (p.id === pathId) {
          return { ...p, progress: res.data.path_progress };
        }
        return p;
      }));

      // For selected path detail view
      if (selectedPath && selectedPath.id === pathId) {
        setSelectedPath(prev => ({
          ...prev,
          steps: prev.steps.map(s => {
            if (s.id === stepId) return res.data.step;
            // Wait, res.data.step is the updated step dictionary
            // We need to match ID
            return s.id === stepId ? res.data.step : s;
          })
        }));

        // Also need to re-fetch path details to get fresh state if complex logic happened on backend?
        // But res.data.step should be enough.
        // Actually, let's just update the specific step in selectedPath
        setSelectedPath(prev => {
          if (!prev) return null;
          return {
            ...prev,
            steps: prev.steps.map(s => s.id === stepId ? res.data.step : s)
          };
        });
      }
    } catch (e) {
      console.error("Failed to update step action", e);
    }
  };

  const [selectedPath, setSelectedPath] = useState(null);

  const loadSavedPathDetails = async (pathId) => {
    try {
      const headers = {};
      if (sessionId !== "demo") {
        headers['X-User-Id'] = sessionId;
      }
      const res = await axios.get(`http://localhost:5000/api/learning-path/${pathId}`, { headers });
      setSelectedPath(res.data.path);
    } catch (e) {
      console.error("Failed to load path details", e);
    }
  };

  const handleDeletePath = async (pathId) => {
    if (!window.confirm("Delete this roadmap?")) return;
    try {
      const headers = {};
      if (sessionId !== "demo") {
        headers['X-User-Id'] = sessionId;
      }
      await axios.delete(`http://localhost:5000/api/learning-path/${pathId}`, { headers });
      load();
      setSelectedPath(null);
    } catch (e) {
      console.error("Failed to delete path", e);
    }
  };

  const handlePractice = (topic) => {
    navigate('/quiz-generator', { state: { topic } });
  };

  const handleSearch = (query) => {
    window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, '_blank');
  };

  const handleDeleteTopic = async (topic) => {
    if (!window.confirm(`Are you sure you want to remove "${topic}" from your learning path? This will hide related quiz history.`)) return;
    try {
      const headers = {};
      if (sessionId !== "demo") {
        headers['X-User-Id'] = sessionId;
      }
      await axios.post('http://localhost:5000/api/learning-path/dismiss-topic', { topic }, { headers });
      load(); // Refresh data
    } catch (e) {
      console.error("Failed to dismiss topic", e);
    }
  };

  const handleRestartProgress = async () => {
    if (!window.confirm("Are you sure you want to RESET ALL PROGRESS? This cannot be undone.")) return;
    try {
      const headers = {};
      if (sessionId !== "demo") {
        headers['X-User-Id'] = sessionId;
      }
      await axios.post('http://localhost:5000/api/learning-path/reset', {}, { headers });
      load(); // Refresh data
    } catch (e) {
      console.error("Failed to reset progress", e);
    }
  };

  if (loading && !stats) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ py: 4, bgcolor: 'background.default', minHeight: '100vh' }}>
      <Container maxWidth="xl">
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={4}>
          <Box>
            <Typography variant="h4" fontWeight="800" gutterBottom sx={{ color: 'primary.main' }}>
              Your Learning Path
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              AI-driven roadmap based on your quiz performance
            </Typography>
          </Box>
          <Button
            variant="outlined"
            color="error"
            onClick={handleRestartProgress}
          >
            Restart Progress
          </Button>
        </Stack>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Button
            onClick={() => setActiveTab(0)}
            sx={{ mr: 2, borderBottom: activeTab === 0 ? '2px solid' : 'none', borderRadius: 0 }}
            color={activeTab === 0 ? "primary" : "inherit"}
          >
            Generate New
          </Button>
          <Button
            onClick={() => setActiveTab(1)}
            sx={{ borderBottom: activeTab === 1 ? '2px solid' : 'none', borderRadius: 0 }}
            color={activeTab === 1 ? "primary" : "inherit"}
          >
            Saved Roadmaps
          </Button>
        </Box>

        {activeTab === 0 ? (
          <Grid container spacing={4}>
            {/* Left Column: Stats & Skills */}
            <Grid item xs={12} md={4}>
              <Stack spacing={4}>
                {/* Overall Progress Card */}
                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="h6" fontWeight="700" gutterBottom>
                      Overall Mastery
                    </Typography>
                    <Box sx={{ position: 'relative', display: 'inline-flex', mb: 2 }}>
                      <CircularProgress
                        variant="determinate"
                        value={skills?.overall?.masteryScore || 0}
                        size={120}
                        thickness={4}
                        sx={{ color: 'primary.main' }}
                      />
                      <Box
                        sx={{
                          top: 0,
                          left: 0,
                          bottom: 0,
                          right: 0,
                          position: 'absolute',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <Typography variant="h4" component="div" color="text.primary" fontWeight="800">
                          {skills?.overall?.masteryScore || 0}%
                        </Typography>
                      </Box>
                    </Box>
                    <Stack spacing={1}>
                      <Stack direction="row" justifyContent="space-between">
                        <Typography variant="body2" color="text.secondary">Questions Answered</Typography>
                        <Typography variant="body2" fontWeight="600">{skills?.overall?.questionsAnswered || 0}</Typography>
                      </Stack>
                      <Stack direction="row" justifyContent="space-between">
                        <Typography variant="body2" color="text.secondary">Correct Answers</Typography>
                        <Typography variant="body2" fontWeight="600">{skills?.overall?.questionsCorrect || 0}</Typography>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>

                {/* Gamification: XP & Badges */}
                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="h6" fontWeight="700" gutterBottom>
                      Achievements
                    </Typography>
                    <Stack spacing={2}>
                      <Box>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                          <Typography variant="subtitle2" fontWeight="600">XP Progress</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {(skills?.overall?.questionsCorrect || 0) * 10} / {((Math.floor(((skills?.overall?.questionsCorrect || 0) * 10) / 100) + 1) * 100)} XP
                          </Typography>
                        </Stack>
                        <LinearProgress
                          variant="determinate"
                          value={((skills?.overall?.questionsCorrect || 0) * 10) % 100}
                          sx={{ height: 8, borderRadius: 4 }}
                        />
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                          Level {Math.floor(((skills?.overall?.questionsCorrect || 0) * 10) / 100) + 1}
                        </Typography>
                      </Box>

                      <Box>
                        <Typography variant="subtitle2" fontWeight="600" gutterBottom>Badges</Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap">
                          {(skills?.overall?.questionsAnswered || 0) >= 1 && (
                            <Chip label="Novice" size="small" color="primary" variant="outlined" />
                          )}
                          {(skills?.overall?.questionsAnswered || 0) >= 10 && (
                            <Chip label="Scholar" size="small" color="secondary" variant="outlined" />
                          )}
                          {(skills?.overall?.masteryScore || 0) >= 80 && (
                            <Chip label="Master" size="small" color="success" variant="outlined" />
                          )}
                          {(skills?.overall?.questionsCorrect || 0) >= 50 && (
                            <Chip label="Expert" size="small" color="warning" variant="outlined" />
                          )}
                          {!(skills?.overall?.questionsAnswered) && (
                            <Typography variant="caption" color="text.secondary">Start learning to earn badges!</Typography>
                          )}
                        </Stack>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>

                {/* Skill Map */}
                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="h6" fontWeight="700" gutterBottom>
                      Skill Map
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {skills?.skills?.map((skill) => (
                        <Tooltip key={skill.id} title={`${skill.masteryScore}% Mastery - ${skill.recommendedNext}`}>
                          <Chip
                            label={skill.name}
                            color={
                              skill.strengthBand === 'strong' ? 'success' :
                                skill.strengthBand === 'medium' ? 'warning' : 'error'
                            }
                            variant={skill.strengthBand === 'strong' ? 'filled' : 'outlined'}
                            onClick={() => handlePractice(skill.name)}
                            onDelete={() => handleDeleteTopic(skill.name)}
                            sx={{ cursor: 'pointer' }}
                          />
                        </Tooltip>
                      ))}
                      {!skills?.skills?.length && (
                        <Typography variant="body2" color="text.secondary">
                          Take quizzes to map your skills.
                        </Typography>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Stack>
            </Grid>

            {/* Right Column: Recommendations & Plan */}
            <Grid item xs={12} md={8}>
              <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid', borderColor: 'divider', mb: 4 }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" fontWeight="700" gutterBottom>
                    Generate New Plan
                  </Typography>
                  <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 2 }}>
                    <TextField label="Topic" value={topic} onChange={(e) => setTopic(e.target.value)} sx={{ minWidth: 240 }} />
                    <TextField
                      select
                      label="Level"
                      value={level}
                      onChange={(e) => setLevel(e.target.value)}
                      sx={{ minWidth: 180 }}
                    >
                      <MenuItem value="beginner">Beginner</MenuItem>
                      <MenuItem value="intermediate">Intermediate</MenuItem>
                      <MenuItem value="advanced">Advanced</MenuItem>
                    </TextField>
                    <TextField
                      type="number"
                      label="Duration (weeks)"
                      value={durationWeeks}
                      onChange={(e) => setDurationWeeks(Number(e.target.value) || 2)}
                      sx={{ minWidth: 180 }}
                    />
                    <Button variant="contained" onClick={handlePlanGenerate}>
                      Generate Plan
                    </Button>
                  </Box>

                  {recs ? <Box>
                    {(recs.strengths ?? []).length > 0 && <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                        Strengths
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        {(recs.strengths ?? []).map((s, i) => <Chip key={i} label={`${s.topic} (${s.accuracy}%)`} color="success" variant="outlined" />)}
                      </Stack>
                    </Box>}
                    {(recs.weaknesses ?? []).length > 0 && <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                        Focus Areas
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        {(recs.weaknesses ?? []).map((w, i) => (
                          <Chip
                            key={i}
                            label={`${w.topic} (${w.accuracy}%)`}
                            color="warning"
                            variant="outlined"
                            onClick={() => handlePractice(w.topic)}
                            onDelete={() => handleDeleteTopic(w.topic)}
                            sx={{ cursor: 'pointer' }}
                          />
                        ))}
                      </Stack>
                    </Box>}
                    <Box>
                      <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                        Next Steps
                      </Typography>
                      {(recs.recommendations ?? []).map((r, i) => <Typography key={i} variant="body2" sx={{ mb: 1 }}>
                        • {r.topic}: {r.action} — {r.details}
                      </Typography>)}
                    </Box>
                  </Box> : <Typography>Loading recommendations...</Typography>}
                </CardContent>
              </Card>

              {plan && (
                <Box>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
                    <Typography variant="h6" fontWeight="700">
                      Personalized Roadmap
                    </Typography>
                    <Button variant="contained" color="secondary" onClick={handleSavePlan}>
                      Save Roadmap
                    </Button>
                  </Stack>

                  <Box sx={{ position: 'relative', pl: 2 }}>
                    {/* Vertical Line */}
                    <Box sx={{
                      position: 'absolute',
                      left: 28,
                      top: 0,
                      bottom: 0,
                      width: 2,
                      bgcolor: 'primary.light',
                      opacity: 0.3
                    }} />

                    {Array.isArray(plan.plan) ? plan.plan.map((step, index) => (
                      <Box key={index} sx={{ display: 'flex', mb: 3, position: 'relative' }}>
                        {/* Step Number Circle */}
                        <Box sx={{
                          width: 40,
                          height: 40,
                          borderRadius: '50%',
                          bgcolor: 'primary.main',
                          color: 'white',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 'bold',
                          zIndex: 1,
                          mr: 2,
                          flexShrink: 0
                        }}>
                          {step.step || index + 1}
                        </Box>

                        {/* Content Card */}
                        <Card sx={{ flex: 1, borderRadius: 2, boxShadow: 1 }}>
                          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <Box>
                                <Typography variant="subtitle1" fontWeight="bold" color="primary.dark">
                                  {step.title}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                  {step.details}
                                </Typography>
                              </Box>
                              <Tooltip title="Practice this topic">
                                <IconButton
                                  color="primary"
                                  onClick={() => handlePractice(step.title)}
                                  sx={{ ml: 1, bgcolor: 'primary.50', '&:hover': { bgcolor: 'primary.100' } }}
                                >
                                  <Quiz />
                                </IconButton>
                              </Tooltip>
                            </Box>

                            {step.videoLink && (
                              <Box sx={{ mt: 2 }}>
                                <Button
                                  variant="outlined"
                                  startIcon={<PlayArrow />}
                                  href={step.videoLink}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  sx={{ textTransform: 'none', mb: 1, mr: 1 }}
                                >
                                  Watch: {step.videoTitle || 'Related Video'}
                                </Button>
                                {step.videoViews && (
                                  <Typography variant="caption" display="inline" color="text.secondary">
                                    {step.videoViews} views
                                  </Typography>
                                )}
                              </Box>
                            )}

                            {step.codingLink && (
                              <Box sx={{ mt: 1 }}>
                                <Button
                                  variant="outlined"
                                  color="success"
                                  size="small"
                                  href={step.codingLink}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  sx={{ textTransform: 'none' }}
                                >
                                  Practice Coding
                                </Button>
                              </Box>
                            )}

                            {step.videoQuery && !step.videoLink && (
                              <Chip
                                icon={<Search sx={{ fontSize: '1rem !important' }} />}
                                label={`Search: ${step.videoQuery}`}
                                size="small"
                                variant="outlined"
                                onClick={() => handleSearch(step.videoQuery)}
                                sx={{ mt: 1.5, fontSize: '0.7rem', cursor: 'pointer' }}
                              />
                            )}
                          </CardContent>
                        </Card>
                      </Box>
                    )) : (
                      <Typography color="error">
                        Plan format error. Please regenerate.
                      </Typography>
                    )}
                  </Box>
                  <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                    Suggested Video Queries
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    {(plan.videoQueries || []).map((q, i) => (
                      <Chip
                        key={i}
                        label={q}
                        icon={<Search sx={{ fontSize: '1rem !important' }} />}
                        onClick={() => handleSearch(q)}
                        sx={{ cursor: 'pointer' }}
                      />
                    ))}
                  </Stack>
                </Box>
              )}
            </Grid>
          </Grid>
        ) : (
          <Grid container spacing={4}>
            <Grid item xs={12} md={4}>
              <Typography variant="h6" gutterBottom>Saved Roadmaps</Typography>
              <Stack spacing={2}>
                {savedPaths.length === 0 && <Typography color="text.secondary">No saved roadmaps.</Typography>}
                {savedPaths.map(path => (
                  <Card
                    key={path.id}
                    sx={{
                      cursor: 'pointer',
                      bgcolor: selectedPath?.id === path.id ? 'primary.50' : 'background.paper',
                      border: selectedPath?.id === path.id ? '1px solid' : 'none',
                      borderColor: 'primary.main'
                    }}
                    onClick={() => loadSavedPathDetails(path.id)}
                  >
                    <CardContent>
                      <Typography variant="subtitle1" fontWeight="bold">{path.topic}</Typography>
                      <Typography variant="caption" color="text.secondary">{path.level} • {path.total_steps} steps</Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                        <LinearProgress variant="determinate" value={path.progress} sx={{ flex: 1, mr: 1, height: 6, borderRadius: 3 }} />
                        <Typography variant="caption">{path.progress}%</Typography>
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            </Grid>
            <Grid item xs={12} md={8}>
              {selectedPath ? (
                <Box>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
                    <Box>
                      <Typography variant="h5" fontWeight="bold">{selectedPath.topic}</Typography>
                      <Typography variant="subtitle1" color="text.secondary">{selectedPath.level} Roadmap</Typography>
                    </Box>
                    <Button color="error" onClick={() => handleDeletePath(selectedPath.id)}>Delete</Button>
                  </Stack>

                  <Box sx={{ position: 'relative', pl: 2 }}>
                    <Box sx={{
                      position: 'absolute',
                      left: 28,
                      top: 0,
                      bottom: 0,
                      width: 2,
                      bgcolor: 'primary.light',
                      opacity: 0.3
                    }} />

                    {selectedPath.steps.map((step, index) => (
                      <Box key={step.id} sx={{ display: 'flex', mb: 3, position: 'relative' }}>
                        <Box
                          onClick={() => handleStepAction(selectedPath.id, step.id, 'complete')}
                          sx={{
                            width: 40,
                            height: 40,
                            borderRadius: '50%',
                            bgcolor: step.is_completed ? 'success.main' : 'grey.300',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 'bold',
                            zIndex: 1,
                            mr: 2,
                            flexShrink: 0,
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                          }}
                        >
                          {step.is_completed ? '✓' : step.step_number}
                        </Box>

                        <Card sx={{ flex: 1, borderRadius: 2, boxShadow: 1, opacity: step.is_completed ? 0.7 : 1 }}>
                          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <Box>
                                <Typography variant="subtitle1" fontWeight="bold" color={step.is_completed ? 'text.secondary' : 'primary.dark'} sx={{ textDecoration: step.is_completed ? 'line-through' : 'none' }}>
                                  {step.title}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                  {step.details}
                                </Typography>
                              </Box>
                            </Box>

                            {step.video_link && (
                              <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', bgcolor: 'background.default', p: 1, borderRadius: 1 }}>
                                <Button
                                  variant="text"
                                  startIcon={<PlayArrow />}
                                  href={step.video_link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  size="small"
                                  sx={{ textTransform: 'none', fontWeight: 'bold' }}
                                >
                                  Watch Video
                                </Button>
                                <FormControlLabel
                                  control={
                                    <Checkbox
                                      checked={step.video_watched}
                                      onChange={() => handleStepAction(selectedPath.id, step.id, 'video')}
                                      size="small"
                                    />
                                  }
                                  label={<Typography variant="caption">Watched</Typography>}
                                />
                              </Box>
                            )}

                            {step.coding_link && (
                              <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', bgcolor: 'background.default', p: 1, borderRadius: 1 }}>
                                <Button
                                  variant="text"
                                  color="success"
                                  startIcon={<Code />}
                                  size="small"
                                  href={step.coding_link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  sx={{ textTransform: 'none', fontWeight: 'bold' }}
                                >
                                  Practice Coding
                                </Button>
                                <FormControlLabel
                                  control={
                                    <Checkbox
                                      checked={step.code_practiced}
                                      onChange={() => handleStepAction(selectedPath.id, step.id, 'code')}
                                      size="small"
                                      color="success"
                                    />
                                  }
                                  label={<Typography variant="caption">Practiced</Typography>}
                                />
                              </Box>
                            )}

                            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                              <Button
                                size="small"
                                variant={step.is_completed ? "contained" : "outlined"}
                                color={step.is_completed ? "success" : "primary"}
                                onClick={() => handleStepAction(selectedPath.id, step.id, 'complete')}
                                startIcon={step.is_completed ? <CheckCircle /> : <RadioButtonUnchecked />}
                              >
                                {step.is_completed ? "Completed" : "Mark Complete"}
                              </Button>
                            </Box>
                          </CardContent>
                        </Card>
                      </Box>
                    ))}
                  </Box>
                </Box>
              ) : (
                <Box display="flex" justifyContent="center" alignItems="center" height="50vh">
                  <Typography color="text.secondary">Select a roadmap to view details</Typography>
                </Box>
              )}
            </Grid>
          </Grid>
        )}
      </Container>
    </Box>
  );
};

export default LearningPath;
