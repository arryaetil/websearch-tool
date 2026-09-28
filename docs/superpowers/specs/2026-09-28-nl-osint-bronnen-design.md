# Ontwerp: Nederlandse OSINT-bronnen, identiteitskaart en risk flags

Datum: 2026-09-28 · Status: gebouwd en lokaal getest, nog niet gedeployed

## Doel

KYCX breder laten zoeken (meer bronnen) en tegelijk strenger laten vaststellen of een bron echt over de gezochte persoon gaat. Het OSINT Framework (osintframework.com, data `arf.json`, MIT) dient als inspiratie en catalogus. Het is geen databron: het mist Nederlandse registers en bevat veel bronnen die voor KYC niet proportioneel zijn (dating, people search, telefoon, breach data, dark web). Daarom een eigen, kleine Nederlandse/EU-bronnenlijst.

Blijvende uitgangspunten: een mens beoordeelt altijd; zoekresultaten zijn leads, geen bevindingen; een lege uitkomst is nooit "schoon"; opslag blijft 7 dagen / max 100 runs.

## Bronnen ronde 1 (gratis, geen aanvraag nodig)

| Bron | Rol | Wat naar buiten gaat |
| --- | --- | --- |
| Serper: 3 bestaande zoekopdrachten + 1 officiële-sites-zoekopdracht `"naam" (site:afm.nl OR site:dnb.nl OR site:kvk.nl OR site:rechtspraak.nl)` | Adverse + identiteit | Naam en stad naar Serper (zoals nu) |
| Nationale sanctielijst terrorisme + EU geconsolideerde sanctielijst | Adverse (+ identiteit via geboortedatum) | Niets: dagelijks downloaden, lokaal vergelijken |
| BIG-register-webservice | Identiteit + adverse (doorhaling/beperking) | Naam naar CIBG; alleen als beroep = zorg |
| Wayback Machine availability-API | Bewijs bewaren | Alleen de artikel-URL; **geen** nieuwe snapshots maken |
| Handmatige checklist (links) | Dekking | Niets: analist zoekt zelf |

Checklist-links: Centraal Insolventieregister (insolventies.rechtspraak.nl), KvK bestuursverboden, AFM-registers.

Niet in ronde 1: Insolventieregister-webservice (wacht op toestemming ETIL voor abonnement; voorwaarden: doelbinding "informeren van deelnemers aan het handelsverkeer", vernietigen binnen 6 maanden na einde insolventie, licentie niet overdraagbaar), KvK-API (betaald), OpenSanctions (licentie voor zakelijk gebruik), UBO-register (vergunning/legitiem belang), ICIJ Offshore Leaks (grote download, weinig NL-opbrengst), Rechtspraak-API (personen gepseudonimiseerd).

Geen heridentificatie van gepseudonimiseerde uitspraken, ook niet via bijnamen. Wel toegestaan: zoeken op bedrijfsnaam, en een uitspraak ophalen als een nieuwsbericht er een ECLI-nummer van noemt (later).

## Deel 1 — Graaf

```
                  ┌─► web_search (Serper) ─► fetch ─┐
START ─► intake ──┼─► sanctions (lokaal) ───────────┼─► identity ─► adverse ─► archive ─► assemble ─► END
                  └─► big_register (optioneel) ─────┘
```

- `intake`: normaliseert invoer, kiest takken, bepaalt het hoogst haalbare niveau.
- Takken lopen parallel (LangGraph fan-out) en mogen elk apart falen.
- `identity`: extractie door model, oordeel door vaste regels (deel 2).
- `adverse`: alleen voor bronnen die niet als naamgenoot zijn afgewezen; classificeert type: `allegation`, `charge`, `conviction`, `fine`, `sanction`, `professional_measure`, `none`. Citaten moeten letterlijk in de brontekst staan (zoals nu).
- `archive`: zoekt bestaande Wayback-kopie per getoonde bron.
- `assemble`: rapport, flags, dekking, checklist, en welk extra gegeven de uitkomst zekerder zou maken.

## Deel 2 — Identiteitskaart

