import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute, AdminRoute } from "@/components/layout/ProtectedRoute";
import { UserLayout } from "@/components/layout/UserLayout";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { LandingPage } from "@/pages/public/LandingPage";
import { LoginPage } from "@/pages/public/LoginPage";
import { RegisterPage } from "@/pages/public/RegisterPage";
import { DashboardPage } from "@/pages/user/DashboardPage";
import { BookingPage } from "@/pages/user/BookingPage";
import { MyBookingsPage } from "@/pages/user/MyBookingsPage";
import { BookingDetailPage } from "@/pages/user/BookingDetailPage";
import { AdminLivePage } from "@/pages/admin/AdminLivePage";
import { AdminBookingsPage } from "@/pages/admin/AdminBookingsPage";
import { AdminAnalyticsPage } from "@/pages/admin/AdminAnalyticsPage";
import { AdminSettingsPage } from "@/pages/admin/AdminSettingsPage";
import { CameraManagerPage } from "@/pages/admin/CameraManagerPage";
import { SlotEditorPage } from "@/pages/admin/SlotEditorPage";

export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },

  {
    path: "/app",
    element: <ProtectedRoute><UserLayout /></ProtectedRoute>,
    children: [
      { index: true, element: <Navigate to="dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "book/:slotId", element: <BookingPage /> },
      { path: "bookings", element: <MyBookingsPage /> },
      { path: "bookings/:id", element: <BookingDetailPage /> },
    ],
  },

  {
    path: "/admin",
    element: <AdminRoute><AdminLayout /></AdminRoute>,
    children: [
      { index: true, element: <Navigate to="live" replace /> },
      { path: "live", element: <AdminLivePage /> },
      { path: "bookings", element: <AdminBookingsPage /> },
      { path: "analytics", element: <AdminAnalyticsPage /> },
      { path: "cameras", element: <CameraManagerPage /> },
      { path: "slot-editor", element: <SlotEditorPage /> },
      { path: "settings", element: <AdminSettingsPage /> },
    ],
  },

  { path: "*", element: <Navigate to="/" replace /> },
]);
