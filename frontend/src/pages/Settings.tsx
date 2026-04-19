import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { ScanStatus } from "../types";

export default function Settings() {
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    api.getScanStatus().then(setScanStatus);
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      await api.triggerScan();
      setTimeout(async () => {
        const status = await api.getScanStatus();
        setScanStatus(status);
        setScanning(false);
      }, 2000);
    } catch {
      setScanning(false);
    }
  };

  return (
    <div className="pb-20 pt-4 px-4">
      <h1 className="text-xl font-bold mb-6">Settings</h1>

      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-4">
        <h2 className="font-semibold mb-3">Scanner</h2>
        {scanStatus && (
          <div className="text-sm text-gray-400 space-y-1 mb-4">
            <p>Last scan: {scanStatus.last_scan_at || "Never"}</p>
            <p>New jobs found: {scanStatus.last_scan_new_jobs}</p>
            <p>Status: {scanStatus.is_running ? "Running..." : "Idle"}</p>
          </div>
        )}
        <button
          onClick={handleScan}
          disabled={scanning}
          className="w-full py-2.5 rounded-lg bg-blue-600 text-white font-medium disabled:opacity-50"
        >
          {scanning ? "Scanning..." : "Scan Now"}
        </button>
      </div>

      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <h2 className="font-semibold mb-2">About</h2>
        <p className="text-sm text-gray-400">JobFinder Agent v0.1.0</p>
        <p className="text-xs text-gray-600 mt-1">Autonomous job hunting pipeline</p>
      </div>
    </div>
  );
}
