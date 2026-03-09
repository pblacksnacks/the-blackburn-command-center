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

  // Determine hierarchy level
  let roleIndex = 3;
  if (/\b(ceo|cto|cfo|cmo|coo|cro|cpo|cco|chro|chief|founder|general counsel)\b/.test(t))
    roleIndex = 0;
  else if (/\b(vp|vice president|svp|evp|head of|head)\b/.test(t))
    roleIndex = 1;
  else if (/\bdirector\b/.test(t))
    roleIndex = 2;

  // Determine department
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

  // C-suite with no clear dept keyword → default to engineering column
  if (roleIndex === 0) return { deptKey: 'engineering', roleIndex: 0 };

  return null;
}

/* ── Style maps ───────────────────────────────────────────────── */

const roleTagColors: Record<string, string> = {
  'Decision Maker': 'bg-red-50 text-red-700',
  Influencer: 'bg-amber-50 text-amber-700',
  Champion: 'bg-blue-50 text-blue-600',
  'End User': 'bg-slate-50 text-slate-500',
};

const productColors: Record<string, string> = {
  Enterprise: 'text-purple-600',
  'Claude Code': 'text-emerald-600',
  'Claude.ai': 'text-blue-600',
  API: 'text-orange-600',
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
    <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5 mb-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          Account Org Power Map
        </h2>
        {(match || isCeoContact) && (
          <span className="text-xs text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full font-semibold">
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
                  ? 'border-2 border-blue-500 bg-blue-50 ring-2 ring-blue-300/40'
                  : 'bg-slate-900 text-white'
              }`}
            >
              {isCeoContact && (
                <div className="text-[8px] font-bold text-blue-600 uppercase tracking-widest mb-0.5">
                  ★ Entry Point
                </div>
              )}
              <div className={`font-bold ${isCeoContact ? 'text-blue-900' : ''}`}>
                {isCeoContact ? senderName || 'CEO' : 'CEO'}
              </div>
              <div className={`text-[10px] mt-0.5 ${isCeoContact ? 'text-blue-600' : 'text-slate-400'}`}>
                {companyName || 'Company'} Leadership
              </div>
            </div>
          </div>

          {/* Vertical connector from CEO */}
          <div className="flex justify-center">
            <div className="w-px h-4 bg-slate-300" />
          </div>

          {/* Horizontal connecting bar */}
          <div className="mx-[6%] border-t-2 border-slate-300" />

          {/* Department columns */}
          <div className="grid grid-cols-8 gap-1.5">
            {departments.map((dept) => (
              <div key={dept.key} className="flex flex-col items-center">
                {/* Vertical drop from horizontal bar */}
                <div className="w-px h-3 bg-slate-300" />

                {/* Department label */}
                <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1.5 text-center leading-tight">
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
                      {i > 0 && <div className="w-px h-2 bg-slate-200" />}

                      <div
                        className={`w-full rounded-lg border p-1.5 text-center transition-all ${
                          isContact
                            ? 'border-blue-500 bg-blue-50 shadow-md shadow-blue-500/10 ring-2 ring-blue-300/40'
                            : 'border-slate-200 bg-white'
                        }`}
                      >
                        {isContact && (
                          <div className="text-[7px] font-bold text-blue-600 uppercase tracking-widest mb-0.5">
                            ★ Entry Point
                          </div>
                        )}

                        {/* Name (only for contact) */}
                        {isContact && senderName && (
                          <div className="text-[10px] font-bold text-blue-900 leading-tight mb-0.5">
                            {senderName}
                          </div>
                        )}

                        {/* Title */}
                        <div
                          className={`text-[10px] font-semibold leading-tight ${
                            isContact ? 'text-blue-700' : 'text-slate-700'
                          }`}
                        >
                          {isContact && senderTitle ? senderTitle : role.title}
                        </div>

                        {/* Product */}
                        <div
                          className={`text-[9px] font-medium mt-0.5 ${
                            productColors[role.product] || 'text-slate-500'
                          }`}
                        >
                          {role.product}
                        </div>

                        {/* Role tag */}
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
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-4 pt-3 border-t border-slate-100 text-[10px] text-slate-500">
        <span className="font-semibold text-slate-600">Roles:</span>
        {Object.entries(roleTagColors).map(([label, cls]) => (
          <span key={label} className="flex items-center gap-1">
            <span className={`inline-block w-2 h-2 rounded-full ${cls.split(' ')[0]}`} />
            {label}
          </span>
        ))}
        <span className="ml-2 font-semibold text-slate-600">Products:</span>
        {Object.entries(productColors).map(([label, cls]) => (
          <span key={label} className={`font-medium ${cls}`}>{label}</span>
        ))}
      </div>
    </div>
  );
}
