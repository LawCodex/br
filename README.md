# LawCodex — Brasil (Brazil)

Brazilian federal legislation as plain Markdown, one file per norm, generated from the
compiled (consolidated) texts published by the Presidency of the Republic on the
**Portal da Legislação do Planalto** (`https://www.planalto.gov.br/ccivil_03/`), maintained by
the Casa Civil — Secretaria Especial para Assuntos Jurídicos.

Part of [LawCodex](https://github.com/LawCodex): the legislation of every country as Markdown in git.

- Jurisdiction: Brazil (`br`), federal level; language: Portuguese (`pt`)
- Source: Planalto — <https://www.planalto.gov.br/ccivil_03/>
- Retrieved: 2026-10-12
- Total: **19,150** files

## Coverage

| Directory | Content | Files | `in_force` | `repealed` | from *texto compilado* |
|---|---|---:|---:|---:|---:|
| `constituicao/` | Constituição Federal de 1988 (texto compilado, all amendments applied) | 1 | 1 | 0 | 1 |
| `emendas-constitucionais/` | Emendas Constitucionais (EC) and Emendas Constitucionais de Revisão (ECR) | 145 | 145 | 0 | 0 |
| `codigos/` | Codes listed in Planalto's *Códigos* table (Civil, Penal, CPC, CPP, CLT, CTN, CDC, ...) | 22 | 21 | 1 | 19 |
| `leis-complementares/` | Leis Complementares, by year | 239 | 219 | 20 | 5 |
| `leis/` | Leis ordinárias, by year | 14,753 | 13,959 | 794 | 253 |
| `leis-delegadas/` | Leis Delegadas | 13 | 8 | 5 | 0 |
| `decretos-lei/` | Decretos-Lei (1937–1946 and 1965–1988), by year | 3,809 | 3,248 | 561 | 24 |
| `medidas-provisorias/` | Medidas Provisórias still pending / in force | 74 | 74 | 0 | 0 |
| `leis-imperio/` | Leis do Império (1808–1889) published by Planalto, by year | 94 | 93 | 1 | 0 |
| **Total** | | **19,150** | **17,768** | **1,382** | **302** |

What each directory holds:

- **`constituicao/`** — the Constitution of 5 October 1988 from Planalto's *texto compilado*
  (`ConstituicaoCompilado.htm`), i.e. with every constitutional amendment applied, including the
  ADCT (Ato das Disposições Constitucionais Transitórias).
- **`emendas-constitucionais/`** — every Emenda Constitucional (`ec-NNN-YYYY.md`) and the six
  Emendas Constitucionais de Revisão of 1994 (`ecr-NNN-1994.md`), as listed in Planalto's
  amendment tables. These are amending acts: their content is already merged into the
  compiled Constitution, but they also contain autonomous (transitional) provisions.
- **`codigos/`** — the acts listed in Planalto's *Códigos* table (Código Civil, Código Penal,
  Código de Processo Civil 2015 and the repealed 1973 code — whose Title IV on insolvency is still
  in force —, Código de Processo Penal, CLT, Código Tributário Nacional, Código de Defesa do
  Consumidor, Código Eleitoral, Código de Trânsito, Código Florestal, Código Penal Militar,
  Código Comercial of 1850, Código de Águas, ECA, ...). File names carry the act that enacted
  the code (`codigo-civil-lei-10406-2002.md`). These acts are **not** repeated in `leis/` or
  `decretos-lei/`.
- **`leis-complementares/<year>/`**, **`leis/<year>/`**, **`decretos-lei/<year>/`** — every
  Lei Complementar, Lei ordinária and Decreto-Lei listed in Planalto's yearly index tables
  (*quadros*), whether in force or repealed (see `status`). Planalto's tables of ordinary laws
  hold a few laws of 1891–1937 and are essentially complete from 1960 on (gaps in 1946–1959, see
  below); the Decretos-Lei tables cover 1937–1946 (a selection) and 1965–1988.
