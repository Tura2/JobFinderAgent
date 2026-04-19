import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Company } from "../types";

export default function Companies() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", ats_type: "greenhouse", ats_slug: "", career_page_url: "" });

  const refresh = () => api.getCompanies().then(setCompanies);

  useEffect(() => {
    refresh();
  }, []);

  const handleAdd = async () => {
    await api.addCompany(form);
    setForm({ name: "", ats_type: "greenhouse", ats_slug: "", career_page_url: "" });
    setShowAdd(false);
    refresh();
  };

  const handleDelete = async (id: number) => {
    await api.deleteCompany(id);
    refresh();
  };

  const handleToggle = async (company: Company) => {
    await api.updateCompany(company.id, { active: !company.active });
    refresh();
  };

  return (
    <div className="pb-20 pt-4 px-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Watchlist</h1>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium"
        >
          + Add
        </button>
      </div>

      {showAdd && (
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-4 space-y-3">
          <input
            placeholder="Company name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
          />
          <select
            value={form.ats_type}
            onChange={(e) => setForm({ ...form, ats_type: e.target.value })}
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
          >
            <option value="greenhouse">Greenhouse</option>
            <option value="lever">Lever</option>
            <option value="workday">Workday</option>
            <option value="custom">Custom</option>
            <option value="linkedin">LinkedIn</option>
          </select>
          <input
            placeholder="ATS slug (e.g. vercel)"
            value={form.ats_slug}
            onChange={(e) => setForm({ ...form, ats_slug: e.target.value })}
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
          />
          <input
            placeholder="Career page URL (for custom/workday)"
            value={form.career_page_url}
            onChange={(e) => setForm({ ...form, career_page_url: e.target.value })}
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={handleAdd}
            className="w-full py-2 rounded-lg bg-green-600 text-white text-sm font-medium"
          >
            Save
          </button>
        </div>
      )}

      {companies.length === 0 ? (
        <p className="text-center text-gray-500 mt-8">No companies in your watchlist.</p>
      ) : (
        <div className="space-y-2">
          {companies.map((co) => (
            <div
              key={co.id}
              className="flex items-center justify-between bg-gray-900 rounded-lg p-3 border border-gray-800"
            >
              <div>
                <p className={`font-medium text-sm ${co.active ? "" : "text-gray-500 line-through"}`}>
                  {co.name}
                </p>
                <p className="text-xs text-gray-500">{co.ats_type}{co.ats_slug ? ` / ${co.ats_slug}` : ""}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleToggle(co)}
                  className={`text-xs px-2 py-1 rounded ${co.active ? "bg-green-800 text-green-300" : "bg-gray-800 text-gray-500"}`}
                >
                  {co.active ? "Active" : "Paused"}
                </button>
                <button
                  onClick={() => handleDelete(co.id)}
                  className="text-xs px-2 py-1 rounded bg-red-900/50 text-red-400"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
