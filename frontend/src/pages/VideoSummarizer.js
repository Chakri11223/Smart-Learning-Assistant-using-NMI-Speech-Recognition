import { useState, useRef, useEffect } from "react";
import axios from "axios";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  Button,
  TextField,
  Alert,
  LinearProgress,
  Stack,
  Chip,
  Dialog,
  Switch,
  FormControlLabel
} from "@mui/material";
const VideoSummarizer = () => {
  const [tab, setTab] = useState(0);
  // Track loading state by ID
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [maxWords, setMaxWords] = useState(250);
  const [url, setUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  const fileRef = useRef(null);
  const [videoFile, setVideoFile] = useState(null);
  const [useBalancedWords, setUseBalancedWords] = useState(false);

  const getEffectiveMaxWords = () => useBalancedWords ? "balanced" : maxWords;

  const fetchSavedSummaries = async () => {
    try {
      const userStr = localStorage.getItem('authUser');
      const user = userStr ? JSON.parse(userStr) : null;
      if (!user) return;

      const res = await axios.get("http://localhost:5000/api/video/saved", {
        headers: { 'X-User-Id': user.id }
      });
      setSavedSummaries(res.data.summaries || []);
    } catch (e) {
      console.error("Failed to fetch saved summaries", e);
    }
  };

  const handleSaveSummary = async () => {
    if (!saveTitle.trim() || !result?.summary) return;
    setSaving(true);
    try {
      const userStr = localStorage.getItem('authUser');
      const user = userStr ? JSON.parse(userStr) : null;

      await axios.post("http://localhost:5000/api/video/save", {
        title: saveTitle,
        summary_text: result.summary,
        video_url: result.url || ""
      }, {
        headers: { 'X-User-Id': user?.id }
      });

      setSaveDialogOpen(false);
      setSaveTitle("");
      fetchSavedSummaries();
    } catch (e) {
      setError("Failed to save summary.");
    }
    setSaving(false);
  };
  const handleSummarizeTranscript = async () => {
    if (!transcript.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await axios.post("http://localhost:5000/api/summarize-transcript", {
        transcript,
        maxWords: getEffectiveMaxWords()
      });
      setResult(res.data);
    } catch (e) {
      const axiosError = e;
      setError(axiosError.response?.data?.error || axiosError.message);
    }
    setLoading(false);
  };
  const handleSummarizeUrl = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await axios.post("http://localhost:5000/api/summarize-url", { url, maxWords: getEffectiveMaxWords() });
      setResult(res.data);
    } catch (e) {
      const axiosError = e;
      setError(axiosError.response?.data?.error || axiosError.message);
    }
    setLoading(false);
  };
  const handleSummarizeVideo = async () => {
    if (!videoFile) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("video", videoFile);
      form.append("maxWords", String(getEffectiveMaxWords()));
      const res = await axios.post("http://localhost:5000/api/summarize-video", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setResult(res.data);
    } catch (e) {
      const axiosError = e;
      setError(axiosError.response?.data?.error || axiosError.message);
    }
    setLoading(false);
  };
  // Save & Audio State
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveTitle, setSaveTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedSummaries, setSavedSummaries] = useState([]);
  const [playingId, setPlayingId] = useState(null); // Changed from boolean to ID (null = nothing playing)
  const [loadingId, setLoadingId] = useState(null); // Tracks which ID is currently loading audio
  const audioRef = useRef(new Audio());


  useEffect(() => {
    fetchSavedSummaries();
    return () => {
      audioRef.current.pause();
    };
  }, []);

  const handlePlayAudio = async (text, id) => {
    // If clicking the currently playing item, stop it
    if (playingId === id) {
      audioRef.current.pause();
      setPlayingId(null);
      return;
    }

    // If something else is playing, stop it first
    if (playingId) {
      audioRef.current.pause();
    }

    try {
      setLoadingId(id);
      const res = await axios.post("http://localhost:5000/api/tts", { text }, {
        responseType: 'blob'
      });

      const blobUrl = URL.createObjectURL(res.data);
      audioRef.current.src = blobUrl;
      audioRef.current.play();
      setLoadingId(null);
      setPlayingId(id);

      audioRef.current.onended = () => setPlayingId(null);
    } catch (e) {
      console.error("Audio playback failed", e);
      setLoadingId(null);
      setPlayingId(null);
    }
  };

  const handleDownloadPdf = async () => {
    // ... existing download code ...
    if (!result?.summary) return;
    try {
      const items = [{ question: "Video Summary", answer: result.summary }];
      const res = await axios.post(
        "http://localhost:5000/api/generate-pdf",
        { items, title: "Video Summary" },
        { responseType: "blob" }
      );
      const blobUrl = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const anchor = document.createElement("a");
      anchor.href = blobUrl;
      anchor.download = "video_summary.pdf";
      anchor.click();
      URL.revokeObjectURL(blobUrl);
    } catch (e) {
      const axiosError = e;
      setError(axiosError.response?.data?.error || axiosError.message);
    }
  };

  const handleViewSummary = (summary) => {
    setResult({
      summary: summary.summary_text,
      video_id: null,
      url: summary.video_url
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const StopIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );

  return (
    <Box>
      <Typography variant="h3" gutterBottom sx={{ color: "#1976d2", fontWeight: "bold", mb: 3 }}>
        Video Summarizer
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>How to use:</strong> For YouTube videos, copy the transcript from the captions and use the "Paste
          Transcript" tab. For local videos, use the "Upload Video" tab. The "YouTube URL" tab provides guidance but cannot
          download videos directly.
        </Typography>
      </Alert>

      <Box sx={{ display: 'flex', gap: 4, flexDirection: { xs: 'column', md: 'row' } }}>
        <Box sx={{ flex: 1 }}>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
            <Tab label="Upload Video" />
            <Tab label="YouTube URL" />
            <Tab label="Paste Transcript" />
          </Tabs>

          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Stack direction="row" spacing={3} alignItems="center" sx={{ mb: 2 }}>
                <TextField
                  type="number"
                  label="Max Words"
                  value={maxWords}
                  onChange={(e) => setMaxWords(Number(e.target.value) || 250)}
                  disabled={useBalancedWords}
                  sx={{ width: 140 }}
                  size="small"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={useBalancedWords}
                      onChange={(e) => setUseBalancedWords(e.target.checked)}
                      color="primary"
                    />
                  }
                  label="Balanced (Auto-Limit)"
                />
                {result?.warnings?.map((warning, index) => <Chip key={warning + index.toString()} label={warning} color="warning" variant="outlined" />)}
              </Stack>

              {tab === 0 && <Box>
                <Typography variant="body1" sx={{ mb: 2, color: "text.secondary" }}>
                  Upload a video file (MP4, AVI, MOV, etc.) to get an AI-generated transcript and summary. The video will be
                  processed locally and then summarized using AI.
                </Typography>
                <Button variant="outlined" onClick={() => fileRef.current?.click()} sx={{ mr: 2 }}>
                  Choose Video
                </Button>
                <input
                  ref={fileRef}
                  type="file"
                  accept="video/*"
                  style={{ display: "none" }}
                  onChange={(e) => setVideoFile(e.target.files?.[0] || null)}
                />
                {videoFile && <Typography sx={{ mt: 1 }}>
                  Selected: {videoFile.name}
                </Typography>}
                <Box sx={{ mt: 2 }}>
                  <Button variant="contained" disabled={loading || !videoFile} onClick={handleSummarizeVideo}>
                    Summarize Video
                  </Button>
                </Box>
              </Box>}

              {tab === 1 && <Box>
                <Typography variant="body1" sx={{ mb: 2, color: "text.secondary" }}>
                  Enter a YouTube URL to get guidance on video summarization. For full transcripts, use the 'Upload Video' or
                  'Paste Transcript' tabs.
                </Typography>
                <TextField
                  fullWidth
                  label="YouTube URL"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                />
                <Box sx={{ mt: 2 }}>
                  <Button variant="contained" disabled={loading || !url.trim()} onClick={handleSummarizeUrl}>
                    Get Video Guidance
                  </Button>
                </Box>
              </Box>}

              {tab === 2 && <Box>
                <Typography variant="body1" sx={{ mb: 2, color: "text.secondary" }}>
                  Paste a video transcript or captions here to get an AI-generated summary. You can copy transcripts from
                  YouTube's auto-generated captions or any other video platform.
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={8}
                  placeholder="Paste transcript here..."
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                />
                <Box sx={{ mt: 2 }}>
                  <Button variant="contained" disabled={loading || !transcript.trim()} onClick={handleSummarizeTranscript}>
                    Summarize Transcript
                  </Button>
                </Box>
              </Box>}

              {loading && <LinearProgress sx={{ mt: 2 }} />}
              {error && <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>}
            </CardContent>
          </Card>

          {result && <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom sx={{ color: "#1976d2", fontWeight: "bold" }}>
                {result.video_id ? "Video Guidance" : "AI Summary"}
              </Typography>

              {result.warnings && result.warnings.includes("youtube_url_limited") && <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  <strong>YouTube URL Detected:</strong> This feature provides guidance for YouTube videos. For full
                  transcripts and summaries, please use the other tabs.
                </Typography>
              </Alert>}

              <Typography variant="body1" sx={{ whiteSpace: "pre-wrap", mb: 2 }}>
                {(result.summary || "").replace(/\*/g, "").split(/\n\n+/).map((paragraph, index) => <span key={paragraph + index.toString()} style={{ display: "block", marginBottom: "12px" }}>
                  {paragraph}
                </span>)}
              </Typography>

              {result.video_id && <Box sx={{ mt: 3, p: 2, backgroundColor: "#f5f5f5", borderRadius: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  <strong>Video ID:</strong> {result.video_id}
                  <br />
                  <strong>URL:</strong> {result.url}
                </Typography>
              </Box>}

              <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
                <Button variant="outlined" onClick={handleDownloadPdf}>
                  Download PDF
                </Button>
                <Button variant="contained" color="secondary" onClick={() => setSaveDialogOpen(true)}>
                  Save Summary
                </Button>
                {playingId !== "main" ? (
                  <Button
                    variant="contained"
                    color="info"
                    onClick={() => handlePlayAudio(result.summary, "main")}
                    disabled={loadingId !== null}
                  >
                    {loadingId === "main" ? "Generating..." : "Listen with AI"}
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    color="error"
                    onClick={() => handlePlayAudio(result.summary, "main")}
                    startIcon={<StopIcon />}
                  >
                    Stop Audio
                  </Button>
                )}
              </Stack>
            </CardContent>
          </Card>}
        </Box>

        {/* Saved Summaries Sidebar */}
        <Card sx={{ width: { xs: '100%', md: 350 }, height: 'fit-content' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom fontWeight="bold">
              Saved Summaries
            </Typography>
            {savedSummaries.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No saved summaries yet.
              </Typography>
            ) : (
              <Stack spacing={2}>
                {savedSummaries.map(summary => (
                  <Card key={summary.id} variant="outlined">
                    <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                      <Typography variant="subtitle1" fontWeight="bold" noWrap title={summary.title}>
                        {summary.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                        {new Date(summary.created_at).toLocaleString(undefined, {
                          dateStyle: 'medium',
                          timeStyle: 'short'
                        })}
                      </Typography>

                      <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleViewSummary(summary)}
                        >
                          View
                        </Button>
                        <Button
                          size="small"
                          onClick={() => handlePlayAudio(summary.summary_text, summary.id)}
                          startIcon={playingId !== summary.id && loadingId !== summary.id && <span>🔊</span>}
                          variant={playingId === summary.id ? "contained" : "soft"}
                          color={playingId === summary.id ? "error" : "primary"}
                          disabled={loadingId !== null}
                        >
                          {loadingId === summary.id ? "Generating..." : (playingId === summary.id ? "Stop" : "Listen")}
                        </Button>
                      </Stack>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)}>
        <Box sx={{ p: 3, minWidth: 300 }}>
          <Typography variant="h6" gutterBottom>Save Summary</Typography>
          <TextField
            fullWidth
            label="Title"
            value={saveTitle}
            onChange={(e) => setSaveTitle(e.target.value)}
            margin="normal"
          />
          <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{ mt: 2 }}>
            <Button onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleSaveSummary} disabled={saving}>
              Save
            </Button>
          </Stack>
        </Box>
      </Dialog>
    </Box>
  );
};
var VideoSummarizer_default = VideoSummarizer;
export {
  VideoSummarizer_default as default
};
