import { render, screen } from "@testing-library/react";
import App from "./App";
test("renders Smart Learning Assistant heading", () => {
  render(<App />);
  const heading = screen.getByText(/Smart Learning Assistant/i);
  expect(heading).toBeInTheDocument();
});
