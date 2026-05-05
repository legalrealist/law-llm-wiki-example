# Log

Append-only record of wiki operations. Each entry header is parseable:
`## [YYYY-MM-DD] <operation> | <title>`

Operations: `ingest`, `query`, `lint`, `update`, `init`.

To get the last 5 entries: `grep "^## \[" wiki/log.md | tail -5`

---

## [2026-04-10] update | wiki.py: link-cases now reports unlinked citations with no page; abbreviation normalization added (US/U.S. → United States, LA, NY, etc.)
Script updated: `find_page()` now expands common abbreviations before fuzzy matching; missing citations surfaced in report rather than silently dropped.

## [2026-04-10] update | Mass case page creation — ~250 new pages across all courses
Created missing pages for Criminal Investigations (4th/5th/6th Amendment), Criminal Law, Criminal Adjudications, Federal Courts, Constitutional Law, Contracts II, Corporations, Torts, Evidence, Property, Legislation, Professional Responsibility, Transnational Litigation, Administrative Law, Conflict of Laws, Antitrust, Civil Procedure.
link-cases: 383 links added; link-shorthands: 20 additional links; lint: 0 broken links.
Remaining unlinked (63): mix of regex noise, acronym shorthands (GM, DLJ, VW, HLP, NCR), and ~20 genuinely obscure cases — see tools/reports/link-cases-20260410-123011.md.

