import { useEffect, useState } from 'react';
import { X } from 'lucide-react';

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  title?: string;
}

export default function BottomSheet({ isOpen, onClose, children, title }: BottomSheetProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setMounted(true);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
      const t = setTimeout(() => setMounted(false), 320);
      return () => clearTimeout(t);
    }
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  if (!mounted) return null;

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 50 }} role="dialog" aria-modal="true">
      {/* Scrim */}
      <div
        style={{
          position: 'absolute', inset: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(4px)',
          opacity: isOpen ? 1 : 0,
          transition: 'opacity 0.3s',
        }}
        onClick={onClose}
        aria-hidden
      />

      {/* Sheet */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        background: '#111827',
        borderRadius: '24px 24px 0 0',
        borderTop: '1px solid #1f2937',
        maxHeight: '90%',
        display: 'flex', flexDirection: 'column',
        transform: isOpen ? 'translateY(0)' : 'translateY(100%)',
        transition: 'transform 0.32s cubic-bezier(0.4,0,0.2,1)',
      }}>
        {/* Drag handle */}
        <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 4px' }}>
          <div style={{ width: 40, height: 4, background: '#374151', borderRadius: 2 }} />
        </div>

        {/* Optional title header */}
        {title && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '4px 20px 8px', flexShrink: 0,
          }}>
            <span style={{ fontWeight: 600, fontSize: 16, color: '#f9fafb' }}>{title}</span>
            <button
              onClick={onClose}
              style={{
                width: 32, height: 32, background: '#1f2937', border: 'none',
                borderRadius: 8, display: 'flex', alignItems: 'center',
                justifyContent: 'center', cursor: 'pointer',
              }}
              aria-label="Close"
            >
              <X size={15} color="#9ca3af" />
            </button>
          </div>
        )}

        {/* Content */}
        <div style={{ overflowY: 'auto', flex: 1, padding: '10px 20px 40px', scrollbarWidth: 'none' }}>
          {children}
        </div>
      </div>
    </div>
  );
}
