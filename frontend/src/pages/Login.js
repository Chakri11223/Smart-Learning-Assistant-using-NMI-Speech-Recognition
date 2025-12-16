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
} from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import axios from 'axios';

const toPlainText = (value, fallback) => {
  // Always return a string, never React elements or objects
  if (value == null || value === undefined) return fallback || '';
  if (typeof value === 'string') {
    return value.trim() || fallback || '';
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  // Check for React elements
  if (React.isValidElement(value)) {
    console.warn('Login: React element detected in toPlainText, using fallback');
    return fallback || '';
  }
  // Check for objects that might be React elements
  if (typeof value === 'object') {
    if (value.$$typeof || value.type || value._owner || value._store) {
      console.warn('Login: React element-like object detected, using fallback');
      return fallback || '';
    }
    // Try to extract a message property if it exists
    if (value.message && typeof value.message === 'string') {
      return value.message;
    }
    if (value.error && typeof value.error === 'string') {
      return value.error;
    }
    // Last resort: try to stringify
    try {
      const json = JSON.stringify(value);
      if (json && json !== '{}' && json !== '[]' && json !== 'null') {
        return json;
      }
    } catch {
      /* ignore */
    }
  }
  return fallback || '';
};

function Login({ onAuthSuccess }) {
  const [form, setForm] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  // Safe setters that always ensure string values
  const setErrorSafe = (value) => {
    const safe = toPlainText(value, '');
    setError(safe);
  };

  const setSuccessSafe = (value) => {
    const safe = toPlainText(value, '');
    setSuccess(safe);
  };

  // Force error and success to always be strings on every render
  const safeError = typeof error === 'string' ? error : toPlainText(error, '');
  const safeSuccess = typeof success === 'string' ? success : toPlainText(success, '');

  const handleChange = (event) => {
    const { name, value } = event.target;
    // Ensure we only store strings in form state
    const safeValue = typeof value === 'string' ? value : String(value || '');
    setForm((prev) => ({ ...prev, [name]: safeValue }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setErrorSafe('');
    setSuccessSafe('');

    try {
      const response = await axios.post(
        'http://localhost:5000/api/auth/login',
        {
          email: form.email,
          password: form.password,
        }
      );

      const { token, user, message } = response.data || {};
      if (token && user) {
        try {
          localStorage.setItem('authToken', token);
          localStorage.setItem('authUser', JSON.stringify(user));
        } catch (storageErr) {
          console.warn('Unable to persist auth payload:', storageErr);
        }
        if (typeof onAuthSuccess === 'function') {
          onAuthSuccess(user, token);
        }
        setSuccessSafe(message || 'Login successful.');
        setTimeout(() => navigate('/'), 900);
      } else {
        setErrorSafe('Unexpected response from server.');
      }
    } catch (e) {
      let errorMessage = 'Failed to login. Please try again.';
      if (e && typeof e === 'object') {
        const axiosError = e;
        if (axiosError.response?.data) {
          const errorData = axiosError.response.data;
          if (errorData.error) {
            errorMessage = errorData.error;
          } else if (errorData.message) {
            errorMessage = errorData.message;
          }
        } else if (axiosError.message) {
          errorMessage = axiosError.message;
        }
      } else if (e instanceof Error) {
        errorMessage = e.message;
      }
      setErrorSafe(errorMessage);
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
            Welcome back
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
            Sign in to continue generating quizzes and summaries.
          </Typography>

          <form onSubmit={handleSubmit}>
            <Stack spacing={2.5}>
              <TextField
                label="Email"
                name="email"
                type="email"
                size="small"
                value={String(form.email || '')}
                onChange={handleChange}
                fullWidth
                required
              />
              <TextField
                label="Password"
                name="password"
                type="password"
                size="small"
                value={String(form.password || '')}
                onChange={handleChange}
                fullWidth
                required
              />
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: -1 }}>
                <Link component={RouterLink} to="/forgot-password" sx={{ fontSize: '0.85rem', fontWeight: 500 }}>
                  Forgot Password?
                </Link>
              </Box>
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
                {loading ? 'Signing in...' : 'Sign in'}
              </Button>
            </Stack>
          </form>

          {safeError && safeError.trim() ? (
            <Alert severity="error" sx={{ mt: 2, py: 0.5 }}>
              {String(safeError)}
            </Alert>
          ) : null}

          {safeSuccess && safeSuccess.trim() ? (
            <Alert severity="success" sx={{ mt: 2, py: 0.5 }}>
              {String(safeSuccess)}
            </Alert>
          ) : null}

          <Typography variant="body2" sx={{ mt: 3, textAlign: 'center' }} color="text.secondary">
            Need an account?{' '}
            <Link component={RouterLink} to="/signup" fontWeight="bold">
              Create one
            </Link>
          </Typography>
          <Typography variant="body2" sx={{ mt: 1, textAlign: 'center' }} color="text.secondary">
            No access?{' '}
            <Link component={RouterLink} to="/verify-email" fontWeight="bold">
              Verify email
            </Link>
          </Typography>
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

export default Login;

