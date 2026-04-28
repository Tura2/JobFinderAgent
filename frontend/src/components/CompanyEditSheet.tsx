import { useState } from 'react';
import { api } from '../api/client';
import type { Company, TestResult } from '../types';

const ATS_TYPES = ['greenhouse', 'lever', 'workday', 'custom', 'linkedin'] as const;

interface Props {
  company: Company;
  onClose: () => void;
  onUpdated: (updated: Company) => void;
}

const inputStyle: React.CSSProperties = {
  width: '100%', background: '#0f172a', border: '1px solid #374151',
  borderRadius: 10, padding: '10px 12px', color: '#f9fafb', fontSize: 14,
  fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box',
};

const labelStyle: React.CSSProperties = {
  color: '#6b7280', fontSize: 11, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '0.06em',
  display: 'block', marginBottom: 5, marginTop: 14,
};

function daysAgo(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}

export default function CompanyEditSheet({ company, onClose, onUpdated }: Props) {
  const [form, setForm] = useState({
    name: company.name,
    ats_type: company.ats_type,
    ats_slug: company.ats_slug ?? '',
    career_page_url: company.career_page_url ?? '',
    linkedin_url: company.linkedin_url ?? '',
  });

  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(
    company.last_test_at
      ? { passed: company.last_test_passed ?? false, jobs_found: company.last_test_jobs_found ?? 0, tested_at: company.last_test_at }
      : null
  );

  const runTest = async () => {
    setIsTesting(true);
    try {
      const result = await api.testCompany(company.id);
      setTestResult(result);
      onUpdated({
        ...company,
        ...form,
        ats_slug: form.ats_slug || null,
        career_page_url: form.career_page_url || null,
        linkedin_url: form.linkedin_url || null,
        last_test_passed: result.passed,
        last_test_jobs_found: result.jobs_found,
        last_test_at: result.tested_at,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveAndTest = async () => {
    const updated = await api.updateCompany(company.id, {
      name: form.name,
      ats_type: form.ats_type,
      ats_slug: form.ats_slug || null,
      career_page_url: form.career_page_url || null,
      linkedin_url: form.linkedin_url || null,
    });
    onUpdated(updated);
    await runTest();
  };

  const needsSlug = form.ats_type === 'greenhouse' || form.ats_type === 'lever';
  const needsCareerUrl = form.ats_type === 'workday' || form.ats_type === 'custom';
  const needsLinkedIn = form.ats_type === 'linkedin';

  const daysUntilRecheck = testResult
    ? Math.max(0, 30 - daysAgo(testResult.tested_at))
    : null;

  return (
    <div style={{ padding: '0 0 8px' }}>
      <label style={labelStyle}>Company name</label>
      <input
        style={inputStyle}
        value={form.name}
        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
      />

      <label style={labelStyle}>ATS type</label>
      <div style={{ display: 'flex', gap: 5, marginTop: 6 }}>
        {ATS_TYPES.map(t => (
          <button
            key={t}
            onClick={() => setForm(f => ({ ...f, ats_type: t }))}
            style={{
              flex: 1, height: 30, borderRadius: 8,
              border: `1px solid ${form.ats_type === t ? '#6366f1' : '#374151'}`,
              background: form.ats_type === t ? '#1e1b4b' : '#1f2937',
              color: form.ats_type === t ? '#818cf8' : '#4b5563',
              fontSize: 10, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
              textTransform: 'capitalize',
            }}
          >{t}</button>
        ))}
      </div>

      {needsSlug && (
        <>
          <label style={labelStyle}>Slug</label>
          <input
            style={inputStyle}
            value={form.ats_slug}
            onChange={e => setForm(f => ({ ...f, ats_slug: e.target.value }))}
            placeholder="e.g. vercel, monday, wix"
          />
        </>
      )}
      {needsCareerUrl && (
        <>
          <label style={labelStyle}>Career page URL</label>
          <input
            type="url"
            style={inputStyle}
            value={form.career_page_url}
            onChange={e => setForm(f => ({ ...f, career_page_url: e.target.value }))}
            placeholder="https://..."
          />
        </>
      )}
      {needsLinkedIn && (
        <>
          <label style={labelStyle}>LinkedIn company URL</label>
          <input
            type="url"
            style={inputStyle}
            value={form.linkedin_url}
            onChange={e => setForm(f => ({ ...f, linkedin_url: e.target.value }))}
            placeholder="https://www.linkedin.com/company/..."
          />
        </>
      )}

      {/* Test result block */}
      <div style={{ marginTop: 14 }}>
        {isTesting ? (
          <div style={{
            background: '#0f172a', border: '1px solid #374151', borderRadius: 12,
            padding: '11px 14px', display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 16 }}>⏳</span>
            <div>
              <div style={{ color: '#9ca3af', fontSize: 13, fontWeight: 600 }}>Testing…</div>
              <div style={{ color: '#4b5563', fontSize: 11, marginTop: 1 }}>Fetching from {form.ats_type}</div>
            </div>
          </div>
        ) : testResult ? (
          <div style={{
            background: testResult.passed ? '#031a0e' : '#1a0505',
            border: `1px solid ${testResult.passed ? '#166534' : '#7f1d1d'}`,
            borderRadius: 12, padding: '11px 14px',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 16 }}>{testResult.passed ? '✅' : '❌'}</span>
            <div>
              <div style={{ color: testResult.passed ? '#22c55e' : '#ef4444', fontSize: 13, fontWeight: 600 }}>
                {testResult.passed ? `Pass — ${testResult.jobs_found} jobs found` : 'Fail — 0 jobs found'}
              </div>
              <div style={{ color: testResult.passed ? '#166534' : '#7f1d1d', fontSize: 11, marginTop: 1 }}>
                Tested {daysAgo(testResult.tested_at)}d ago
                {testResult.passed && daysUntilRecheck !== null && ` · next check in ${daysUntilRecheck}d`}
                {!testResult.passed && ' · check the slug or URL'}
              </div>
            </div>
          </div>
        ) : (
          <div style={{
            background: '#0f172a', border: '1px solid #1f2937', borderRadius: 12,
            padding: '11px 14px', display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 16 }}>⬜</span>
            <div>
              <div style={{ color: '#6b7280', fontSize: 13, fontWeight: 600 }}>Never tested</div>
              <div style={{ color: '#4b5563', fontSize: 11, marginTop: 1 }}>Add the URL and hit Test</div>
            </div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
        <button
          onClick={handleSaveAndTest}
          disabled={isTesting}
          style={{
            flex: 1, height: 44, background: isTesting ? '#374151' : '#6366f1',
            color: '#fff', border: 'none', borderRadius: 12,
            fontSize: 14, fontWeight: 600, cursor: isTesting ? 'default' : 'pointer',
            fontFamily: 'inherit',
          }}
        >
          Save + Test
        </button>
        <button
          onClick={runTest}
          disabled={isTesting}
          style={{
            height: 44, background: '#1f2937', border: '1px solid #374151',
            borderRadius: 12, padding: '0 16px', color: '#9ca3af',
            fontSize: 14, fontWeight: 600, cursor: isTesting ? 'default' : 'pointer',
            fontFamily: 'inherit',
          }}
        >
          ⟳ Test now
        </button>
      </div>
    </div>
  );
}
