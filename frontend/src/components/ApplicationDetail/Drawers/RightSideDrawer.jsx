import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export function RightSideDrawer({
  isOpen,
  onClose,
  title,
  subtitle,
  icon: Icon,
  width = '520px',
  children,
}) {
  // Close drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Lock body scroll when drawer is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div
        className="drawer-container"
        style={{ width: `min(${width}, 100vw)` }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-header-title">
            {Icon && (
              <div className="drawer-icon-wrap">
                <Icon size={20} className="drawer-header-icon" />
              </div>
            )}
            <div>
              <h2 className="drawer-title-text">{title}</h2>
              {subtitle && <p className="drawer-subtitle-text">{subtitle}</p>}
            </div>
          </div>
          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close drawer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="drawer-body">
          {children}
        </div>
      </div>
    </div>
  );
}
