import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Box,
    Container,
    Typography,
    Grid,
    Paper,
    Card,
    CardContent,
    CircularProgress,
    Alert,
    List,
    ListItem,
    ListItemText,
    Chip,
    Divider
} from '@mui/material';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    Radar,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Legend
} from 'recharts';
import { TrendingUp, Warning, Assessment, Delete } from '@mui/icons-material';
import { IconButton } from '@mui/material';

const Analytics = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchAnalytics();
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

    const fetchAnalytics = async () => {
        try {
            const res = await axios.get('http://localhost:5000/api/analytics/dashboard', {
                headers: getAuthHeaders()
            });
            setData(res.data);
        } catch (err) {
            console.error("Failed to fetch analytics", err);
            setError("Failed to load analytics data. Please try again later.");
        }
        setLoading(false);
    };

    const handleDeleteFocusArea = async (id) => {
        try {
            await axios.delete(`http://localhost:5000/api/analytics/focus-area/${id}`, {
                headers: getAuthHeaders()
            });
            // Update local state to remove the item
            setData(prev => ({
                ...prev,
                weak_areas: prev.weak_areas.filter(item => item.id !== id)
            }));
        } catch (err) {
            console.error("Failed to delete focus area", err);
            // Optionally show an error message
        }
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Container maxWidth="lg" sx={{ mt: 4 }}>
                <Alert severity="error">{error}</Alert>
            </Container>
        );
    }

    if (!data || data.total_quizzes === 0) {
        return (
            <Container maxWidth="lg" sx={{ mt: 4 }}>
                <Paper sx={{ p: 4, textAlign: 'center', borderRadius: 4 }}>
                    <Assessment sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h5" gutterBottom>
                        No Data Available
                    </Typography>
                    <Typography color="text.secondary">
                        Take some quizzes to see your learning analytics here!
                    </Typography>
                </Paper>
            </Container>
        );
    }

    return (
        <Box sx={{ bgcolor: 'background.default', minHeight: '100vh', py: 4 }}>
            <Container maxWidth="lg">
                <Typography variant="h4" fontWeight="bold" gutterBottom sx={{ mb: 4, color: 'primary.main' }}>
                    Learning Analytics
                </Typography>

                {/* Summary Cards */}
                <Grid container spacing={3} sx={{ mb: 4 }}>
                    <Grid item xs={12} md={6}>
                        <Card sx={{ borderRadius: 3, boxShadow: 2 }}>
                            <CardContent sx={{ display: 'flex', alignItems: 'center', p: 3 }}>
                                <Box sx={{ p: 2, borderRadius: '50%', bgcolor: 'primary.light', color: 'primary.contrastText', mr: 3 }}>
                                    <Assessment fontSize="large" />
                                </Box>
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {data.total_quizzes}
                                    </Typography>
                                    <Typography variant="subtitle1" color="text.secondary">
                                        Total Quizzes Taken
                                    </Typography>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={6}>
                        <Card sx={{ borderRadius: 3, boxShadow: 2 }}>
                            <CardContent sx={{ display: 'flex', alignItems: 'center', p: 3 }}>
                                <Box sx={{ p: 2, borderRadius: '50%', bgcolor: data.average_score >= 70 ? 'success.light' : 'warning.light', color: 'white', mr: 3 }}>
                                    <TrendingUp fontSize="large" />
                                </Box>
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {data.average_score}%
                                    </Typography>
                                    <Typography variant="subtitle1" color="text.secondary">
                                        Average Score
                                    </Typography>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <Card sx={{ borderRadius: 3, boxShadow: 2 }}>
                            <CardContent sx={{ display: 'flex', alignItems: 'center', p: 3 }}>
                                <Box sx={{ p: 2, borderRadius: '50%', bgcolor: 'orange', color: 'white', mr: 3 }}>
                                    <span style={{ fontSize: '2rem' }}>🔥</span>
                                </Box>
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {data.streak?.current || 0}
                                    </Typography>
                                    <Typography variant="subtitle1" color="text.secondary">
                                        Day Streak
                                    </Typography>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>

                {/* Additional Charts Row */}
                <Grid container spacing={3} sx={{ mb: 4 }}>
                    {/* Subject Mastery (Bar Chart) */}
                    <Grid item xs={12} md={7}>
                        <Paper sx={{ p: 3, borderRadius: 3, boxShadow: 2, height: '100%', minHeight: 350 }}>
                            <Typography variant="h6" fontWeight="bold" gutterBottom>
                                Subject Mastery
                            </Typography>
                            {data.mastery_distribution && data.mastery_distribution.length > 0 ? (
                                <Box sx={{ height: 300, mt: 2 }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart
                                            data={data.mastery_distribution}
                                            layout="vertical"
                                            margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                            <XAxis type="number" domain={[0, 100]} hide />
                                            <YAxis
                                                dataKey="subject"
                                                type="category"
                                                tick={{ fontSize: 11, width: 100 }}
                                                width={100}
                                            />
                                            <Tooltip
                                                cursor={{ fill: 'transparent' }}
                                                contentStyle={{ borderRadius: 8 }}
                                            />
                                            <Bar dataKey="score" fill="#3B82F6" radius={[0, 4, 4, 0]} barSize={20} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </Box>
                            ) : (
                                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 250 }}>
                                    <Typography color="text.secondary">Take quizzes to see mastery.</Typography>
                                </Box>
                            )}
                        </Paper>
                    </Grid>

                    {/* Activity Breakdown (Pie Chart) */}
                    <Grid item xs={12} md={5}>
                        <Paper sx={{ p: 3, borderRadius: 3, boxShadow: 2, height: '100%', minHeight: 350 }}>
                            <Typography variant="h6" fontWeight="bold" gutterBottom>
                                Activity Distribution
                            </Typography>
                            {data.activity_breakdown && data.activity_breakdown.length > 0 ? (
                                <Box sx={{ height: 300, mt: 2 }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={data.activity_breakdown}
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={60}
                                                outerRadius={100}
                                                paddingAngle={5}
                                                dataKey="value"
                                            >
                                                {data.activity_breakdown.map((entry, index) => (
                                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                                ))}
                                            </Pie>
                                            <Tooltip contentStyle={{ borderRadius: 8 }} />
                                            <Legend verticalAlign="bottom" height={36} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </Box>
                            ) : (
                                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 250 }}>
                                    <Typography color="text.secondary">No activity data yet.</Typography>
                                </Box>
                            )}
                        </Paper>
                    </Grid>
                </Grid>

                <Grid container spacing={3}>
                    {/* Progress Chart */}
                    <Grid item xs={12} md={8}>
                        <Paper sx={{ p: 3, borderRadius: 3, boxShadow: 2, height: '100%' }}>
                            <Typography variant="h6" fontWeight="bold" gutterBottom>
                                Performance Trend
                            </Typography>
                            <Box sx={{ height: 300, mt: 2 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={data.recent_activity}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                                        <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                                        <Tooltip
                                            contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                                        />
                                        <ReferenceLine y={60} stroke="red" strokeDasharray="3 3" label="Pass" />
                                        <Line
                                            type="monotone"
                                            dataKey="score"
                                            stroke="#1976d2"
                                            strokeWidth={3}
                                            dot={{ r: 4, fill: '#1976d2' }}
                                            activeDot={{ r: 6 }}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </Box>
                        </Paper>
                    </Grid>

                    {/* Weak Areas */}
                    <Grid item xs={12} md={4}>
                        <Paper sx={{ p: 3, borderRadius: 3, boxShadow: 2, height: '100%' }}>
                            <Typography variant="h6" fontWeight="bold" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                                <Warning color="warning" sx={{ mr: 1 }} />
                                Focus Areas
                            </Typography>
                            <Typography variant="body2" color="text.secondary" paragraph>
                                Quizzes where you scored below 60%. Consider reviewing these topics.
                            </Typography>

                            {data.weak_areas.length > 0 ? (
                                <List>
                                    {data.weak_areas.map((item) => (
                                        <React.Fragment key={item.id}>
                                            <ListItem
                                                alignItems="flex-start"
                                                sx={{ px: 0 }}
                                                secondaryAction={
                                                    <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteFocusArea(item.id)}>
                                                        <Delete />
                                                    </IconButton>
                                                }
                                            >
                                                <ListItemText
                                                    primary={
                                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mr: 6 }}>
                                                            <Typography variant="subtitle2" fontWeight="bold">
                                                                {item.title}
                                                            </Typography>
                                                            {item.video_suggestion_url && (
                                                                <Chip
                                                                    label="Watch Video"
                                                                    component="a"
                                                                    href={item.video_suggestion_url}
                                                                    target="_blank"
                                                                    clickable
                                                                    color="primary"
                                                                    size="small"
                                                                    variant="outlined"
                                                                    sx={{ ml: 1, height: 24, fontSize: '0.7rem', cursor: 'pointer' }}
                                                                />
                                                            )}
                                                        </Box>
                                                    }
                                                    secondary={
                                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5, mr: 6 }}>
                                                            <Typography variant="caption" color="text.secondary">
                                                                {item.date}
                                                            </Typography>
                                                            <Chip
                                                                label={`${item.score}%`}
                                                                size="small"
                                                                color="error"
                                                                variant="outlined"
                                                                sx={{ height: 20, fontSize: '0.7rem' }}
                                                            />
                                                        </Box>
                                                    }
                                                />
                                            </ListItem>
                                            <Divider component="li" />
                                        </React.Fragment>
                                    ))}
                                </List>
                            ) : (
                                <Box sx={{ py: 4, textAlign: 'center' }}>
                                    <Typography color="success.main" fontWeight="medium">
                                        Great job! No weak areas detected recently.
                                    </Typography>
                                </Box>
                            )}
                        </Paper>
                    </Grid>
                </Grid>
            </Container>
        </Box>
    );
};

export default Analytics;
