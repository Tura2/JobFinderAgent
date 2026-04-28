import { useState, useEffect } from 'react';
import { Plus, Power, Trash2, Building2 } from 'lucide-react';
import { api } from '../api/client';
import type { Company } from '../types';
import BottomSheet from '../components/BottomSheet';
import CompanyEditSheet from '../components/CompanyEditSheet';

const ATS_TYPES = ['greenhouse', 'lever', 'workday', 'custom', 'linkedin'] as const;

const emptyForm = {
  name: '', ats_type: 'greenhouse', ats_slug: '', career_page_url: '', linkedin_url: '',
};

function daysAgo(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}

function TestBadge({ company }: { company: Company }) {
  const dotColor = company.last_test_passed === null
    ? '#374151'
    : company.last_test_passed ? '#22c55e' : '#ef4444';

  const dotShadow = company.last_test_passed === true
    ? '0 0 5px rgba(34,197,94,0.5)'
    : company.last_test_passed === false
      ? '0 0 5px rgba(239,68,68,0.5)'
      : 'none';

  const pillBg = company.last_test_passed === false ? '#1a0505' : '#1f2937';
  const pillColor = company.last_test_passed === false ? '#ef4444' : '#4b5563';

  return (
    <>
      <span style={{
        width: 7, height: 7, borderRadius: '50%', flexShrink: 0, display: 'inline-block',
        background: dotColor, boxShadow: dotShadow,
      }} />
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 3,
        background: pillBg, borderRadius: 6, padding: '1px 5px',
        fontSize: 10, color: pillColor, flexShrink: 0,
      }}>
        {company.last_test_at ? `🕐 ${daysAgo(company.last_test_at)}d` : '— never'}
      </span>
    </>
  );
}

