import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import MagazinePage from '../pages/MagazinePage';

/**
 * Public-only app for the standalone magazine deployment (Hostinger shared hosting).
 *
 * Ships ONLY the read-only magazine — no auth, no dashboard, no admin code.
 * Every route resolves to the magazine so deep links / refreshes work behind
 * the SPA fallback in .htaccess.
 */
export default function PublicApp() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/magazine" element={<MagazinePage />} />
        <Route path="*" element={<Navigate to="/magazine" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