**Invoer** (nieuw, optioneel): `birth_year` (jaartal, geen volledige datum) en `profession` (`healthcare`, `lawyer`, `other`, `unknown`). Bestaand: `name`, `city`, `employer`, `context`.

**Extractie.** Het model levert per bron alleen feiten met letterlijk citaat: genoemde naam, leeftijd, woonplaats, werkgever/bedrijf, beroep, publicatiedatum. Het model velt geen identiteitsoordeel meer dat de regels kan overrulen.

**Vergelijking per gegeven:** `match`, `conflict` of `absent`.

- Naam: genormaliseerd (hoofdletters, accenten, tussenvoegsels). Varianten die als volledige naam tellen: "Voornaam Achternaam", "V. Achternaam", "Achternaam, Voornaam". "Voornaam A." / "Jan de V." (gebruikelijk in NL-misdaadnieuws) telt als **gedeeltelijke naam**. Andere voornaam = `conflict`.
- Stad: letterlijk genoemd = `match`; expliciet andere woonplaats van deze persoon = `conflict`.
- Werkgever/bedrijf: genoemd = `match`; expliciet andere werkgever = `conflict`.
- Leeftijd/geboortejaar: `publicatiejaar − leeftijd` binnen ±1 jaar van `birth_year` = `match`, anders `conflict`. Is de publicatiedatum onbekend, dan kan leeftijd geen `conflict` opleveren (alleen `absent`).
- Beroep: bevestigd door invoer of BIG-register = `match`; expliciet ander beroep = `conflict`.

**Regels (in code, niet te overrulen door het model):**

| Niveau | `confidence_score` | Voorwaarde |
| --- | --- | --- |
| Unrelated (naamgenoot) | 0 | Minstens één `conflict` |
| Name only | 1 | Naam (volledig of gedeeltelijk) `match`, verder niets |
| Candidate | 2 | Naam + stad, of naam + sterk gegeven, zonder conflict, maar niet sterk genoeg |
| Strong match | 3 | Geen conflict **en** volledige naam + stad + ≥1 sterk gegeven, **of** gedeeltelijke naam + stad + ≥2 sterke gegevens |

Sterke gegevens: werkgever/bedrijf, leeftijd/geboortejaar, beroepsregistratie. Naam + stad alleen is nooit sterk. De bestaande regel (naam + stad + werkgever) blijft daarmee sterk.

**Sanctielijsten:** geen model. Naam of alias vergeleken met speling voor schrijfwijze (RapidFuzz, alleen kandidaatgeneratie). Geboortedatum op de lijst + `birth_year` ingevuld: gelijk = strong, anders unrelated. Zonder `birth_year`: altijd candidate, met melding "vul geboortejaar in".

**Elke bron telt apart.** Clustering over bronnen heen is later werk.

## Deel 3 — Foutafhandeling en dekking

- Rapport krijgt `coverage`: per bron `searched`, `not_applicable`, `failed` of `manual`, met toelichting en tijdstip.
- Een gefaalde tak geeft een coverage-flag, nooit "geen treffers".
- Sanctielijst ouder dan 2 dagen: coverage-flag "verouderd".
- Timeouts per tak; de graaf rondt altijd af met een rapport.

## Deel 4 — Risk flags en frontend

**Flag-structuur:** `{code, group, label, reason, source_urls}` met `group` = `act`, `review` of `coverage`.

| Group | Wanneer | Codes (voorbeelden) |
| --- | --- | --- |
| `act` | Adverse bevinding **en** strong match | `sanction_match`, `regulatory_fine`, `professional_measure`, `reported_conviction`, `reported_allegation` |
| `review` | Signaal zonder zekere identiteit | `possible_sanction_match`, `identity_needs_review` |
| `coverage` | Bron niet (volledig) doorzocht | `source_not_searched`, `source_failed`, `sanctions_list_stale` |

Geen totaalscore voor "risico van de persoon". Geen flags → tekst "No flags in the sources searched" plus lijst doorzochte bronnen.

**Frontend** (Engelse UI, bestaande KYCX-stijl, IBC-branding, Ubuntu, bestaande tokens):