export default function Companies() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);

  const refresh = () => api.getCompanies().then(setCompanies);
  useEffect(() => { refresh(); }, []);

  const handleAdd = async () => {
    if (!form.name.trim()) return;
    await api.addCompany(form);
    setForm(emptyForm);
    setShowAdd(false);
    refresh();
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm('Remove this company from your watchlist?')) return;
    await api.deleteCompany(id);
    refresh();
  };

  const handleToggle = async (e: React.MouseEvent, company: Company) => {
    e.stopPropagation();
    await api.updateCompany(company.id, { active: !company.active });
    refresh();
  };

  const handleCompanyUpdated = (updated: Company) => {
    setCompanies(cs => cs.map(c => c.id === updated.id ? updated : c));
    if (selectedCompany?.id === updated.id) setSelectedCompany(updated);
  };

  const needsSlug = form.ats_type === 'greenhouse' || form.ats_type === 'lever';
  const needsCareerUrl = form.ats_type === 'workday' || form.ats_type === 'custom';
  const needsLinkedIn = form.ats_type === 'linkedin';
  const active = companies.filter(c => c.active).length;

  const inputStyle: React.CSSProperties = {
    width: '100%', background: '#0f172a', border: '1px solid #374151',
    borderRadius: 10, padding: '10px 12px', color: '#f9fafb', fontSize: 14,
    fontFamily: 'inherit', outline: 'none',
  };

  return (
    <div style={{ paddingBottom: 96, paddingTop: 24, paddingInline: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
        <div>
          <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 700, letterSpacing: '-0.03em' }}>Watchlist</h1>
          <p style={{ color: '#4b5563', fontSize: 13, marginTop: 2 }}>
            {active} active · {companies.length} total
          </p>
        </div>
        <button
          onClick={() => setShowAdd(v => !v)}
          style={{
            height: 36, background: '#6366f1', color: '#fff', border: 'none',
            borderRadius: 10, padding: '0 14px', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 13, fontWeight: 600, fontFamily: 'inherit', flexShrink: 0,
          }}
        >
          <Plus size={13} color="#fff" /> Add
        </button>
      </div>

      {showAdd && (
        <div style={{
          background: '#111827', border: '1px solid #1f2937', borderRadius: 16,
          padding: 14, marginBottom: 10,
        }}>
          <div style={{ color: '#4b5563', fontSize: 12, marginBottom: 8 }}>New company</div>
          <input
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
            placeholder="Company name"
            style={{ ...inputStyle, marginBottom: 8 }}
          />
          <div style={{ display: 'flex', gap: 5, marginBottom: 10 }}>
            {ATS_TYPES.map(t => (
              <button key={t} onClick={() => setForm({ ...form, ats_type: t })} style={{
                flex: 1, height: 28,
                background: form.ats_type === t ? '#1e1b4b' : '#1f2937',
                border: `1px solid ${form.ats_type === t ? '#6366f1' : '#374151'}`,
                borderRadius: 8, color: form.ats_type === t ? '#818cf8' : '#4b5563',
                fontSize: 10, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
                textTransform: 'capitalize',
              }}>{t}</button>
            ))}
          </div>
          {needsSlug && (
            <input
              placeholder={`${form.ats_type === 'greenhouse' ? 'Greenhouse' : 'Lever'} slug (e.g. vercel)`}
              value={form.ats_slug}
              onChange={e => setForm({ ...form, ats_slug: e.target.value })}
              style={{ ...inputStyle, marginBottom: 8 }}
            />
          )}
          {needsCareerUrl && (
            <input type="url" placeholder="Career page URL"
              value={form.career_page_url}
              onChange={e => setForm({ ...form, career_page_url: e.target.value })}
              style={{ ...inputStyle, marginBottom: 8 }}
            />
          )}
          {needsLinkedIn && (
            <input type="url" placeholder="LinkedIn company URL"
              value={form.linkedin_url}
              onChange={e => setForm({ ...form, linkedin_url: e.target.value })}
              style={{ ...inputStyle, marginBottom: 8 }}
            />
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => { setShowAdd(false); setForm(emptyForm); }}
              style={{
                flex: 1, height: 38, background: '#1f2937', color: '#6b7280',
                border: 'none', borderRadius: 12, cursor: 'pointer',
                fontSize: 13, fontWeight: 600, fontFamily: 'inherit',
              }}
            >Cancel</button>
            <button
              onClick={handleAdd}
              disabled={!form.name.trim()}
              style={{
                flex: 1, height: 38, background: '#6366f1', color: '#fff',
                border: 'none', borderRadius: 12, cursor: 'pointer',
                fontSize: 13, fontWeight: 600, fontFamily: 'inherit',
                opacity: form.name.trim() ? 1 : 0.4,
              }}
            >Add</button>
          </div>
        </div>
      )}

      {companies.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '64px 0' }}>
          <div style={{
            background: '#1a1f2e', border: '1px solid #1f2937', borderRadius: '50%',
            width: 72, height: 72, display: 'flex', alignItems: 'center',
            justifyContent: 'center', margin: '0 auto 16px',
          }}>
            <Building2 size={30} color="#374151" />
          </div>
          <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 16, marginBottom: 6 }}>No companies yet</div>
          <div style={{ color: '#4b5563', fontSize: 13 }}>Add companies to start scanning for jobs.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {companies.map(co => (
            <div
              key={co.id}
              onClick={() => setSelectedCompany(co)}
              style={{
                background: '#111827', border: '1px solid #1f2937',
                borderRadius: 16, padding: '12px 14px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
                cursor: 'pointer',
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ color: co.active ? '#f9fafb' : '#4b5563', fontWeight: 600, fontSize: 15 }}>
                  {co.name}
                </div>
                <div style={{ color: '#374151', fontSize: 12, marginTop: 3, display: 'flex', alignItems: 'center', gap: 5 }}>
                  <TestBadge company={co} />
                  <span>{co.ats_type}{co.ats_slug ? ` · ${co.ats_slug}` : ''}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <button
                  onClick={e => handleToggle(e, co)}
                  style={{
                    background: co.active ? '#031a0e' : '#1a1f2e',
                    border: `1px solid ${co.active ? '#166534' : '#1f2937'}`,
                    borderRadius: 8, padding: '6px 10px', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 5,
                    fontSize: 12, fontWeight: 600,
                    color: co.active ? '#22c55e' : '#4b5563',
                    fontFamily: 'inherit',
                  }}
                  aria-label={co.active ? 'Pause' : 'Activate'}
                >
                  <Power size={11} color={co.active ? '#22c55e' : '#4b5563'} />
                  {co.active ? 'Active' : 'Paused'}
                </button>
                <button
                  onClick={e => handleDelete(e, co.id)}
                  style={{
                    background: '#1a0a0a', border: '1px solid #3f1010',
                    borderRadius: 8, padding: 7, cursor: 'pointer',
                    display: 'flex', alignItems: 'center',
                  }}
                  aria-label={`Remove ${co.name}`}
                >
                  <Trash2 size={14} color="#ef4444" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <BottomSheet
        isOpen={selectedCompany !== null}
        onClose={() => setSelectedCompany(null)}
        title={selectedCompany?.name ?? ''}
      >
        {selectedCompany && (
          <CompanyEditSheet
            company={selectedCompany}
            onClose={() => setSelectedCompany(null)}
            onUpdated={handleCompanyUpdated}
          />
        )}
      </BottomSheet>
    </div>
  );
}
