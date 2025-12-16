import React from "react";
import { Typography } from "@mui/material";
const SafeText = ({
  children,
  variant = "body1",
  component = "span",
  debugLabel = "SafeText",
  ...props
}) => {
  const devMode = typeof process !== "undefined" ? process.env?.NODE_ENV !== "production" : true;
  const emitLog = React.useCallback((reason, value) => {
    if (!devMode) return;
    try {
      console.groupCollapsed?.(`[SafeText:${debugLabel}] ${reason}`);
      console.log("Raw value:", value);
      console.trace?.("Trace");
    } catch (loggingError) {
      console.warn("SafeText logging failed:", loggingError);
    } finally {
      if (console.groupEnd && devMode) {
        console.groupEnd();
      }
    }
  }, [debugLabel, devMode]);
  const safeContent = React.useMemo(() => {
    if (children == null) return "";
    const MAX_DEPTH = 4;
    const toStringPrimitive = (value, depth = 0) => {
      if (value == null) return "";
      if (depth > MAX_DEPTH) {
        emitLog("Max depth reached", value);
        return "[Nested Content]";
      }
      if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
        return String(value);
      }
      if (React.isValidElement(value)) {
        emitLog("React element detected", value);
        return "[React Element]";
      }
      if (Array.isArray(value)) {
        emitLog("Array detected", value);
        return value.map((item) => toStringPrimitive(item, depth + 1)).filter(Boolean).join(" ");
      }
      if (typeof value === "object") {
        emitLog("Object detected", value);
        try {
          return JSON.stringify(value);
        } catch (jsonError) {
          emitLog("Object stringify failed", { value, jsonError });
          return "[Object]";
        }
      }
      try {
        return String(value);
      } catch (stringError) {
        emitLog("String conversion failed", { value, stringError });
        return "[Invalid Content]";
      }
    };
    return toStringPrimitive(children);
  }, [children, emitLog]);
  return <Typography variant={variant} component={component} {...props}>
      {safeContent}
    </Typography>;
};
var SafeText_default = SafeText;
export {
  SafeText_default as default
};
