interface ConfirmAppliedProps {
  isOpen: boolean;
  jobTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmApplied({ isOpen, jobTitle, onConfirm, onCancel }: ConfirmAppliedProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="confirm-dialog">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div className="relative bg-gray-900 rounded-2xl p-6 mx-4 max-w-sm w-full border border-gray-800">
        <h3 className="text-lg font-semibold text-white mb-2">Did you submit?</h3>
        <p className="text-sm text-gray-400 mb-6">
          Confirm that you completed the application for <strong>{jobTitle}</strong>.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-lg bg-gray-800 text-gray-400 hover:bg-gray-700 font-medium"
          >
            Not yet
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-2.5 rounded-lg bg-green-600 text-white hover:bg-green-500 font-medium"
          >
            Yes, submitted
          </button>
        </div>
      </div>
    </div>
  );
}
