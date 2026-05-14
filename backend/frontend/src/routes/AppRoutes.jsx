import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import ProtectedRoute from './ProtectedRoute';
import LoginPage from '../pages/LoginPage';
import DashboardPage from '../pages/DashboardPage';
import UploadPage from '../pages/UploadPage';

import AnalyticsPage from '../pages/AnalyticsPage';
import FeedbackExplorerPage from '../pages/FeedbackExplorerPage';
import ClustersPage from '../pages/ClustersPage';
import InsightsPage from '../pages/InsightsPage';
import VisualizationsPage from '../pages/VisualizationsPage';

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="explorer" element={<FeedbackExplorerPage />} />
        <Route path="clusters" element={<ClustersPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="visualizations" element={<VisualizationsPage />} />
        <Route path="settings" element={<div className="text-white p-6">Settings Coming Soon</div>} />
      </Route>

      {/* Fallback route */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
