import React, { useState } from 'react';
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
import { Email } from '@mui/icons-material';

function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (event) => {
        event.preventDefault();
        setLoading(true);
        setError('');
        setSuccess('');

        try {
            const response = await axios.post('http://localhost:5000/api/auth/forgot-password', {
                email
            });

            const message = response.data?.message || 'Reset code sent!';
            setSuccess(message);

            // Store email for the next step
            try {
                localStorage.setItem('resetPasswordEmail', email);
            } catch (e) { /* ignore */ }

            setTimeout(() => navigate('/reset-password'), 1500);
        } catch (err) {
            let message = 'Failed to send reset code.';
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
                        Forgot Password?
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
                        Enter your email address and we'll send you a code to reset your password.
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
                                {loading ? 'Sending Code...' : 'Send Reset Code'}
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
                        Remember your password?{' '}
                        <Link component={RouterLink} to="/login" fontWeight="bold">
                            Sign in
                        </Link>
                    </Typography>
                </Paper>
            </Container>
        </Box>
    );
}

export default ForgotPassword;
