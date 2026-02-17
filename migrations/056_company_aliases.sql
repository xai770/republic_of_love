-- Migration 056: Company aliases registry for anonymization
-- Purpose: Canonical bilingual company descriptions, verified by privacy auditor
-- Date: 2026-02-17
--
-- Design: When a CV names a company, we look it up here.
-- Hit  → use stored anonymized description (EN + DE).
-- Miss → inline LLM generates temp, Doug researches, verifier approves.
-- Once verified, description is locked. All yogis get the same text
-- for the same company. "What we don't have, we can't leak."

BEGIN;

-- 1. Core table
CREATE TABLE IF NOT EXISTS company_aliases (
    alias_id         SERIAL PRIMARY KEY,
    company_pattern  TEXT NOT NULL,                -- lowercase canonical: "deutsche bank"
    anonymized_en    TEXT NOT NULL,                -- "a large German bank"
    anonymized_de    TEXT NOT NULL,                -- "eine große deutsche Bank"
    industry         TEXT,                         -- "banking", "pharma", "automotive"
    size_hint        TEXT,                         -- "large", "mid-size", "startup"
    country          TEXT,                         -- "DE", "US", "CH", etc.
    verified         BOOLEAN DEFAULT FALSE,        -- verifier actor approved?
    verified_at      TIMESTAMPTZ,
    source           TEXT DEFAULT 'llm_inline',    -- 'llm_inline' | 'doug' | 'manual' | 'seed'
    research_notes   TEXT,                         -- Doug's raw research summary
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Case-insensitive unique on the pattern
CREATE UNIQUE INDEX IF NOT EXISTS idx_company_alias_pattern
    ON company_aliases (LOWER(company_pattern));

-- For lookup during anonymization
CREATE INDEX IF NOT EXISTS idx_company_alias_verified
    ON company_aliases (verified) WHERE verified = TRUE;

COMMENT ON TABLE company_aliases IS
'Canonical anonymized company descriptions for CV anonymization.
Each real company name maps to one EN + one DE description.
Descriptions must satisfy the ≥3-companies rule: at least 3 real companies
could plausibly match the description. Verified by privacy auditor actor.';

COMMENT ON COLUMN company_aliases.company_pattern IS
'Lowercase canonical company name. Variations (e.g. "DB", "Deutsche Bank AG",
"Deutsche Bank Group") should all map to the same row. Use additional patterns
in company_alias_variants for alternate spellings.';