- Samenvatting: aantal gekoppelde bevindingen, hoogste identiteitsniveau als woord + meter van 3 segmenten, aantal te beoordelen bronnen.
- Risk flags gegroepeerd Act → Review → Coverage; per regel icoon + label + reden + bronlink; kleur nooit als enige drager.
- Bronpaneel: identiteitskaart met per gegeven ✓ / ✗ / – en citaat, meter met tekst "evidence level, not a probability". "Geen tegenstrijdigheden" krijgt een neutraal icoon.
- Coverage-rij met checklist-links voor handmatige bronnen.
- Oude opgeslagen runs (zonder kaart of flag-groepen) blijven leesbaar met de huidige weergave.
- Werkwijze Impeccable (Operate-modus): craft-floor lezen vóór UI-wijzigingen; na afronding één keer `impeccable detect --json` op de gewijzigde bestanden. `PRODUCT.md` ontbreekt; `impeccable init` later aanbieden, niet blokkerend.

## Testen

- Unit tests met verzonnen personen: naamvarianten, gedeeltelijke naam, leeftijdsberekening (incl. onbekende publicatiedatum), conflict wint altijd, sanctie met juiste/verkeerde geboortedatum, sanctie zonder geboortejaar, gefaalde tak → coverage-flag, oude run zonder nieuwe velden.
- Vergelijking met de huidige graaf op dezelfde verzonnen set: terecht afgewezen naamgenoten, gemiste treffers, looptijd, kosten.
- Frontend: `npm run build` en één visuele controle desktop + mobiel.
- Test met een echt persoon alleen na aparte, expliciete toestemming van de gebruiker.

## Open punten (buiten dit ontwerp)

1. Toestemming ETIL voor Insolventieregister-abonnement.
2. Exacte download-URL's en hergebruiksvoorwaarden van NL- en EU-sanctielijst en BIG-webservice vaststellen bij de bouw.
3. Heeft ETIL (Wwft/vergunning) recht op UBO-toegang?
4. Rechtsgrond en DPIA voor verwerking van geboortejaar en strafrechtelijke gegevens (zie governance-vragen in `OSINT_PLAN.md`).

## Afwijkingen bij de bouw (2026-09-28)

- **Beroep geeft nooit een tegenstrijdigheid**, alleen `match` of `absent`: mensen hebben vaak meerdere rollen, dus een andere functietitel is zwak tegenbewijs.
- **Eén modelaanroep per bron.** Het model levert feiten en claims in één keer; de `adverse`-stap is een vaste regel (claims tellen alleen bij een strong match). Dat houdt de kosten gelijk aan de vorige versie.
- **Naamvergelijking bij sanctielijsten** gebruikt `difflib` uit de standaardbibliotheek in plaats van RapidFuzz, met een voorfilter op gedeelde naamdelen en een verplichte overeenkomst van de eerste voornaam. Geen extra afhankelijkheid, ongeveer 0,1 s per check.
- **Handmatige bronnen staan in het dekkingspaneel, niet als flag**, omdat ze bij elke check gelden en anders ruis worden. Coverage-flags zijn er alleen voor bronnen die faalden of verouderd zijn.
- **Roepnamen** (bijv. Appie voor Albert) tellen als gedeeltelijke naam en nooit als tegenstrijdige voornaam. Zoeken gebeurt ook op bijnamen: een extra Serper-zoekopdracht met ingekorte en roepnaamvormen ("Albert B.", "Appie B.", "Appie Bril") plus de stad, en een optioneel veld "Known as" voor bijnamen die de analist kent. Nieuw claimtype `settlement` (deal met justitie), apart van een veroordeling.
- **Uitzondering blijft:** geen bijnamen gebruiken om door de Rechtspraak weggelakte uitspraken aan een persoon te koppelen.
- **Bronnen geverifieerd:** EU-lijst (XML, token-URL, geen account), NL-terrorismelijst (ODS op rijksoverheid.nl), BIG-webservice `https://api.bigregister.nl/zksrv/soap/4` (SOAP, geen account), Wayback availability-API.
