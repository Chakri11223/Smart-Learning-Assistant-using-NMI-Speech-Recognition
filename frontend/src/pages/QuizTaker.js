import React, { useState, useEffect } from "react";
import axios from "axios";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  Paper,
  Container,
  Alert,
  LinearProgress,
  Chip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tooltip,
  Stack
} from "@mui/material";
import {
  CheckCircle,
  Cancel,
  EmojiEvents,
  Fullscreen,
  FullscreenExit,
  Warning,
  Timer,
  Block
} from "@mui/icons-material";
import SafeText from "../components/SafeText";

const safeString = (val) => {
  try {
    if (val == null) return "";
    if (typeof val === "string") return val;
    if (typeof val === "number" || typeof val === "boolean") return String(val);
    if (React.isValidElement(val)) return "[React Element]";
    if (typeof val === "object") {
      if (val.$$typeof) return "[React Element]";
      if (val.type && val.props) return "[React Element]";
      if (Array.isArray(val)) return val.map((item) => safeString(item)).join(" ");
      return JSON.stringify(val);
    }
    return String(val);
  } catch (error) {
    return "[Invalid Content]";
  }
};

const QuizTaker = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const questions = location.state?.questions || [];
  const quizTitle = location.state?.title || "Untitled Quiz";

  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showWarning, setShowWarning] = useState(false);
  const [tabSwitchCount, setTabSwitchCount] = useState(0);
  const [startTime, setStartTime] = useState(Date.now());
  const [timeSpent, setTimeSpent] = useState(0);
  const [disqualified, setDisqualified] = useState(false);

  useEffect(() => {
    if (!questions || questions.length === 0) {
      // If no questions, maybe redirect back?
    }
    setAnswers({});
    setSubmitted(false);
    setResults(null);
    setError("");
    setTabSwitchCount(0);
    setStartTime(Date.now());
    setTimeSpent(0);
    setDisqualified(false);

    // Request fullscreen on mount
    enterFullscreen();
  }, [questions]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };

    const handleVisibilityChange = () => {
      if (document.hidden && !submitted && !disqualified) {
        setTabSwitchCount((prev) => {
          const newCount = prev + 1;
          if (newCount >= 3) {
            setDisqualified(true);
            exitFullscreen();
          } else {
            setShowWarning(true);
          }
          return newCount;
        });
      }
    };

    const handleKeyDown = (e) => {
      // Prevent common shortcuts that might switch context
      if (
        e.key === "F11" ||
        (e.ctrlKey && e.shiftKey && e.key === "I") ||
        (e.ctrlKey && e.key.toLowerCase() === "u") ||
        (e.ctrlKey && e.key.toLowerCase() === "s") ||
        (e.ctrlKey && e.key.toLowerCase() === "p") ||
        (e.altKey && e.key === "Tab") // Attempt to catch alt-tab (browser might block this)
      ) {
        // e.preventDefault(); // Browser might not allow preventing some of these
        // Just warn
        if (!submitted && !disqualified) {
          setShowWarning(true);
        }
      }
    };

    const handleContextMenu = (e) => {
      e.preventDefault();
      if (!submitted && !disqualified) {
        setShowWarning(true);
      }
    };

    const updateTimeSpent = () => {
      if (!submitted && !disqualified) {
        setTimeSpent(Date.now() - startTime);
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("contextmenu", handleContextMenu);
    const timeInterval = window.setInterval(updateTimeSpent, 1000);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("contextmenu", handleContextMenu);
      window.clearInterval(timeInterval);
    };
  }, [submitted, startTime, disqualified]);

  const enterFullscreen = async () => {
    try {
      await document.documentElement.requestFullscreen?.();
    } catch (err) {
      console.error("Error entering fullscreen:", err);
    }
  };

  const exitFullscreen = async () => {
    try {
      await document.exitFullscreen?.();
    } catch (err) {
      console.error("Error exiting fullscreen:", err);
    }
  };

  const handleBack = () => {
    exitFullscreen();
    navigate('/quiz-generator');
  };

  const handleAnswerChange = (questionId, value) => {
    if (disqualified) return;
    const numeric = Number.parseInt(value, 10);
    setAnswers((prev) => ({
      ...prev,
      [questionId]: Number.isNaN(numeric) ? undefined : numeric
    }));
  };

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

  const handleSubmit = async () => {
    if (Object.keys(answers).length < questions.length) {
      setError("Please answer all questions before submitting.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const numericAnswers = Object.fromEntries(
        Object.entries(answers).map(([qid, val]) => [qid, typeof val === "number" ? val : 0])
      );
      const userStr = localStorage.getItem('authUser');
      const user = userStr ? JSON.parse(userStr) : null;
      const userId = user?.id;

      const response = await axios.post("http://localhost:5000/api/submit-quiz", {
        questions,
        answers: numericAnswers,
        quizTitle,
        user_id: userId, // Send explicitly in body
        sessionId: `quiz-session-${Date.now()}`,
        securityData: {
          tabSwitchCount,
          timeSpent: Math.round(timeSpent / 1000),
          isFullscreen,
          userAgent: navigator.userAgent,
          screenResolution: `${window.screen?.width || 0}x${window.screen?.height || 0}`,
          timestamp: new Date().toISOString()
        }
      }, {
        headers: getAuthHeaders()
      });
      setResults(response.data);
      setSubmitted(true);
    } catch (err) {
      const axiosError = err;
      const message = axiosError.response?.data?.error?.message || axiosError.response?.data?.error?.error || axiosError.response?.data?.error || axiosError.message;
      setError(`Failed to submit quiz: ${message}`);
    }
    setLoading(false);
  };

  const getScoreColor = (percentage) => {
    if (percentage >= 80) return "#4caf50";
    if (percentage >= 60) return "#ff9800";
    return "#f44336";
  };

  const getScoreMessage = (percentage) => {
    if (percentage >= 90) return "Excellent!";
    if (percentage >= 80) return "Great job!";
    if (percentage >= 70) return "Good work!";
    if (percentage >= 60) return "Not bad!";
    return "Keep studying!";
  };

  if (!questions || questions.length === 0) {
    return (
      <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "background.default" }}>
        <Card sx={{ p: 4, textAlign: "center", maxWidth: 400 }}>
          <Typography variant="h5" color="text.secondary" gutterBottom>
            No active quiz found
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Please go back to the generator and create a new quiz.
          </Typography>
          <Button variant="contained" onClick={handleBack} sx={{ mt: 2 }}>
            Back to Generator
          </Button>
        </Card>
      </Box>
    );
  }

  if (disqualified) {
    return (
      <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#fff0f0" }}>
        <Container maxWidth="sm">
          <Card sx={{ p: 5, textAlign: "center", borderRadius: 4, boxShadow: 6 }}>
            <Block sx={{ fontSize: 80, color: "#d32f2f", mb: 2 }} />
            <Typography variant="h3" gutterBottom sx={{ color: "#d32f2f", fontWeight: "bold" }}>
              Quiz Terminated
            </Typography>
            <Typography variant="h6" color="text.secondary" paragraph>
              You have exceeded the maximum number of tab switches (3).
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              To maintain the integrity of the quiz, your session has been closed.
            </Typography>
            <Button variant="contained" color="error" onClick={handleBack} size="large" sx={{ mt: 3 }}>
              Return to Home
            </Button>
          </Card>
        </Container>
      </Box>
    );
  }

  if (submitted && results) {
    return (
      <Box sx={{ minHeight: "100vh", bgcolor: "background.default", py: 4 }}>
        <Container maxWidth="md">
          <Card sx={{ boxShadow: 8, borderRadius: 3, bgcolor: "background.paper" }}>
            <CardContent sx={{ p: 5, color: "text.primary" }}>
              <Box sx={{ textAlign: "center", mb: 4 }}>
                <EmojiEvents
                  sx={{
                    fontSize: 80,
                    color: getScoreColor(results?.score?.percentage ?? 0),
                    mb: 2
                  }}
                />
                <Typography
                  variant="h2"
                  gutterBottom
                  sx={{
                    color: "primary.main",
                    fontWeight: "bold",
                    fontSize: { xs: "2rem", md: "3rem" }
                  }}
                >
                  🎉 Quiz Complete!
                </Typography>
                <Typography
                  variant="h3"
                  sx={{
                    color: getScoreColor(results?.score?.percentage ?? 0),
                    fontWeight: "bold",
                    mb: 1
                  }}
                >
                  {results?.score?.percentage ?? 0}%
                </Typography>
                <Typography
                  variant="h5"
                  sx={{
                    color: getScoreColor(results?.score?.percentage ?? 0),
                    mb: 3,
                    fontWeight: "bold"
                  }}
                >
                  {getScoreMessage(results?.score?.percentage ?? 0)}
                </Typography>

                <Box sx={{ display: "flex", justifyContent: "center", gap: 2, mb: 4 }}>
                  <Chip
                    label={`\u2705 ${results?.score?.correct ?? 0} Correct`}
                    color="success"
                    variant="outlined"
                    sx={{ fontSize: "16px", py: 1 }}
                  />
                  <Chip
                    label={`\u274C ${(results?.score?.total ?? 0) - (results?.score?.correct ?? 0)} Incorrect`}
                    color="error"
                    variant="outlined"
                    sx={{ fontSize: "16px", py: 1 }}
                  />
                </Box>

                <LinearProgress
                  variant="determinate"
                  value={results?.score?.percentage ?? 0}
                  sx={{
                    height: 16,
                    borderRadius: 8,
                    backgroundColor: "#e0e0e0",
                    "& .MuiLinearProgress-bar": {
                      backgroundColor: getScoreColor(results?.score?.percentage ?? 0),
                      borderRadius: 8
                    }
                  }}
                />
              </Box>

              <Divider sx={{ my: 4 }} />

              <Typography
                variant="h4"
                gutterBottom
                sx={{
                  color: "primary.main",
                  fontWeight: "bold",
                  mb: 3,
                  textAlign: "center"
                }}
              >
                📝 Question Review
              </Typography>

              {(results?.results ?? []).map((result, index) => (
                <Paper
                  key={result.questionId}
                  sx={{
                    p: 4,
                    mb: 3,
                    bgcolor: "background.paper",
                    borderRadius: 3,
                    border: "2px solid",
                    borderColor: result.isCorrect ? "success.main" : "error.main",
                    boxShadow: 4,
                    color: "text.primary"
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
                    <Box
                      sx={{
                        backgroundColor: result.isCorrect ? "#4caf50" : "#f44336",
                        color: "white",
                        borderRadius: "50%",
                        width: 40,
                        height: 40,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                        fontWeight: "bold"
                      }}
                    >
                      {index + 1}
                    </Box>
                    <SafeText variant="h6" component="span" sx={{ flexGrow: 1, fontWeight: "bold" }}>
                      {result?.question}
                    </SafeText>
                    {result?.isCorrect ? (
                      <CheckCircle sx={{ color: "#4caf50", fontSize: 40 }} />
                    ) : (
                      <Cancel sx={{ color: "#f44336", fontSize: 40 }} />
                    )}
                  </Box>

                  {Array.isArray(result?.options) &&
                    result.options.map((option, optionIndex) => (
                      <Box
                        key={optionIndex}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          p: 2,
                          mb: 2,
                          borderRadius: 2,
                          bgcolor:
                            optionIndex === result?.correctAnswer
                              ? "success.light"
                              : optionIndex === result?.userAnswer && !result?.isCorrect
                                ? "error.light"
                                : "transparent",
                          border: "2px solid",
                          borderColor:
                            optionIndex === result?.correctAnswer
                              ? "success.main"
                              : optionIndex === result?.userAnswer && !result?.isCorrect
                                ? "error.main"
                                : "divider"
                        }}
                      >
                        <SafeText variant="body1" component="span" sx={{ flexGrow: 1, fontSize: "1.1rem" }}>
                          {`${String.fromCharCode(65 + optionIndex)}. ${safeString(option)}`}
                        </SafeText>
                        {optionIndex === result?.correctAnswer && (
                          <CheckCircle sx={{ color: "#4caf50", ml: 2, fontSize: 30 }} />
                        )}
                        {optionIndex === result?.userAnswer && !result?.isCorrect && (
                          <Cancel sx={{ color: "#f44336", ml: 2, fontSize: 30 }} />
                        )}
                      </Box>
                    ))}
                </Paper>
              ))}

              <Box sx={{ display: "flex", gap: 2, justifyContent: "center", mt: 6 }}>
                <Button variant="contained" onClick={handleBack} size="large" sx={{ px: 4, py: 1.5 }}>
                  Return to Generator
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Container>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default",
        py: 4
      }}
    >
      <Container maxWidth="md">
        {/* Header / Timer / Status */}
        <Paper sx={{ p: 2, mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderRadius: 3 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Timer color="action" />
            <Typography variant="h6" fontWeight="bold">
              {Math.floor(timeSpent / 60000)}:
              {String(Math.floor((timeSpent % 60000) / 1000)).padStart(2, '0')}
            </Typography>
          </Stack>

          <Stack direction="row" spacing={2} alignItems="center">
            <Chip
              icon={<Warning />}
              label={`Warnings: ${tabSwitchCount}/3`}
              color={tabSwitchCount > 0 ? "warning" : "default"}
              variant={tabSwitchCount > 0 ? "filled" : "outlined"}
            />
            <Tooltip title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}>
              <IconButton onClick={isFullscreen ? exitFullscreen : enterFullscreen}>
                {isFullscreen ? <FullscreenExit /> : <Fullscreen />}
              </IconButton>
            </Tooltip>
          </Stack>
        </Paper>

        <Card sx={{ boxShadow: 8, borderRadius: 3, bgcolor: "background.paper" }}>
          <CardContent sx={{ p: 5, color: "text.primary" }}>
            <Box sx={{ textAlign: "center", mb: 4 }}>
              <Typography
                variant="h3"
                gutterBottom
                sx={{
                  color: "primary.main",
                  fontWeight: "bold",
                }}
              >
                Quiz Session
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Please answer all questions. Do not switch tabs.
              </Typography>
            </Box>

            {questions.map((question, index) => {
              const qid = String(index);
              return (
                <Paper
                  key={`qk-${qid}`}
                  sx={{
                    p: 4,
                    mb: 4,
                    bgcolor: "background.paper",
                    borderRadius: 3,
                    border: "2px solid",
                    borderColor: "divider",
                    boxShadow: 3,
                    "&:hover": {
                      borderColor: "primary.main",
                      boxShadow: 6
                    }
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
                    <Box
                      sx={{
                        backgroundColor: "primary.main",
                        color: "white",
                        borderRadius: "50%",
                        width: 40,
                        height: 40,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                        fontWeight: "bold"
                      }}
                    >
                      {index + 1}
                    </Box>
                    <SafeText variant="h5" component="span" sx={{ color: "text.primary", fontWeight: "bold" }}>
                      {question.question}
                    </SafeText>
                  </Box>

                  <FormControl component="fieldset" sx={{ width: "100%" }}>
                    <RadioGroup
                      name={`q-${qid}`}
                      value={Object.prototype.hasOwnProperty.call(answers, qid) ? String(answers[qid]) : ""}
                      onChange={(e) => handleAnswerChange(qid, e.target.value)}
                    >
                      {question.options.map((option, optionIndex) => (
                        <FormControlLabel
                          key={optionIndex}
                          value={String(optionIndex)}
                          control={<Radio />}
                          label={<SafeText component="span" variant="body1">{safeString(option)}</SafeText>}
                          sx={{
                            mb: 2,
                            p: 2,
                            borderRadius: 2,
                            border:
                              Object.prototype.hasOwnProperty.call(answers, qid) && answers[qid] === optionIndex
                                ? "3px solid"
                                : "2px solid",
                            borderColor:
                              Object.prototype.hasOwnProperty.call(answers, qid) && answers[qid] === optionIndex
                                ? "primary.main"
                                : "divider",
                            "&:hover": {
                              borderColor: "primary.main"
                            }
                          }}
                        />
                      ))}
                    </RadioGroup>
                  </FormControl>
                </Paper>
              );
            })}

            <Box sx={{ display: "flex", gap: 2, justifyContent: "center", mt: 6 }}>
              <Button variant="outlined" onClick={handleBack} size="large" sx={{ px: 4, py: 1.5 }}>
                Cancel
              </Button>
              <Button
                variant="contained"
                onClick={handleSubmit}
                disabled={loading || Object.keys(answers).length < questions.length}
                size="large"
                sx={{
                  minWidth: 150,
                  px: 4,
                  py: 1.5,
                  fontSize: "18px",
                  fontWeight: "bold"
                }}
              >
                {loading ? "Submitting..." : "Submit Quiz"}
              </Button>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mt: 4, fontSize: "16px" }}>
                <SafeText component="span">{error}</SafeText>
              </Alert>
            )}
          </CardContent>
        </Card>
      </Container>

      <Dialog open={showWarning} onClose={() => setShowWarning(false)}>
        <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Warning color="warning" />
          Warning ({tabSwitchCount}/3)
        </DialogTitle>
        <DialogContent>
          <Typography>
            Please stay focused on the quiz window. Switching tabs or exiting fullscreen is a violation.
          </Typography>
          <Typography fontWeight="bold" sx={{ mt: 1 }}>
            If you switch tabs {3 - tabSwitchCount} more times, your quiz will be terminated.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowWarning(false)} variant="contained">
            I Understand
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default QuizTaker;
