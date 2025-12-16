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
  InputAdornment,
} from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Email, Key, Person } from '@mui/icons-material';

const toText = (value, fallback = '') => {
  if (value == null) return fallback;
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return fallback;
};

function Signup() {
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState({ type: '', message: '' });
  const navigate = useNavigate();

  const showAlert = (type, message) => {
    setAlert({
      type,
      message: toText(message).trim(),
    });
  };

  const clearAlert = () => {
    setAlert({ type: '', message: '' });
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleJumpToVerification = () => {
    try {
      if (form.email) {
        localStorage.setItem('pendingVerificationEmail', form.email);
      }
    } catch (storageErr) {
      console.warn('Unable to persist pending verification email:', storageErr);
    }
    const target = form.email ? `/verify-email?email=${encodeURIComponent(form.email)}` : '/verify-email';
    navigate(target);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    clearAlert();

    try {
      const response = await axios.post('http://localhost:5000/api/auth/signup', {
        name: form.name,
        email: form.email,
        password: form.password,
      });

      const { message, emailSent } = response?.data || {};

      if (emailSent === false) {
        showAlert('warning', 'Account created, but failed to send verification email. Please contact support or try resending later.');
      } else {
        showAlert('success', message || 'Verification code sent! Redirecting...');
      }

      try {
        localStorage.setItem('pendingVerificationEmail', form.email);
      } catch (storageErr) {
        console.warn('Unable to store pending verification email:', storageErr);
      }
      setTimeout(() => navigate(`/verify-email?email=${encodeURIComponent(form.email)}`), 1000);
    } catch (err) {
      let message = 'Failed to sign up. Please try again.';
      if (err?.response?.data) {
        message = err.response.data.error || err.response.data.message || message;
      } else if (err?.message) {
        message = err.message;
      }
      showAlert('error', message);
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
          <Box sx={{ mb: 3, textAlign: 'center' }}>
            <Typography variant="h5" component="h1" gutterBottom fontWeight="bold">
              Sign Up
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Create your account to get started
            </Typography>
          </Box>

          <form onSubmit={handleSubmit}>
            <Stack spacing={2.5}>
              <TextField
                label="Full Name"
                name="name"
                size="small"
                value={form.name}
                onChange={handleChange}
                fullWidth
                required
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person color="action" fontSize="small" />
                    </InputAdornment>
                  ),
                }}
              />

              <Box>
                <TextField
                  label="Email Address"
                  placeholder="you@example.com"
                  name="email"
                  type="email"
                  size="small"
                  value={form.email}
                  onChange={handleChange}
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
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 0.5 }}>
                  <Button
                    size="small"
                    onClick={handleJumpToVerification}
                    sx={{ textTransform: 'none', fontSize: '0.8rem' }}
                  >
                    Already have a code? Verify
                  </Button>
                </Box>
              </Box>

              <TextField
                label="Password"
                name="password"
                type="password"
                size="small"
                value={form.password}
                onChange={handleChange}
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
                sx={{ py: 1.2, borderRadius: 2, textTransform: 'none', fontWeight: 600 }}
              >
                {loading ? 'Creating account...' : 'Sign Up'}
              </Button>
            </Stack>
          </form>

          {alert.message && (
            <Alert severity={alert.type === 'success' ? 'success' : 'error'} sx={{ mt: 2, py: 0.5 }}>
              {alert.message}
            </Alert>
          )}

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Already have an account?{' '}
              <Link component={RouterLink} to="/login" fontWeight="bold">
                Sign in
              </Link>
            </Typography>
          </Box>
          <Typography variant="body2" sx={{ mt: 3, textAlign: 'center' }}>
            <Link component={RouterLink} to="/" color="text.secondary" sx={{ textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>
              ← Back to Home
            </Link>
          </Typography>
        </Paper>
      </Container>
    </Box>
  );
}

export default Signup;

