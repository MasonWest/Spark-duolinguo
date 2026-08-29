import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import Home from "./pages/Home";
import LessonPage from "./pages/LessonPage";
import MapPage from "./pages/MapPage";
import QuizPage from "./pages/QuizPage";
import ReviewPage from "./pages/ReviewPage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/lesson/:id" element={<LessonPage />} />
        <Route path="/lesson/:id/quiz" element={<QuizPage />} />
        {/* Phase 6b: 间隔复习 */}
        <Route path="/review/:id" element={<ReviewPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