## [2026-04-10] update | Batch case pages — Transnational Litigation (37), Administrative Law (8), Conflict of Laws (15)
Pages created (Transnational Litigation): [[Alfred Dunhill of London, Inc. v. Republic of Cuba]], [[Argentina v. Weltover, Inc.]], [[Bachchan v. India Abroad Publications Inc.]], [[Banco Nacional de Cuba v. Sabbatino]], [[Carolina Power & Light Co. v. Uranex]], [[Cicippio-Puleo v. Islamic Republic of Iran]], [[De Letelier v. Republic of Chile]], [[De Melo v. Lederle Laboratories]], [[Dole Food Co. v. Patrickson]], [[Evans Cabinet Corp. v. Kitchen International]], [[Gasser GmbH v. MISAT Srl]], [[Hodgson v. Bowerbank]], [[Intel Corp. v. Advanced Micro Devices]], [[IntraComm v. Bajaj]], [[Johnston v. Compagnie Generale Transatlantique]], [[Kadic v. Karadzic]], [[Mitsubishi Motors Corp. v. Soler Chrysler-Plymouth]], [[Mohamad v. Palestinian Authority]], [[Morrison v. National Australia Bank Ltd.]], [[Nedlloyd Lines B.V. v. Superior Court]], [[Owusu v. Jackson]], [[Prewitt Enterprises v. OPEC]], [[Republic of Philippines v. Marcos]], [[Richards v. Lloyd's of London]], [[Sadat v. Mertes]], [[Samantar v. Yousuf]], [[Saudi Arabia v. Nelson]], [[Society of Lloyd's v. Ashenden]], [[Somportex Ltd. v. Philadelphia Chewing Gum Corp.]], [[Telnikoff v. Matusevitch]], [[Turner v. Grovit]], [[Underhill v. Hernandez]], [[Vagenas v. Continental Gin Co.]], [[Van Dusen v. Barrack]], [[W.S. Kirkpatrick & Co. v. Environmental Tectonics Corp.]], [[International Ass'n of Machinists v. OPEC]]
Pages created (Administrative Law): [[American Mining Congress v. EPA]], [[CFTC v. Schor]], [[Christopher v. SmithKline Beecham Corp.]], [[Dunlop v. Bachowski]], [[FTC v. Standard Oil Co. of California]], [[McCarthy v. Madigan]], [[Murray's Lessee v. Hoboken Land & Improvement Co.]], [[Northern Pipeline Construction Co. v. Marathon Pipe Line Co.]], [[PBGC v. LTV Corp.]]
Pages created (Conflict of Laws): [[AT&T Mobility LLC v. Concepcion]], [[Baker v. General Motors Corp.]], [[Bernkrant v. Fowler]], [[Clarke v. Clarke]], [[Durfee v. Duke]], [[Fall v. Eastin]], [[Grant v. McAuliffe]], [[Huntington v. Attrill]], [[Kenney v. Supreme Lodge]], [[Levy v. Daniels' U-Drive Auto Renting Co.]], [[Milwaukee County v. M.E. White Co.]], [[Moore v. Mitchell]], [[Sampson v. Channell]], [[Treinies v. Sunshine Mining Co.]], [[Worthley v. Worthley]]
Skipped (insufficient certainty): Antonier v. Miller, Benjamin v. British European Airways, Valois of America v. Risdon Corp.
Index updated with all 60 new case entries.

## [2026-04-10] update | Batch case pages — Torts (19), Evidence (10), Property (11), Legislation (4), Professional Responsibility (7)
Pages created (Torts): [[BMW of North America, Inc. v. Gore]], [[Carter v. Kinney]], [[Christensen v. Swenson]], [[Doe v. Manheimer]], [[Dreisonstok v. Volkswagenwerk A.G.]], [[Elmore v. American Motors Corp.]], [[Estancias Dallas Corp. v. Schultz]], [[Gala v. Hamilton]], [[Hanks v. Powder Ridge Restaurant Corp.]], [[Mathias v. Accor Economy Lodging]], [[Perez v. Wyeth Laboratories]], [[Posecai v. Wal-Mart Stores]], [[Randi W. v. Muroc Joint Unified School District]], [[Rowland v. Christian]], [[Seffert v. Los Angeles Transit Lines]], [[Simonsen v. Thorin]], [[State Farm Mutual Automobile Insurance Co. v. Campbell]], [[Trimarco v. Klein]], [[Wishnatsky v. Huey]]
Pages created (Evidence): [[Ballou v. Henri Studios Inc.]], [[General Electric Co. v. Joiner]], [[Luce v. United States]], [[Palmer v. Hoffman]], [[Seiler v. Lucasfilm, Ltd.]], [[Specht v. Jensen]], [[Tanner v. United States]], [[United States v. Duffy]], [[United States v. Webster]], [[Weisgram v. Marley Co.]]
Pages created (Property): [[Association for Molecular Pathology v. Myriad Genetics]], [[Cayuga Indian Nation v. Pataki]], [[Diamond v. Chakrabarty]], [[Eyerman v. Mercantile Trust Co.]], [[Hadacheck v. Sebastian]], [[Hawkins v. Mahoney]], [[Pile v. Pedrick]], [[Pocono Springs Civic Ass'n v. MacKenzie]], [[Riddle v. Harmon]], [[Tahoe-Sierra Preservation Council v. Tahoe Regional Planning Agency]], [[Virtual Works, Inc. v. Volkswagen of America]]
Pages created (Legislation): [[Gen. Dynamics Land Systems v. Cline]], [[Lamie v. United States Trustee]], [[Medtronic, Inc. v. Lohr]], [[Perez v. Campbell]]
Pages created (Professional Responsibility): [[Garner v. Wolfenbarger]], [[Meyerhoffer v. Empire Fire & Marine Insurance]], [[N.Y. County Lawyers Ass'n v. Dacey]], [[People v. Fentress]], [[Purcell v. District Attorney]], [[State Bar of Arizona v. Arizona Land Title & Trust Co.]], [[Visa USA Inc. v. First Data Corp.]]
Skipped (insufficient certainty or wrong course): Arpin v. United States, Jones v. State, Levin v. United States, People v. Harris, United States v. Gonzalez, Hatch v. Amoskeag, Nicks v. Heddon, Reves v. Ernst & Young, AMP Inc. (merged into correct name)
Index updated with all 51 new case entries.

## [2026-04-10] update | Batch case pages — Contracts II (37 cases) + Corporations (14 cases)
Pages created (Contracts II): [[Alaniz v. Schal Associates]], [[Canadian Industrial Alcohol Co. v. Dunbar Molasses Co.]], [[Caspi v. Microsoft Network]], [[City of Midland v. O'Bryant]], [[ConEdison v. Arroll]], [[Crane Ice Cream Co. v. Terminal Freezing & Heating Co.]], [[Donovan v. RRL Corp.]], [[Dwyer v. Jung]], [[Flowers v. Diamond Shamrock Corp.]], [[Fortune v. National Cash Register]], [[Gibson v. Cranage]], [[H.R. Moch Co. v. Rensselaer Water Co.]], [[Haines v. City of New York]], [[Jackson v. Seymour]], [[JNA Realty Corp. v. Cross Bay Chelsea]], [[Jones v. Star Credit Corp.]], [[K&G Construction Co. v. Harris]], [[Karpinski v. Ingrasci]], [[Lenawee County Board of Health v. Messerly]], [[Lloyd v. Murphy]], [[Macke Co. v. Pizza of Gaithersburg]], [[Mineral Park Land Co. v. Howard]], [[Mitchill v. Lath]], [[OW Grun Roofing & Construction Co. v. Cope]], [[PG&E v. G.W. Thomas Drayage & Rigging Co.]], [[Plante v. Jacobs]], [[Raffles v. Wichelhaus]], [[Rouse v. United States]], [[Schwartzreich v. Baum-Basch]], [[Seaver v. Ransom]], [[Southwest Engineering Co. v. Martin Tractor Co.]], [[Specht v. Netscape Communications Corp.]], [[Stewart v. Newbury]], [[Tymshare v. Covell]], [[Wood v. Boynton]]
Pages created (Corporations): [[Adams v. Jarvis]], [[Cooke v. Oolie]], [[Fletcher v. A.J. Industries]], [[Gallant Insurance Co. v. Isaac]], [[Hariton v. Arco Electronics]], [[Hoover v. Sun Oil Co.]], [[Humble Oil & Refining Co. v. Martin]], [[Jenson Farms Co. v. Cargill, Inc.]], [[Kamin v. American Express Co.]], [[Page v. Page]], [[Papas v. Tzolis]], [[Siegel v. Buntrock]], [[Tooley v. Donaldson, Lufkin & Jenrette]], [[Vohland v. Sweet]]
Skipped (insufficient certainty): Greghuhn v. Omaha Insurance, Holiday Inn v. Knight, Magnet Resources Inc. v. Summit, Morestain v. Kircher, Ryan v. Weiner, S.P. Dunham & Co. v. Kudra, Triple A Contractors v. Rural Waters, White v. Thomas
Index updated with all 49 new case entries.

## [2026-04-10] update | New antitrust case pages + Antitrust.md submarket links
Pages created: [[FTC v. Whole Foods Market, Inc.]], [[Eastman Kodak Co. v. Image Technical Services, Inc.]]
Antitrust.md line 95: replaced (Vail), (Whole Foods), (Staples), (Kodak) shorthands with explicit wikilinks. Index updated.

## [2026-04-08] update | Stub doctrine pages (batch of 20)
Pages created: [[Presumption Against Extraterritoriality]], [[Presumption Against Retroactivity]], [[Anti-Contact Rule (MR 4.2)]], [[Conflict of Interest (MR 1.7)]], [[Successive Conflicts (MR 1.9)]], [[Imputed Disqualification (MR 1.10)]], [[Duty of Confidentiality (MR 1.6)]], [[Unauthorized Practice of Law]], [[Work-Product Doctrine]], [[Fee Simple Absolute]], [[Nuisance]], [[Recording Acts]], [[Easement by Implication]], [[Free Writing Prospectus (FWP)]], [[Private Placement Exemption (§4(2))]], [[Regulation D (Rules 504, 505, 506)]], [[Shelf Registration]], [[WKSI]], [[Complete Diversity Requirement]], [[Limited Appearance (QIR#2)]]
Index updated: all 20 pages added to Doctrines table in alphabetical order.

## [2026-04-06] init | Wiki initialized
Directory structure created. CLAUDE.md schema written. Starter pages (index, log, overview) created. Ready for first ingest.

## [2026-04-06] update | Reconfigured for law school notes
Switched wiki from LLM/AI research domain to law school notes. Updated CLAUDE.md schema, restructured wiki subdirectories (replaced models/concepts/labs/papers/benchmarks with courses/doctrines/cases/statutes). All 25 .docx source files extracted to raw/extracted/.

## [2026-04-06] ingest | All law school notes (26 files)
Pages created: 23 course pages, 63 doctrine pages, 5 case pages.
Sources ingested: Contracts I & II, Torts, Constitutional Law, Legislation, Property, Criminal Law, Criminal Adjudications, Criminal Inv Analysis, Criminal Investigations, Civil Procedure I & II, Evidence (2013 + Capra F14), Administrative Law, Professional Responsibility, Antitrust, Corporations, Securities Regulation, Conflict of Laws, Federal Courts, Federal Criminal Law, Federal Criminal Law (Richman), Transnational Litigation.
Note: Case pages incomplete — only 5 created (Federal Criminal Law subjects). Remaining case pages pending.

## [2026-04-06] update | Added full U.S.C. citations to all statute names
Renamed 12 statute pages to include full statutory citations in filename and H1 title. Updated all wikilinks across the wiki to match. Statutes updated: RICO (§§ 1961–1968), Sherman Act (§§ 1–2), Clayton Act Section 7 (§ 18), Mail Fraud and Wire Fraud (§§ 1341, 1343), Hobbs Act (§ 1951), Federal Conspiracy Statute (§ 371), Alien Tort Statute (§ 1350), FSIA (§§ 1602–1611), Speedy Trial Act (§§ 3161–3174), Securities Act of 1933 (§§ 77a–77aa), Securities Exchange Act of 1934 (§§ 78a–78pp), APA (§§ 551–706). Non-U.S.C. instruments (UCC, MPC, MRPC, FRCP, FRE) left unchanged.

## [2026-04-06] update | Merged Federal Criminal Law courses
Combined [[Federal Criminal Law]] (Spring 2018) and Federal Criminal Law (Richman) casebook notes into a single page. Merged topics (jurisdiction/institutional design, mail/wire fraud, official corruption, RICO, conspiracy, money laundering, civil rights crimes, material support, drug offenses), key cases (17 total), and exam checklists. Deleted Federal Criminal Law (Richman).md. Index updated.

## [2026-04-06] update | Merged Criminal Investigations courses
Combined [[Criminal Investigations]] and [[Criminal Investigations]] into a single page. Merged topics, exam checklists (4th/5th/6th Amendment + entrapment), key cases, and key doctrines. Deleted Criminal Investigations Analysis.md. Index updated.

## [2026-04-06] update | Fixed backlinks — renamed all wiki files to Title Case
Root cause: all ~300 wiki files used kebab-case filenames (e.g. consideration.md) while wikilinks used Title Case (e.g. [[Consideration]]), so every link opened a new blank page instead of navigating to the existing one. Fix: renamed all files so filename = H1 title = wikilink target. Also deleted 6 empty stub files (INS v. Chadha, Skilling, United States v. Binday/Jones/Takhalov, Defeasible Fees) and rewrote them with full content. CLAUDE.md filename convention updated to Title Case.

## [2026-04-06] update | Statutes section created (18 pages)
Created all statute pages from scratch. Pages written: [[Administrative Procedure Act (APA) (5 U.S.C. §§ 551–706)]], [[Sherman Act (15 U.S.C. §§ 1–2)]], [[Clayton Act § 7 — Mergers (15 U.S.C. § 18)]], [[Securities Act of 1933 (15 U.S.C. §§ 77a–77aa)]], [[Securities Exchange Act of 1934 (15 U.S.C. §§ 78a–78pp)]], [[Model Penal Code (MPC)]], [[Mail Fraud and Wire Fraud (18 U.S.C. §§ 1341, 1343)]], [[Hobbs Act (18 U.S.C. § 1951)]], [[RICO (18 U.S.C. §§ 1961–1968)]], [[Federal Conspiracy Statute (18 U.S.C. § 371)]], [[42 U.S.C. § 1983]], [[Foreign Sovereign Immunities Act (FSIA) (28 U.S.C. §§ 1602–1611)]], [[Federal Rules of Civil Procedure (FRCP)]], [[Federal Rules of Evidence (FRE)]], [[UCC Article 2]], [[Model Rules of Professional Conduct (MRPC)]], [[Alien Tort Statute (ATS) (28 U.S.C. § 1350)]], [[Speedy Trial Act (18 U.S.C. §§ 3161–3174)]]. Index updated with Statutes section.

## [2026-04-06] update | Empty doctrine pages filled
Wrote full content for 2 previously empty doctrine pages: [[Regulatory Takings]] (Penn Central balancing, per se takings, Loretto, Lucas, Nollan/Dolan exactions, 10 key cases) and [[Securities Act Section 5 Registration]] (§ 5 prohibition, three periods, Reg D/506, Rule 144A, Reg A+, § 4(a)(2), Rule 144 resale restrictions, 5 key cases). All 63 doctrine pages now have substantive content.

## [2026-04-06] update | Case pages completed
Created 192 additional case pages (197 total) across all subjects. Pages written from legal knowledge covering: Contracts (18), Torts/Property (20), ConLaw/Legislation (22), Criminal Law/Adjudications/Investigations (26), Civil Procedure/Evidence (27), Admin Law/Prof Resp (20), Antitrust/Corporations/Securities (26), Conflicts/Federal Courts/Fed Crim/Transnational (33). Index updated with all 197 case entries.

## [2026-04-07] lint | Broken wikilinks — full lint pass
Starting broken link count: 159 → 0. Operations performed:
- Fixed 11 doctrine pages missing required sections (Elements, Policy): Character Evidence, Covenants Running with the Land, Defeasible Fees, Easements, Equitable Servitudes, Future Interests, Habit and Routine Practice, Hearsay, Proximate Cause, Relevance, Rule Against Perpetuities
- Created 15 new doctrine pages: [[Business Judgment Rule]], [[Duty of Care (Corporations)]], [[Duty of Loyalty (Corporations)]], [[Entire Fairness Test]], [[Unocal Enhanced Scrutiny]], [[Revlon Mode]], [[Shareholder Derivative Suit]], [[Corporate Opportunity Doctrine]], [[Piercing the Corporate Veil]], [[Strict Scrutiny]], [[Intermediate Scrutiny]], [[Collateral Estoppel]] (redirect), [[Res Judicata]] (redirect), [[Duty of Care]] (disambiguation), [[Duty of Loyalty]] (redirect)
- Created ~165 new case pages spanning all subjects (4th/5th Amendment, Admin Law, Antitrust, Conflict of Laws, Contracts, Corporations, Criminal Law/Adjudications/Investigations, Evidence, Federal Criminal Law, Professional Responsibility, Property, Securities, Torts, Civil Procedure)
- Fixed systemic trailing-period mismatch: 9 case filenames ending in punctuation (e.g. `Corp.md`) were causing wikilinks with trailing periods (e.g. `[[SomeCorp.]]`) to fail. Fixed by stripping trailing periods from those 9 wikilinks across all wiki files
- Updated index.md: added 48 new doctrine entries and 134 new case entries (all pages now indexed)
Final broken link count: 0

## [2026-04-07] update | overview.md filled
Wrote full content for [[overview]] (~4,700 words). Sections: Subjects Covered (table of all 21 courses with core questions), Cross-Cutting Themes (10 themes: standards of review, intent/mental state, reasonable person, causation, balancing tests, preclusion, federalism, procedure/rights, fiduciary duties, materiality), Exam Approaches (detailed issue-spotting checklists for Torts, Contracts, Criminal Law, Criminal Investigations, Administrative Law, Corporations, Conflict of Laws, Securities/Federal Criminal fraud), Open Questions (7 unresolved or contested doctrinal areas including post-Loper Bright admin law, Carpenter digital Fourth Amendment, MFW protocol, Skilling/honest services). Zero broken wikilinks.

## [2026-04-08] update | Expanded all 21 course pages to comprehensive study documents
All 21 course pages expanded from thin summaries (~4–8 KB) to full study documents (~15–23 KB each). Pages written directly from source .txt files in raw/extracted/. Pages expanded in this session:
- [[Criminal Adjudications]]: prosecutorial discretion, grand jury, right to counsel, bail, speedy trial (Barker four-factor), Brady/discovery, guilty pleas (Alford plea, FRCP 11 colloquy), plea bargaining, sentencing
- [[Professional Responsibility]]: regulatory framework (inherent power doctrine, Keller, NC Dental), ACP (Wigmore 8 elements, crime-fraud exception, waiver), work-product doctrine, MR 1.6 confidentiality, complicity in client illegality, conflicts of interest (MR 1.7/1.9/1.10), organizational clients (Upjohn), anti-contact rule (MR 4.2)
- [[Legislation]]: statutory interpretation theories (intentionalism/purposivism/textualism/dynamic), Merrill's four-level canon hierarchy, linguistic canons, normative canons, Chevron/Mead/Brand X, preemption, in pari materia
- [[Property]]: theories of property, acquisition, adverse possession, estates in land, landlord-tenant, transfers/recording acts, easements, covenants, nuisance/zoning, takings (Penn Central/Lucas/Loretto/Kelo)
- [[Securities Regulation]]: §5 registration (three periods), FWP/WKSI/shelf registration, Howey investment contract test, §4(2) private placement, Regulation D (Rules 504/505/506), MD&A
- [[Constitutional Law]]: judicial review, justiciability, Commerce Clause (Lopez three categories), taxing/spending, commandeering (Printz), DCC, Youngstown tripartite, equal protection (race/sex/animus), substantive DP (Lochner), incorporation, First/Second Amendment
- [[Civil Procedure II]]: SMJ (§1331 federal question, §1332 diversity), supplemental jurisdiction (§1367), Pennoyer TJ framework, International Shoe minimum contacts, general/specific jurisdiction (Goodyear/Daimler/McGee), notice (Mullane), removal tactics

## [2026-04-09] update | Case pages pass 2 — unlinked v. patterns

**New case pages created (84):**
Constitutional Law (17): [[Wickard v. Filburn]], [[Craig v. Boren]], [[United States v. Morrison]], [[New York Times Co. v. Sullivan]], [[Texas v. Johnson]], [[Baker v. Carr]], [[Reynolds v. Sims]], [[Yick Wo v. Hopkins]], [[McDonald v. City of Chicago]], [[Lemon v. Kurtzman]], [[Cooper v. Aaron]], [[Gibbons v. Ogden]], [[Bolling v. Sharpe]], [[Garcia v. San Antonio Metropolitan Transit Authority]], [[Missouri v. Holland]], [[United States v. Virginia]], [[Romer v. Evans]]
Admin Law (14): [[Norton v. SUWA]], [[Bennett v. Spear]], [[Friends of the Earth v. Laidlaw Environmental Services]], [[Universal Camera Corp. v. NLRB]], [[Darby v. Cisneros]], [[Crowell v. Benson]], [[Stern v. Marshall]], [[Clinton v. City of New York]], [[ICC v. Locomotive Engineers]], [[Johnson v. Robison]], [[Block v. Community Nutrition Institute]], [[Webster v. Doe]], [[Lincoln v. Vigil]], [[NLRB v. Bell Aerospace Co.]]
Federal Courts (7): [[Swift v. Tyson]], [[Younger v. Harris]], [[Burford v. Sun Oil Co.]], [[Railroad Commission of Texas v. Pullman Co.]], [[Skelly Oil Co. v. Phillips Petroleum Co.]], [[Boyle v. United Technologies Corp.]], [[United Mine Workers of America v. Gibbs]]
Corporations (9): [[Stone v. Ritter]], [[Francis v. United Jersey Bank]], [[Joy v. North]], [[Graham v. Allis-Chalmers Manufacturing Co.]], [[Blasius Industries v. Atlas Corp.]], [[Katz v. Bregman]], [[Auerbach v. Bennett]], [[Tarnowski v. Resop]], [[National Biscuit Co. v. Stroud]]
Property (5): [[Ghen v. Rich]], [[Keeble v. Hickeringill]], [[Morgan v. High Penn Oil Co.]], [[Holbrook v. Taylor]], [[Othen v. Rosier]]
Torts (6): [[Hymowitz v. Eli Lilly and Co.]], [[Davies v. Mann]], [[Farwell v. Keaton]], [[Thing v. La Chusa]], [[Dillon v. Legg]], [[Bethel v. New York City Transit Authority]]
Criminal Adjudications (7): [[Powell v. Alabama]], [[Betts v. Brady]], [[Hurtado v. California]], [[Williams v. Florida]], [[Brady v. United States]], [[Johnson v. Zerbst]], [[Tollett v. Henderson]]
Criminal Law (5): [[Kennedy v. Louisiana]], [[People v. Marrero]], [[Graham v. Connor]], [[Scott v. Harris]], [[State v. Tally]]
Conflict of Laws (5): [[Harris v. Balk]], [[Fauntleroy v. Lum]], [[Home Insurance Co. v. Dick]], [[Testa v. Katt]], [[Michigan v. Long]]
Legislation (5): [[Wyeth v. Levine]], [[Geier v. American Honda Motor Co.]], [[EEOC v. Arabian American Oil Co. (Aramco)]], [[Smith v. City of Jackson]], [[Wachovia Bank v. Schmidt]]
Evidence (5): [[Michelson v. United States]], [[United States v. Abel]], [[United States v. Mezzanatto]], [[Mutual Life Insurance Co. v. Hillmon]], [[Shepard v. United States]]

**Wikilinks added:** +106 wikilinks across 13 course pages connecting prose mentions to new case pages.
**Index updated:** 145 new entries added to Cases section.

## [2026-04-09] update | Doctrine wikilinks pass + broken link fixes

**Broken wikilinks fixed (8):** Trailing-period mismatch on Co./Corp. filenames in Corporations, Federal Courts, Property, Torts.

**Doctrine wikilinks added (+254):** Linked all unlinked doctrine mentions across all 21 course pages.
Key doctrines linked: [[Chevron Deference]], [[Auer Deference]], [[Skidmore Deference]], [[Erie Doctrine]], [[Non-Delegation Doctrine]], [[Commerce Clause]], [[Equal Protection]], [[Strict Scrutiny]], [[Substantive Due Process]], [[Negligence]], [[Strict Liability]], [[Products Liability]], [[Mens Rea]], [[Actus Reus]], [[Hearsay]], [[Character Evidence]], [[Warrant Requirement]], [[Exclusionary Rule]], [[Fruit of the Poisonous Tree]], [[Probable Cause]], [[Accomplice Liability]], [[Felony Murder]], [[Consideration]], [[Promissory Estoppel]], [[Statute of Frauds]], [[Parol Evidence Rule]], [[Business Judgment Rule]], [[Duty of Loyalty]], [[Revlon Mode]], [[Unocal Enhanced Scrutiny]], [[Adverse Possession]], [[Regulatory Takings]], [[Nuisance]], [[Future Interests]], [[Rule Against Perpetuities]], [[Forum Non Conveniens]], [[Full Faith and Credit]], [[Governmental Interest Analysis]], [[Renvoi]], [[Depecage]], [[Act of State Doctrine]], [[Presumption Against Extraterritoriality]], [[Textualism]], [[Legislative History]], [[Canons of Construction]], [[Mail Fraud]], [[Wire Fraud]], and many more.

**Result:** 0 broken wikilinks across all course pages.
## [2026-04-11] update | Created ~50 missing case stubs and applied links
Pages added: [[Brentwood Academy v. Tennessee Secondary School Athletic Assoc]], [[Burton v. Wilmington Parking Authority]], [[Jackson v. Metropolitan Edison Co]], [[NCAA v. Tarkanian]], [[Terry v. Adams]], [[Foley v. Connelie]], [[Mississippi University for Women v. Hogan]], [[Nguyen v. INS]], [[Rostker v. Goldberg]], [[Clark v. Arizona]], [[Montana v. Engelhoff]], [[People v. Ireland]], [[People v. Washington]], [[People v. Lauria]], [[State v. Reeves]], [[United States v. Jackson]], [[Duro v. Reina]], [[Jones v. United States]], [[Republic of Argentina v. Weltover]], [[Letelier v. Republic of Chile]], [[Hardesty v. Smith]], [[Mitchell v. Lath]], [[Pacific Gas & Electric Co. v. G.W. Thomas Drayage]], [[Post v. Jones]], [[Bloomgarden v. Coyer]], [[Massman Construction Co. v. City Council of Greenville]], [[Schiavi Mobile Homes v. Gironda]], [[Matthews v. Bay Head Improvement Ass'n]], [[Hughes v. Alexandria Scrap Corp]], [[Nix v. Hedden]], [[United States v. Maze]], [[Erickson v. Pardus]], [[Bradley v. School Board of Richmond]], [[United States v. Bass]], [[United States v. R.L.C]], [[INS v. Lopez-Mendoza]], [[Beam v. Stewart]], [[T.C. Theatre Corp. v. Warner Bros. Pictures]], [[Knight v. Jewett]], [[Levin v. United States]], [[People v. Hernandez]]
Operations: link-cases (48 links added across 30 files), update-index (124 entries added), lint = 0

