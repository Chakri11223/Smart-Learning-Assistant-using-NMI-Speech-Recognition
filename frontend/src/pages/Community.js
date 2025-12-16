import { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Box,
    Typography,
    Card,
    CardContent,
    Button,
    TextField,
    Dialog,
    Stack,
    Chip,
    Avatar,
    Divider,
    List,
    ListItem,
    IconButton
} from '@mui/material';

import { Delete } from '@mui/icons-material';

const Community = () => {
    const [topics, setTopics] = useState([]);
    const [selectedTopic, setSelectedTopic] = useState(null);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [comment, setComment] = useState("");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchTopics();
    }, []);

    const fetchTopics = async () => {
        try {
            const res = await axios.get("http://localhost:5000/api/community/topics");
            setTopics(res.data.topics || []);
        } catch (e) {
            console.error("Failed to fetch topics", e);
        }
    };

    const handleCreateTopic = async () => {
        if (!title.trim() || !content.trim()) return;

        const userStr = localStorage.getItem('authUser');
        const user = userStr ? JSON.parse(userStr) : null;

        if (!user || !user.id) {
            alert("You must be logged in to create a topic.");
            return;
        }

        try {
            await axios.post("http://localhost:5000/api/community/topics", {
                title,
                content
            }, {
                headers: { 'X-User-Id': user.id }
            });
            setDialogOpen(false);
            setTitle("");
            setContent("");
            fetchTopics();
        } catch (e) {
            console.error("Failed to create topic", e);
            alert("Failed to create topic. " + (e.response?.data?.error || e.message));
        }
    };

    const handleDeleteTopic = async (topicId, e) => {
        e.stopPropagation(); // Prevent opening the topic details when clicking delete
        if (!window.confirm("Are you sure you want to delete this topic?")) return;

        const userStr = localStorage.getItem('authUser');
        const user = userStr ? JSON.parse(userStr) : null;

        try {
            await axios.delete(`http://localhost:5000/api/community/topics/${topicId}`, {
                headers: { 'X-User-Id': user?.id }
            });
            fetchTopics();
            if (selectedTopic && selectedTopic.id === topicId) {
                setSelectedTopic(null); // Return to list if deleted from details
            }
        } catch (e) {
            console.error("Failed to delete topic", e);
            alert("Failed to delete topic. " + (e.response?.data?.error || e.message));
        }
    };

    const handleSelectTopic = async (topicId) => {
        try {
            setLoading(true);
            const res = await axios.get(`http://localhost:5000/api/community/topics/${topicId}`);
            setSelectedTopic(res.data);
        } catch (e) {
            console.error("Failed to load topic details", e);
        }
        setLoading(false);
    };

    const handleAddComment = async () => {
        if (!comment.trim() || !selectedTopic) return;
        try {
            const userStr = localStorage.getItem('authUser');
            const user = userStr ? JSON.parse(userStr) : null;

            await axios.post(`http://localhost:5000/api/community/topics/${selectedTopic.id}/comments`, {
                content: comment
            }, {
                headers: { 'X-User-Id': user?.id }
            });
            setComment("");
            handleSelectTopic(selectedTopic.id); // Refresh
        } catch (e) {
            console.error("Failed to add comment", e);
        }
    };

    const handleLike = async (topicId) => {
        try {
            const userStr = localStorage.getItem('authUser');
            const user = userStr ? JSON.parse(userStr) : null;

            await axios.post(`http://localhost:5000/api/community/topics/${topicId}/like`, {}, {
                headers: { 'X-User-Id': user?.id }
            });
            // Optimistic update or refresh
            if (selectedTopic && selectedTopic.id === topicId) {
                handleSelectTopic(topicId);
            } else {
                fetchTopics();
            }
        } catch (e) {
            console.error("Failed to like topic", e);
        }
    };

    const userStr = localStorage.getItem('authUser');
    const currentUser = userStr ? JSON.parse(userStr) : null;

    if (selectedTopic) {
        return (
            <Box>
                <Button onClick={() => setSelectedTopic(null)} sx={{ mb: 2 }}>&larr; Back to Topics</Button>
                <Card sx={{ mb: 3 }}>
                    <CardContent>
                        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                            <Box>
                                <Typography variant="h4" fontWeight="bold">{selectedTopic.title}</Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                    Posted by {selectedTopic.username} on {new Date(selectedTopic.created_at).toLocaleDateString()}
                                </Typography>
                            </Box>
                            {currentUser && currentUser.id === selectedTopic.user_id && (
                                <IconButton onClick={(e) => handleDeleteTopic(selectedTopic.id, e)} color="error">
                                    <Delete />
                                </IconButton>
                            )}
                        </Stack>
                        <Typography variant="body1" paragraph>{selectedTopic.content}</Typography>

                        <Button variant="outlined" startIcon={<span>👍</span>} onClick={() => handleLike(selectedTopic.id)}>
                            {selectedTopic.likes} Likes
                        </Button>
                    </CardContent>
                </Card>

                <Typography variant="h6" sx={{ mb: 2 }}>Discussion ({selectedTopic.comments.length})</Typography>
                <Stack spacing={2} sx={{ mb: 4 }}>
                    {selectedTopic.comments.map(c => (
                        <Card key={c.id} variant="outlined">
                            <CardContent sx={{ p: 2 }}>
                                <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
                                    <Avatar sx={{ width: 24, height: 24, fontSize: 12 }}>{c.username[0]}</Avatar>
                                    <Typography variant="subtitle2" fontWeight="bold">{c.username}</Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {new Date(c.created_at).toLocaleString()}
                                    </Typography>
                                </Stack>
                                <Typography variant="body2">{c.content}</Typography>
                            </CardContent>
                        </Card>
                    ))}
                </Stack>

                <Box sx={{ position: 'sticky', bottom: 20 }}>
                    <Card elevation={4}>
                        <CardContent>
                            <Stack direction="row" spacing={2}>
                                <TextField
                                    fullWidth
                                    placeholder="Add to the discussion..."
                                    value={comment}
                                    onChange={(e) => setComment(e.target.value)}
                                    size="small"
                                />
                                <Button variant="contained" onClick={handleAddComment} disabled={!comment.trim()}>Post</Button>
                            </Stack>
                        </CardContent>
                    </Card>
                </Box>
            </Box>
        );
    }

    return (
        <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
                <Typography variant="h4" fontWeight="bold" color="primary">Community</Typography>
                <Button variant="contained" onClick={() => setDialogOpen(true)}>New Topic</Button>
            </Stack>

            <Stack spacing={2}>
                {topics.map(topic => (
                    <Card key={topic.id} onClick={() => handleSelectTopic(topic.id)} sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}>
                        <CardContent>
                            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                                <Box>
                                    <Typography variant="h6" fontWeight="bold">{topic.title}</Typography>
                                    <Typography variant="body2" color="text.secondary" noWrap sx={{ mb: 1 }}>{topic.content}</Typography>
                                </Box>
                                {currentUser && currentUser.id === topic.user_id && (
                                    <IconButton onClick={(e) => handleDeleteTopic(topic.id, e)} color="error" size="small">
                                        <Delete />
                                    </IconButton>
                                )}
                            </Stack>
                            <Stack direction="row" spacing={2} alignItems="center">
                                <Chip size="small" label={`by ${topic.username}`} variant="outlined" />
                                <Typography variant="caption">{new Date(topic.created_at).toLocaleDateString()}</Typography>
                                <Typography variant="caption">• {topic.comment_count} comments</Typography>
                                <Typography variant="caption">• {topic.likes} likes</Typography>
                            </Stack>
                        </CardContent>
                    </Card>
                ))}
            </Stack>

            <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
                <Box sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>Create New Topic</Typography>
                    <TextField
                        fullWidth
                        label="Title"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        margin="normal"
                    />
                    <TextField
                        fullWidth
                        multiline
                        rows={4}
                        label="Content"
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        margin="normal"
                    />
                    <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{ mt: 2 }}>
                        <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                        <Button variant="contained" onClick={handleCreateTopic}>Post</Button>
                    </Stack>
                </Box>
            </Dialog>
        </Box>
    );
};

export default Community;
