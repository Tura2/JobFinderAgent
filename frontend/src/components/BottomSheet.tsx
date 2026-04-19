import { useState, useEffect } from "react";

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export default function BottomSheet({ isOpen, onClose, children }: BottomSheetProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setVisible(true);
    } else {
      const t = setTimeout(() => setVisible(false), 300);
      return () => clearTimeout(t);
    }
  }, [isOpen]);

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50" data-testid="bottom-sheet">
      <div
        className={`absolute inset-0 bg-black/50 transition-opacity ${isOpen ? "opacity-100" : "opacity-0"}`}
        onClick={onClose}
      />
      <div
        className={`absolute bottom-0 left-0 right-0 bg-gray-900 rounded-t-2xl max-h-[85vh] overflow-y-auto transition-transform ${
          isOpen ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="w-12 h-1.5 bg-gray-600 rounded-full mx-auto mt-3 mb-4" />
        <div className="px-4 pb-8">{children}</div>
      </div>
    </div>
  );
}
