import React from "react";
import { Box, Typography, Button, Card, CardContent, Alert } from "@mui/material";
import { ErrorOutline } from "@mui/icons-material";

const toSafeText = (value, fallback = "") => {
  if (value == null) return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (typeof value === "object") {
    if (value.$$typeof || value.type || value.props) {
      return fallback;
    }
    try {
      const json = JSON.stringify(value);
      if (json && json !== "{}") return json;
    } catch {
      /* ignore */
    }
  }
  return fallback;
};
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }
  static getDerivedStateFromError() {
    return { hasError: true, error: null, errorInfo: null };
  }
  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    if (errorInfo?.componentStack) {
      console.error("ErrorBoundary component stack:\n", errorInfo.componentStack);
    }
    try {
      window.__lastReactError = {
        message: error?.message,
        stack: error?.stack,
        componentStack: errorInfo?.componentStack,
        timestamp: Date.now()
      };
      console.groupCollapsed?.("[ErrorBoundary] Stored last React error on window.__lastReactError");
      console.log("Message:", error?.message);
      console.log("Stack:", error?.stack);
      console.log("Component stack:", errorInfo?.componentStack);
      console.groupEnd?.();
    } catch (storageError) {
      console.warn("ErrorBoundary: unable to persist error info", storageError);
    }
    if (error.message && error.message.includes("Objects are not valid as a React child")) {
      console.error("React object error detected:", {
        error: error.message,
        componentStack: errorInfo.componentStack,
        errorBoundary: errorInfo.errorBoundary
      });
    }
    this.setState({
      error,
      errorInfo
    });
  }
  render() {
    if (this.state.hasError) {
      const message = toSafeText(this.state.error?.message, "Something went wrong.");
      const stack = toSafeText(this.state.errorInfo?.componentStack, "");
      const isReactObjectError = message.includes("Objects are not valid as a React child");
      return <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 2
        }}
      >
          <Card sx={{ maxWidth: 600, boxShadow: 8, borderRadius: 3 }}>
            <CardContent sx={{ p: 4, textAlign: "center" }}>
              <ErrorOutline sx={{ fontSize: 80, color: "error.main", mb: 2 }} />

              <Typography variant="h4" gutterBottom sx={{ color: "error.main", fontWeight: "bold" }}>
                {isReactObjectError ? "Data Rendering Error" : "Application Error"}
              </Typography>

              <Typography variant="h6" sx={{ mb: 3, color: "text.secondary" }}>
                {isReactObjectError ? "Invalid data detected in quiz content. This has been automatically handled." : "Something went wrong. Please try again."}
              </Typography>

              {isReactObjectError && <Alert severity="warning" sx={{ mb: 3, textAlign: "left" }}>
                  <Typography variant="body2">
                    <strong>Technical Details:</strong> The application detected an attempt to render complex objects as
                    React children. This has been automatically prevented to maintain application stability.
                  </Typography>
                </Alert>}

              <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
                <Button
        variant="contained"
        onClick={() => {
          this.setState({ hasError: false, error: null, errorInfo: null });
          window.location.reload();
        }}
        size="large"
      >
                  Reload Application
                </Button>
                <Button
        variant="outlined"
        onClick={() => {
          this.setState({ hasError: false, error: null, errorInfo: null });
        }}
        size="large"
      >
                  Try Again
                </Button>
              </Box>

              <Box sx={{ mt: 4, p: 2, bgcolor: "grey.100", borderRadius: 2, textAlign: "left" }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: "bold", mb: 1 }}>
                    Development Error Details:
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.8rem", mb: 1 }}>
                    {message}
                  </Typography>
                  {stack && (
                    <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.75rem", whiteSpace: "pre-line" }}>
                      {stack}
                    </Typography>
                  )}
                </Box>
            </CardContent>
          </Card>
        </Box>;
    }
    return this.props.children;
  }
}
var ErrorBoundary_default = ErrorBoundary;
export {
  ErrorBoundary_default as default
};
