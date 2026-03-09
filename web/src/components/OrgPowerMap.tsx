type RoleTag = 'Decision Maker' | 'Influencer' | 'Champion' | 'End User';

interface OrgRole {
  title: string;
  product: string;
  roleTag: RoleTag;
}

interface Department {
  key: string;
  label: string;
  roles: OrgRole[];
}

const departments: Department[] = [
  {
    key: 'engineering',
    label: 'Engineering',
    roles: [
      { title: 'CTO', product: 'Enterprise', roleTag: 'Decision Maker' },
      { title: 'VP Engineering', product: 'Claude Code', roleTag: 'Influencer' },
      { title: 'Dir. Engineering', product: 'Claude Code', roleTag: 'Influencer' },
      { title: 'Eng Manager', product: 'Claude Code', roleTag: 'End User' },
    ],
  },
  {
    key: 'sales',
    label: 'Sales',
    roles: [
      { title: 'CRO', product: 'Enterprise', roleTag: 'Decision Maker' },
      { title: 'VP Sales', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Dir. Sales', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Sales Manager', product: 'Claude.ai', roleTag: 'End User' },
    ],
  },
  {
    key: 'marketing',
    label: 'Marketing',
    roles: [
      { title: 'CMO', product: 'Enterprise', roleTag: 'Decision Maker' },
      { title: 'VP Marketing', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Dir. Marketing', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Mktg Manager', product: 'Claude.ai', roleTag: 'End User' },
    ],
  },
  {
    key: 'product',
    label: 'Product',
    roles: [
      { title: 'CPO', product: 'Enterprise', roleTag: 'Decision Maker' },
      { title: 'VP Product', product: 'API', roleTag: 'Influencer' },
      { title: 'Dir. Product', product: 'API', roleTag: 'Influencer' },
      { title: 'Product Manager', product: 'API', roleTag: 'End User' },
    ],
  },
  {
    key: 'legal',
    label: 'Legal',
    roles: [
      { title: 'General Counsel', product: 'Enterprise', roleTag: 'Decision Maker' },
      { title: 'VP Legal', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Dir. Legal', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Legal Counsel', product: 'Claude.ai', roleTag: 'End User' },
    ],
  },
  {
    key: 'support',
    label: 'Support',
    roles: [
      { title: 'CCO', product: 'Enterprise', roleTag: 'Decision Maker' },
      { title: 'VP Support', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Dir. Support', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Support Mgr', product: 'Claude.ai', roleTag: 'End User' },
    ],
  },
  {
    key: 'hr',
    label: 'HR',
    roles: [
      { title: 'CHRO', product: 'Enterprise', roleTag: 'Decision Maker' },
      { title: 'VP People', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Dir. People', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'HR Manager', product: 'Claude.ai', roleTag: 'End User' },
    ],
  },
  {
    key: 'finance',
    label: 'Finance',
    roles: [
      { title: 'CFO', product: 'Enterprise', roleTag: 'Decision Maker' },
      { title: 'VP Finance', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Dir. Finance', product: 'Claude.ai', roleTag: 'Influencer' },
      { title: 'Finance Mgr', product: 'Claude.ai', roleTag: 'End User' },
    ],
  },
];

/* ── Contact matching ─────────────────────────────────────────── */

function matchContact(
  senderTitle: string | null,
): { deptKey: string; roleIndex: number } | null {
  if (!senderTitle) return null;
  const t = senderTitle.toLowerCase();

  let roleIndex = 3;
  if (/\b(ceo|cto|cfo|cmo|coo|cro|cpo|cco|chro|chief|founder|general counsel)\b/.test(t))
    roleIndex = 0;
  else if (/\b(vp|vice president|svp|evp|head of|head)\b/.test(t))
    roleIndex = 1;
  else if (/\bdirector\b/.test(t))
    roleIndex = 2;

  const matchers: [string, RegExp][] = [
    ['engineering', /\b(engineer|engineering|software|developer|technical|tech|ai[/ ]|ai$|ml|platform|infrastructure|devops|cto)\b/],
    ['sales', /\b(sales|revenue|business development|account|cro)\b/],
    ['marketing', /\b(marketing|growth|brand|communications|content|demand|cmo)\b/],
    ['product', /\b(product|pm|ux|design|cpo)\b/],
    ['legal', /\b(legal|counsel|compliance|regulatory|attorney)\b/],
    ['support', /\b(support|success|customer|service|cx|cco)\b/],
    ['hr', /\b(people|human resources|hr|talent|recruiting|culture|chro)\b/],
    ['finance', /\b(finance|financial|accounting|treasury|controller|cfo)\b/],
  ];

  for (const [deptKey, regex] of matchers) {
    if (regex.test(t)) return { deptKey, roleIndex };
  }

  if (roleIndex === 0) return { deptKey: 'engineering', roleIndex: 0 };

  return null;
}

/* ── Style maps ───────────────────────────────────────────────── */

const roleTagColors: Record<string, string> = {
  'Decision Maker': 'bg-red-900/30 text-red-300',
  Influencer: 'bg-amber-900/30 text-amber-300',
  Champion: 'bg-blue-900/30 text-blue-300',
  'End User': 'bg-white/5 text-[var(--text-muted)]',
};

const productColors: Record<string, string> = {
  Enterprise: 'text-purple-400',
  'Claude Code': 'text-emerald-400',
  'Claude.ai': 'text-blue-400',
  API: 'text-orange-400',
};

/* ── Component ────────────────────────────────────────────────── */

export default function OrgPowerMap({
  senderName,
  senderTitle,
  companyName,
}: {
  senderName: string | null;
  senderTitle: string | null;
  companyName: string | null;
}) {
  const match = matchContact(senderTitle);
  const isCeoContact =
    senderTitle != null && /\b(ceo|coo|founder|co-founder)\b/i.test(senderTitle) &&
    !(/\b(cto|cfo|cmo|cro|cpo)\b/i.test(senderTitle));

  return (
    <div
      className="rounded-xl p-5 mb-4 animate-fade-in-up"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <svg className="h-4 w-4" style={{ color: 'var(--text-muted)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          Account Org Power Map
        </h2>
        {(match || isCeoContact) && (
          <span
            className="text-xs px-2.5 py-1 rounded-full font-semibold"
            style={{ background: 'rgba(212, 165, 116, 0.12)', color: 'var(--accent)' }}
          >
            Entry point: {senderName || senderTitle}
          </span>
        )}
      </div>

      <div className="overflow-x-auto pb-2">
        <div className="min-w-[820px]">
          {/* CEO node — centered at top */}
          <div className="flex justify-center">
            <div
              className={`rounded-lg px-5 py-2.5 text-center text-xs shadow-sm ${
                isCeoContact
                  ? 'border-2 ring-2'
                  : ''
              }`}
              style={
                isCeoContact
                  ? { borderColor: 'var(--accent)', background: 'rgba(212, 165, 116, 0.1)', ringColor: 'rgba(212, 165, 116, 0.2)' }
                  : { background: 'rgba(245, 240, 232, 0.08)', border: '1px solid var(--border)' }
              }
            >
              {isCeoContact && (
                <div className="text-[8px] font-bold uppercase tracking-widest mb-0.5" style={{ color: 'var(--accent)' }}>
                  ★ Entry Point
                </div>
              )}
              <div className="font-bold" style={{ color: isCeoContact ? 'var(--accent)' : 'var(--text-primary)' }}>
                {isCeoContact ? senderName || 'CEO' : 'CEO'}
              </div>
              <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {companyName || 'Company'} Leadership
              </div>
            </div>
          </div>

          {/* Vertical connector from CEO */}
          <div className="flex justify-center">
            <div className="w-px h-4" style={{ background: 'var(--border)' }} />
          </div>

          {/* Horizontal connecting bar */}
          <div className="mx-[6%]" style={{ borderTop: '2px solid var(--border)' }} />

          {/* Department columns */}
          <div className="grid grid-cols-8 gap-1.5">
            {departments.map((dept) => (
              <div key={dept.key} className="flex flex-col items-center">
                {/* Vertical drop from horizontal bar */}
                <div className="w-px h-3" style={{ background: 'var(--border)' }} />

                {/* Department label */}
                <div className="text-[9px] font-bold uppercase tracking-wider mb-1.5 text-center leading-tight" style={{ color: 'var(--text-muted)' }}>
                  {dept.label}
                </div>

                {/* Role nodes */}
                {dept.roles.map((role, i) => {
                  const isContact =
                    !isCeoContact && match?.deptKey === dept.key && match?.roleIndex === i;
                  const displayTag: RoleTag = isContact ? 'Champion' : role.roleTag;

                  return (
                    <div key={role.title} className="w-full flex flex-col items-center">
                      {/* Vertical connector between nodes */}
                      {i > 0 && <div className="w-px h-2" style={{ background: 'rgba(245, 240, 232, 0.06)' }} />}

                      <div
                        className={`w-full rounded-lg border p-1.5 text-center transition-all ${
                          isContact
                            ? 'border-2 shadow-md ring-2'
                            : ''
                        }`}
                        style={
                          isContact
                            ? { borderColor: 'var(--accent)', background: 'rgba(212, 165, 116, 0.1)', boxShadow: '0 4px 12px rgba(212, 165, 116, 0.15)', ringColor: 'rgba(212, 165, 116, 0.2)' }
                            : { borderColor: 'var(--border)', background: 'var(--bg-card-solid)' }
                        }
                      >
                        {isContact && (
                          <div className="text-[7px] font-bold uppercase tracking-widest mb-0.5" style={{ color: 'var(--accent)' }}>
                            ★ Entry Point
                          </div>
                        )}

                        {isContact && senderName && (
                          <div className="text-[10px] font-bold leading-tight mb-0.5" style={{ color: 'var(--accent)' }}>
                            {senderName}
                          </div>
                        )}

                        <div
                          className="text-[10px] font-semibold leading-tight"
                          style={{ color: isContact ? 'var(--accent)' : 'var(--text-secondary)' }}
                        >
                          {isContact && senderTitle ? senderTitle : role.title}
                        </div>

                        <div
                          className={`text-[9px] font-medium mt-0.5 ${
                            productColors[role.product] || ''
                          }`}
                          style={productColors[role.product] ? {} : { color: 'var(--text-muted)' }}
                        >
                          {role.product}
                        </div>

                        <span
                          className={`inline-block mt-1 text-[7px] font-bold px-1.5 py-px rounded-full uppercase tracking-wide ${
                            roleTagColors[displayTag]
                          }`}
                        >
                          {displayTag}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-4 pt-3 text-[10px]" style={{ borderTop: '1px solid var(--border)', color: 'var(--text-muted)' }}>
        <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>Roles:</span>
        {Object.entries(roleTagColors).map(([label, cls]) => (
          <span key={label} className="flex items-center gap-1">
            <span className={`inline-block w-2 h-2 rounded-full ${cls.split(' ')[0]}`} />
            {label}
          </span>
        ))}
        <span className="ml-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>Products:</span>
        {Object.entries(productColors).map(([label, cls]) => (
          <span key={label} className={`font-medium ${cls}`}>{label}</span>
        ))}
      </div>
    </div>
  );
}