- **`leis-delegadas/`** — the 13 Leis Delegadas (1962 and 1992).
- **`medidas-provisorias/`** — only the provisional measures (MPs) that Planalto's MP tables
  mark as *Em Tramitação*: MPs currently before Congress, and the pre-September-2001 MPs that
  remain in force indefinitely under art. 2 of Constitutional Amendment 32/2001 (e.g. MP
  2.200-2/2001 on ICP-Brasil). Converted, rejected, lapsed (*vigência encerrada*) and revoked MPs
  are not included (when converted, their content is in the conversion law in `leis/`).
  Two corrections to Planalto's table are applied: post-EC 32 MPs labelled *Em Tramitação* but
  older than 240 days (a few 2020 MPs whose table entry was never updated — an MP lapses after at
  most 120 days plus recess) are skipped, and so are MPs whose own page says they were revoked.
- **`leis-imperio/<year>/`** — the Leis do Império that Planalto publishes (its *LIM* table),
  a historical selection: `lim-<number>-<year>.md` for numbered laws, `lim-<date>[-n].md` for
  unnumbered ones (`-2`, `-3` ... when Planalto lists several laws of the same day). The Código
  Comercial (Lei nº 556/1850) is in `codigos/`.

### Compiled text and struck-through wording

Planalto publishes each act on a page that is updated in place: superseded wording is kept on
the page **struck through** (`<strike>`/`<s>`/`<del>`/CSS `line-through`) next to the new wording,
and the amending act is cited in parentheses — e.g. *(Redação dada pela Lei nº 13.146, de 2015)*,
*(Incluído pela ...)*, *(Revogado pela ...)*. For heavily amended acts Planalto also publishes a
separate *texto compilado* page.

