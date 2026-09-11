import React from 'react';
import { Outlet } from 'react-router-dom';
import { CustomerTopBar } from './CustomerTopBar';

export function CustomerLayout() {
  return (
    <div className="customer-app-layout">
      <CustomerTopBar />
      <main className="customer-main-content">
        <Outlet />
      </main>

      <style>{`
        .customer-app-layout {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          background-color: #f8fafc;
          color: #0f172a;
          font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
        }

        .customer-main-content {
          flex: 1;
          max-width: 1200px;
          width: 100%;
          margin: 0 auto;
          padding: 2rem 1.5rem 3rem 1.5rem;
        }

        @media (max-width: 640px) {
          .customer-main-content {
            padding: 1.25rem 1rem 2rem 1rem;
          }
        }
      `}</style>
    </div>
  );
}

export default CustomerLayout;