-- 2. Variants table for alternate spellings / abbreviations
CREATE TABLE IF NOT EXISTS company_alias_variants (
    variant_id   SERIAL PRIMARY KEY,
    alias_id     INTEGER NOT NULL REFERENCES company_aliases(alias_id) ON DELETE CASCADE,
    variant      TEXT NOT NULL,                -- lowercase: "db", "deutsche bank ag"
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_company_variant_lower
    ON company_alias_variants (LOWER(variant));

COMMENT ON TABLE company_alias_variants IS
'Alternate spellings and abbreviations that map to the same company_aliases row.
E.g. "db" → "deutsche bank", "dbk" → "deutsche bank", "roche" → "f. hoffmann-la roche"';

-- 3. Seed data — the companies we already know from the anonymizer + PII detector
INSERT INTO company_aliases (company_pattern, anonymized_en, anonymized_de, industry, size_hint, country, verified, verified_at, source)
VALUES
    -- Banks
    ('deutsche bank',       'a large German bank',                          'eine große deutsche Bank',                              'banking',        'large',    'DE', TRUE, NOW(), 'seed'),
    ('commerzbank',         'a major German commercial bank',               'eine große deutsche Geschäftsbank',                     'banking',        'large',    'DE', TRUE, NOW(), 'seed'),
    ('dresdner bank',       'a large German bank (since acquired)',          'eine große deutsche Bank (inzwischen übernommen)',      'banking',        'large',    'DE', TRUE, NOW(), 'seed'),
    ('goldman sachs',       'a major US investment bank',                    'eine große US-Investmentbank',                          'banking',        'large',    'US', TRUE, NOW(), 'seed'),
    ('jp morgan',           'a major US bank',                              'eine große US-Bank',                                    'banking',        'large',    'US', TRUE, NOW(), 'seed'),
    ('morgan stanley',      'a major US investment bank',                    'eine große US-Investmentbank',                          'banking',        'large',    'US', TRUE, NOW(), 'seed'),
    ('credit suisse',       'a major Swiss bank (since acquired)',           'eine große Schweizer Bank (inzwischen übernommen)',     'banking',        'large',    'CH', TRUE, NOW(), 'seed'),
    ('ubs',                 'a major Swiss bank',                           'eine große Schweizer Bank',                             'banking',        'large',    'CH', TRUE, NOW(), 'seed'),

    -- Consulting
    ('mckinsey',            'a top-tier management consulting firm',         'eine führende Managementberatung',                      'consulting',     'large',    'US', TRUE, NOW(), 'seed'),
    ('bcg',                 'a top-tier management consulting firm',         'eine führende Managementberatung',                      'consulting',     'large',    'US', TRUE, NOW(), 'seed'),
    ('bain',                'a top-tier management consulting firm',         'eine führende Managementberatung',                      'consulting',     'large',    'US', TRUE, NOW(), 'seed'),
    ('deloitte',            'a Big Four professional services firm',         'eine der Big-Four-Wirtschaftsprüfungsgesellschaften',   'consulting',     'large',    'US', TRUE, NOW(), 'seed'),
    ('kpmg',                'a Big Four professional services firm',         'eine der Big-Four-Wirtschaftsprüfungsgesellschaften',   'consulting',     'large',    'NL', TRUE, NOW(), 'seed'),
    ('pwc',                 'a Big Four professional services firm',         'eine der Big-Four-Wirtschaftsprüfungsgesellschaften',   'consulting',     'large',    'UK', TRUE, NOW(), 'seed'),
    ('ey',                  'a Big Four professional services firm',         'eine der Big-Four-Wirtschaftsprüfungsgesellschaften',   'consulting',     'large',    'UK', TRUE, NOW(), 'seed'),
    ('accenture',           'a major global consulting firm',                'ein großes globales Beratungsunternehmen',              'consulting',     'large',    'IE', TRUE, NOW(), 'seed'),
    ('capgemini',           'a large European IT consulting firm',           'ein großes europäisches IT-Beratungsunternehmen',       'consulting',     'large',    'FR', TRUE, NOW(), 'seed'),

    -- IT Services
    ('infosys',             'a large Indian IT services company',            'ein großes indisches IT-Dienstleistungsunternehmen',    'it_services',    'large',    'IN', TRUE, NOW(), 'seed'),
    ('tcs',                 'a large Indian IT services company',            'ein großes indisches IT-Dienstleistungsunternehmen',    'it_services',    'large',    'IN', TRUE, NOW(), 'seed'),
    ('wipro',               'a large Indian IT services company',            'ein großes indisches IT-Dienstleistungsunternehmen',    'it_services',    'large',    'IN', TRUE, NOW(), 'seed'),

    -- Tech
    ('sap',                 'a leading enterprise software company',         'ein führendes Unternehmen für Unternehmenssoftware',    'software',       'large',    'DE', TRUE, NOW(), 'seed'),
    ('siemens',             'a large German industrial technology company',  'ein großer deutscher Industrietechnologiekonzern',      'industrial',     'large',    'DE', TRUE, NOW(), 'seed'),

    -- Pharma
    ('novartis',            'one of the top 10 global pharmaceutical companies',  'eines der 10 größten Pharmaunternehmen weltweit',  'pharma',        'large',    'CH', TRUE, NOW(), 'seed'),
    ('roche',               'a leading Swiss pharmaceutical company',              'ein führendes Schweizer Pharmaunternehmen',         'pharma',        'large',    'CH', TRUE, NOW(), 'seed'),
    ('f. hoffmann-la roche','a leading Swiss pharmaceutical company',              'ein führendes Schweizer Pharmaunternehmen',         'pharma',        'large',    'CH', TRUE, NOW(), 'seed'),
    ('pfizer',              'a major global pharmaceutical company',               'ein großes globales Pharmaunternehmen',             'pharma',        'large',    'US', TRUE, NOW(), 'seed'),
    ('merck',               'a major pharmaceutical and chemicals company',        'ein großes Pharma- und Chemieunternehmen',          'pharma',        'large',    'DE', TRUE, NOW(), 'seed'),
    ('bayer',               'a large German pharmaceutical and chemicals company', 'ein großer deutscher Pharma- und Chemiekonzern',    'pharma',        'large',    'DE', TRUE, NOW(), 'seed'),
    ('sanofi',              'a major European pharmaceutical company',             'ein großes europäisches Pharmaunternehmen',          'pharma',        'large',    'FR', TRUE, NOW(), 'seed'),
    ('astrazeneca',         'a major global pharmaceutical company',               'ein großes globales Pharmaunternehmen',              'pharma',        'large',    'UK', TRUE, NOW(), 'seed'),

    -- Automotive
    ('bmw',                 'a premium German automotive manufacturer',             'ein deutscher Premium-Automobilhersteller',          'automotive',    'large',    'DE', TRUE, NOW(), 'seed'),
    ('volkswagen',          'a large German automotive manufacturer',               'ein großer deutscher Automobilhersteller',           'automotive',    'large',    'DE', TRUE, NOW(), 'seed'),
    ('audi',                'a premium German automotive manufacturer',             'ein deutscher Premium-Automobilhersteller',          'automotive',    'large',    'DE', TRUE, NOW(), 'seed'),
    ('porsche',             'a premium German automotive manufacturer',             'ein deutscher Premium-Automobilhersteller',          'automotive',    'large',    'DE', TRUE, NOW(), 'seed'),
    ('daimler',             'a large German automotive manufacturer',               'ein großer deutscher Automobilhersteller',           'automotive',    'large',    'DE', TRUE, NOW(), 'seed'),
    ('mercedes',            'a large German automotive manufacturer',               'ein großer deutscher Automobilhersteller',           'automotive',    'large',    'DE', TRUE, NOW(), 'seed'),

    -- Insurance
    ('allianz',             'a leading European insurance group',                   'eine führende europäische Versicherungsgruppe',       'insurance',     'large',    'DE', TRUE, NOW(), 'seed'),
    ('munich re',           'a major global reinsurance company',                   'ein großer globaler Rückversicherer',                 'insurance',     'large',    'DE', TRUE, NOW(), 'seed'),
    ('zurich insurance',    'a major European insurance group',                     'eine große europäische Versicherungsgruppe',          'insurance',     'large',    'CH', TRUE, NOW(), 'seed'),

    -- Industrial
    ('bosch',               'a large German industrial technology company',         'ein großer deutscher Industrietechnologiekonzern',    'industrial',    'large',    'DE', TRUE, NOW(), 'seed'),
    ('basf',                'a large German chemicals company',                     'ein großer deutscher Chemiekonzern',                  'chemicals',     'large',    'DE', TRUE, NOW(), 'seed'),
    ('henkel',              'a large German consumer goods and chemicals company',  'ein großer deutscher Konsumgüter- und Chemiekonzern', 'chemicals',    'large',    'DE', TRUE, NOW(), 'seed'),

    -- Big Tech
    ('amazon',              'a major global technology company',                    'ein großer globaler Technologiekonzern',               'tech',          'large',    'US', TRUE, NOW(), 'seed'),
    ('google',              'a major global technology company',                    'ein großer globaler Technologiekonzern',               'tech',          'large',    'US', TRUE, NOW(), 'seed'),
    ('microsoft',           'a major global technology company',                    'ein großer globaler Technologiekonzern',               'tech',          'large',    'US', TRUE, NOW(), 'seed'),
    ('apple',               'a major global technology company',                    'ein großer globaler Technologiekonzern',               'tech',          'large',    'US', TRUE, NOW(), 'seed'),
    ('meta',                'a major global technology company',                    'ein großer globaler Technologiekonzern',               'tech',          'large',    'US', TRUE, NOW(), 'seed'),
    ('tesla',               'a major electric vehicle and technology company',      'ein großer Elektrofahrzeug- und Technologiekonzern',   'automotive',   'large',    'US', TRUE, NOW(), 'seed'),

    -- Broadcasting / Transport (from current profile)
    ('zdf',                 'a national public broadcaster',                        'ein öffentlich-rechtlicher Sender',                    'media',         'large',    'DE', TRUE, NOW(), 'seed'),
    ('deutsche bahn',       'a national transportation company',                    'ein nationales Transportunternehmen',                  'transport',     'large',    'DE', TRUE, NOW(), 'seed')

ON CONFLICT DO NOTHING;

-- 4. Seed variants for common abbreviations
INSERT INTO company_alias_variants (alias_id, variant)
SELECT a.alias_id, v.variant
FROM company_aliases a
CROSS JOIN LATERAL (VALUES
    ('deutsche bank',    'db'),
    ('deutsche bank',    'deutsche bank ag'),
    ('deutsche bank',    'deutsche bank group'),
    ('commerzbank',      'coba'),
    ('commerzbank',      'commerzbank ag'),
    ('dresdner bank',    'dresdner bank ag'),
    ('goldman sachs',    'gs'),
    ('goldman sachs',    'goldman sachs & co'),
    ('jp morgan',        'jpmorgan'),
    ('jp morgan',        'j.p. morgan'),
    ('jp morgan',        'jpmorgan chase'),
    ('morgan stanley',   'ms'),
    ('credit suisse',    'cs'),
    ('credit suisse',    'credit suisse group'),
    ('mckinsey',         'mckinsey & company'),
    ('bcg',              'boston consulting group'),
    ('bain',             'bain & company'),
    ('pwc',              'pricewaterhousecoopers'),
    ('ey',               'ernst & young'),
    ('ey',               'ernst and young'),
    ('sap',              'sap se'),
    ('sap',              'sap ag'),
    ('siemens',          'siemens ag'),
    ('novartis',         'novartis ag'),
    ('novartis',         'novartis pharma'),
    ('roche',            'roche holding'),
    ('f. hoffmann-la roche', 'hoffmann-la roche'),
    ('bmw',              'bmw ag'),
    ('bmw',              'bmw group'),
    ('volkswagen',       'vw'),
    ('volkswagen',       'volkswagen ag'),
    ('daimler',          'daimler ag'),
    ('daimler',          'daimler-benz'),
    ('mercedes',         'mercedes-benz'),
    ('mercedes',         'mercedes-benz group'),
    ('allianz',          'allianz se'),
    ('allianz',          'allianz group'),
    ('bosch',            'robert bosch'),
    ('bosch',            'robert bosch gmbh'),
    ('basf',             'basf se'),
    ('google',           'alphabet'),
    ('google',           'alphabet inc'),
    ('meta',             'facebook'),
    ('meta',             'facebook inc'),
    ('tcs',              'tata consultancy services'),
    ('deutsche bahn',    'db ag'),
    ('deutsche bahn',    'db fernverkehr'),
    ('zdf',              'zweites deutsches fernsehen')
) AS v(pattern, variant)
WHERE LOWER(a.company_pattern) = v.pattern
ON CONFLICT DO NOTHING;

COMMIT;