For every act the converter uses the *texto compilado* page when the act's page links to one
(front matter `text_version: compiled (texto compilado)`; `source` is the compiled page and
`source_original_page` the act's page), otherwise the act's own page
(`text_version: Planalto page (updated in place)`). In both cases **all struck-through text is
dropped**, so that the Markdown shows only the wording currently in force; the number of
struck-through elements removed is recorded in `struck_through_removed`. When a whole provision is
struck through and only an annotation such as *(Revogado pela Lei nº ...)* remains, the provision
label (e.g. `Art. 7º`, `§ 2º`, `IV -`) is kept in front of the annotation. Planalto's inline
annotations (*Redação dada por*, *Incluído por*, *Vide*, *Vigência*, ...) are preserved as text.

Amending provisions quote the text they insert into other acts; such quoted articles are kept
as plain paragraphs (only the act's own articles become headings).

### Status

`status: repealed` is set when Planalto's page header (between the title and the ementa) carries
a whole-act annotation such as *Revogada pela Lei nº ...*, *Revogado pelo Decreto-Lei ...*,
*Vigência encerrada*, *Rejeitada*, *Sem eficácia*; the annotation is copied to `status_note`.
Otherwise `status: in_force`, which means "no express repeal noted by Planalto" — temporary acts
whose effects are exhausted (budget laws, credit openings, acts naming a road...) are not
detected as such. Planalto's notes are not exhaustive for older acts, so treat `status` as
indicative. For medidas provisórias, `situacao_planalto` copies the status column of Planalto's
MP table.

## Not covered

- **Decretos** (regulatory decrees of the President, tens of thousands since 1889, plus
  *decretos não numerados*), portarias and other infralegal acts — mass-volume secondary
  legislation, skipped.
- Medidas provisórias that were converted, rejected or lapsed (see above).
- Treaties and the *Atos decorrentes do disposto no § 3º do art. 5º* (treaties with
  constitutional rank), *Decretos Legislativos*, *Resoluções* of the Senate/Congress.
- State and municipal legislation.
- Annex images and PDF-only annexes (only the HTML text of each page is converted; tables are
  rendered as Markdown tables, or as minimal HTML when they have merged cells).
- Cross-check against the Senado Federal open-data norm lists (<https://legis.senado.leg.br/dadosabertos/>), by number and year:
  - Leis ordinárias: Senado lists 15,655; 917 are absent from Planalto's index tables and therefore not included (e.g. Lei nº 11 de 28/12/1946; Lei nº 12 de 28/12/1946; Lei nº 10 de 20/12/1946; Lei nº 204 de 31/12/1947; Lei nº 208 de 31/12/1947; Lei nº 203 de 31/12/1947; Lei nº 207 de 31/12/1947; Lei nº 206 de 31/12/1947).
  - Leis complementares: Senado lists 237; 0 are absent from Planalto's index tables and therefore not included.
  - Decretos-Lei: Senado lists 12,378; 6,339 are absent from Planalto's index tables and therefore not included (e.g. Decreto-Lei nº 3.031 de 31/08/1938; Decreto-Lei nº 4.851 de 07/11/1939; Decreto-Lei nº 2.933 de 31/12/1940; Decreto-Lei nº 2.932 de 31/12/1940; Decreto-Lei nº 2.929 de 31/12/1940; Decreto-Lei nº 2.927 de 31/12/1940; Decreto-Lei nº 2.934 de 31/12/1940; Decreto-Lei nº 2.926 de 31/12/1940).
  - Emendas Constitucionais: Senado lists 139; 0 are absent from Planalto's index tables and therefore not included.
  The missing ordinary laws are almost all from 1946–1959 (≈750 of the 1940s, ≈170 of the
  1950s); the missing Decretos-Lei are all from the Estado Novo (1937–1946), of which Planalto
  publishes only a selection. The Senado holds only scanned/original texts for these, so they are
  not included.
- Pages linked from Planalto's tables that return *404 Not Found* (not included): Leis nº 4, 6,
  7, 8 and 9 of 1935–1936 (`leis/1930-1949/L000N.htm`), Lei nº 6.928/1981 and Decreto-Lei
  nº 8.765/1946. The *texto compilado* link of one act is broken; its regular page was used.

## Format

```markdown
---
title: "Lei nº 8.078, de 11 de setembro de 1990"
identifier: "urn:lex:br:federal:lei:1990-09-11;8078"   # LexML URN
type: act            # constitution | constitutional_amendment | code | complementary_law | act |
                     # delegated_law | decree_law | provisional_measure
jurisdiction: br
language: pt
date: 1990-09-11     # signature date
status: in_force     # in_force | repealed (see above)
ementa: "Dispõe sobre a proteção do consumidor e dá outras providências."
source: "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm"
source_original_page: "https://www.planalto.gov.br/ccivil_03/leis/L8078.htm"
text_version: compiled (texto compilado)
struck_through_removed: 2
retrieved: 2026-10-11
---
```

Body: `# title`, the official heading of the act in bold, the ementa in italics, Planalto's
header annotations as a blockquote, then the text. Structural divisions (Parte, Livro, Título,
Capítulo, Seção, Subseção; ADCT/Anexo) become headings from `##` down, articles become the
deepest heading level; when the hierarchy is too deep for Markdown's six levels (e.g. Código
Civil), articles are bold labels (`**Art. 1.228.**`) instead. Paragraphs (§), incisos and
alíneas are plain paragraphs, as on Planalto.

File names: `<prefix>-<number>-<year>.md` with prefixes `ec`, `ecr`, `lcp`, `lei`, `ldl`, `del`,
`mpv` (e.g. `leis/1990/lei-8078-1990.md`, `medidas-provisorias/mpv-2200-2-2001.md`). Where Planalto
lists two different acts under the same number and year, the second gets a `-2` suffix.

## Licence

Brazilian legislative texts are not protected by copyright: Lei nº 9.610/1998 (Lei de Direitos
Autorais), art. 8º, IV, excludes "os textos de tratados ou convenções, leis, decretos,
regulamentos, decisões judiciais e demais atos oficiais" from protection. Planalto's texts are
not the official publication (that is the Diário Oficial da União) — each page notes *"Este texto
não substitui o publicado no DOU"*.

## Regenerating

```sh
pip install -r scripts/requirements.txt
python scripts/enumerate_norms.py   # parse Planalto's index tables -> _raw/br/index.json
python scripts/fetch.py             # download pages (+ texto compilado), cached in _raw/br/cache
python scripts/convert.py           # write the Markdown files
python scripts/crosscheck.py        # optional: compare with the Senado open-data norm lists
python scripts/readme.py            # refresh the counts in this README
```

Raw downloads go to `../_raw/br/` (outside the repository). Planalto's firewall drops requests
whose User-Agent does not look like a browser, so the scripts send
`Mozilla/5.0 (compatible; LawCodex/1.0; +https://github.com/LawCodex)`; at most 4 concurrent
requests. Planalto has no robots.txt.
