import React, { useState, useEffect } from 'react';
import {
    Box,
    Container,
    Paper,
    Typography,
    TextField,
    Button,
    Stack,
    Alert,
    Link,
    InputAdornment
} from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Key, Email } from '@mui/icons-material';

function ResetPassword() {
    const [email, setEmail] = useState('');
    const [code, setCode] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const savedEmail = localStorage.getItem('resetPasswordEmail');
        if (savedEmail) {
            setEmail(savedEmail);
        }
    }, []);

    const handleSubmit = async (event) => {
        event.preventDefault();
        setLoading(true);
        setError('');
        setSuccess('');

        try {
            const response = await axios.post('http://localhost:5000/api/auth/reset-password', {
                email,
                code,
                newPassword
            });

            const message = response.data?.message || 'Password reset successful!';
            setSuccess(message);

            // Clear stored email
            localStorage.removeItem('resetPasswordEmail');

            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            let message = 'Failed to reset password.';
            if (err.response?.data?.error) {
                message = err.response.data.error;
            } else if (err.message) {
                message = err.message;
            }
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box
            sx={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: 'background.default',
                py: 4,
                px: 2,
            }}
        >
            <Container maxWidth="xs">
                <Paper
                    elevation={3}
                    sx={{
                        p: 4,
                        borderRadius: 3,
                    }}
                >
                    <Typography variant="h5" sx={{ fontWeight: 700, mb: 1, textAlign: 'center' }}>
                        Reset Password
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
                        Enter the code sent to your email and choose a new password.
                    </Typography>

                    <form onSubmit={handleSubmit}>
                        <Stack spacing={2.5}>
                            <TextField
                                label="Email Address"
                                type="email"
                                size="small"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                fullWidth
                                required
                                InputProps={{
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <Email color="action" fontSize="small" />
                                        </InputAdornment>
                                    ),
                                }}
                            />

                            <TextField
                                label="Verification Code"
                                size="small"
                                value={code}
                                onChange={(e) => setCode(e.target.value)}
                                fullWidth
                                required
                                inputProps={{ maxLength: 6 }}
                            />

                            <TextField
                                label="New Password"
                                type="password"
                                size="small"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                fullWidth
                                required
                                InputProps={{
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <Key color="action" fontSize="small" />
                                        </InputAdornment>
                                    ),
                                }}
                            />

                            <Button
                                type="submit"
                                variant="contained"
                                disabled={loading}
                                fullWidth
                                sx={{
                                    py: 1.2,
                                    fontWeight: 600,
                                    textTransform: 'none',
                                    borderRadius: 2,
                                }}
                            >
                                {loading ? 'Resetting Password...' : 'Reset Password'}
                            </Button>
                        </Stack>
                    </form>

                    {error && (
                        <Alert severity="error" sx={{ mt: 2, py: 0.5 }}>
                            {error}
                        </Alert>
                    )}

                    {success && (
                        <Alert severity="success" sx={{ mt: 2, py: 0.5 }}>
                            {success}
                        </Alert>
                    )}

                    <Typography variant="body2" sx={{ mt: 3, textAlign: 'center' }} color="text.secondary">
                        <Link component={RouterLink} to="/login" fontWeight="bold">
                            Back to Login
                        </Link>
                    </Typography>
                </Paper>
            </Container>
        </Box>
    );
}

export default ResetPassword;
