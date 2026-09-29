import unittest
import zipfile
from io import BytesIO

import big_register
import sanctions
from identity_rules import compare_age, compare_city, compare_employer, compare_name, decide_tier, search_aliases, split_name


def card(**statuses):
    base = {key: {"status": "absent"} for key in ("name", "city", "employer", "age", "profession")}
    base.update({key: {"status": value} for key, value in statuses.items()})
    return base


class NameTests(unittest.TestCase):
    def test_dutch_prefix_is_split(self):
        self.assertEqual(split_name("Jan de Vries"), (["jan"], "de", "vries"))
        self.assertEqual(split_name("Anna Maria van der Berg"), (["anna", "maria"], "van der", "berg"))

    def test_written_variants(self):
        for text in ("Albert Bril", "A. Bril", "Bril, Albert", "ALBERT BRIL (54)", "Albért Bril"):
            self.assertEqual(compare_name("Albert Bril", None, text), "full", text)
        self.assertEqual(compare_name("Jan de Vries", None, "Jan de V. (54) uit Zwolle"), "partial")
        self.assertEqual(compare_name("Albert Bril", None, "Albert Brill"), "absent")

    def test_roepnaam_is_a_partial_name_not_a_conflict(self):
        self.assertEqual(compare_name("Albert Bril", "Appie B.", "Makelaar Appie B. uit Bergentheim"), "partial")
        self.assertEqual(compare_name("Albert Bril", "Appie Bril", "Appie Bril uit Bergentheim"), "partial")
        self.assertEqual(compare_name("Appie Bril", None, "Albert Bril sprak"), "partial")
        self.assertEqual(compare_name("Albert Bril", None, "Appie de Groot"), "absent")

    def test_supplied_alias_is_a_partial_name(self):
        self.assertEqual(compare_name("Albert Bril", "Bertus Bril", "Bertus Bril", ["bertus"]), "partial")
        self.assertEqual(compare_name("Albert Bril", "Bertus Bril", "Bertus Bril"), "conflict")

    def test_search_forms_cover_shortened_names_and_nicknames(self):
        forms = search_aliases("Albert Bril", [])
        self.assertIn("Albert B.", forms)
        self.assertIn("Appie B.", forms)
        self.assertIn("Appie Bril", forms)
        self.assertLessEqual(len(forms), 6)

    def test_other_first_name_conflicts(self):
        self.assertEqual(compare_name("Albert Bril", "Peter Bril", "Peter Bril sprak"), "conflict")

    def test_nickname_and_middle_initial_do_not_conflict(self):
        self.assertEqual(compare_name("Bernard Madoff", "Bernie Madoff", "Bernie Madoff lived in New York"), "partial")
        self.assertEqual(compare_name("Bernard Madoff", "Bernard L. Madoff", "Bernard L. Madoff"), "full")
        self.assertEqual(compare_name("Bernard Madoff", "Bernard Lawrence (Bernie) Madoff",
                                      "Bernard Lawrence (Bernie) Madoff"), "full")


class RuleTests(unittest.TestCase):
    def test_age_uses_publication_year_with_one_year_margin(self):
        self.assertEqual(compare_age(1972, 54, 2026)[0], "match")
        self.assertEqual(compare_age(1972, 53, 2026)[0], "match")
        self.assertEqual(compare_age(1972, 31, 2026)[0], "conflict")
        self.assertEqual(compare_age(1972, 54, None)[0], "absent")
        self.assertEqual(compare_age(None, 54, 2026)[0], "absent")

    def test_city_conflict_only_when_stated(self):
        self.assertEqual(compare_city("Zwolle", "Groningen", ""), "conflict")
        self.assertEqual(compare_city("Zwolle", None, "Een man uit Zwolle"), "match")

    def test_employer_abbreviation_must_be_linked_in_source(self):
        self.assertEqual(compare_employer("SP", "Socialistische Partij",
                                          "Namens de Socialistische Partij (SP) was hij Kamerlid"), "match")
        self.assertEqual(compare_employer("SP", "Socialistische Partij",
                                          "De Socialistische Partij en elders een SP-brief"), "absent")
        self.assertEqual(compare_employer("Bouwman Makelaars", "Jaëlroh B.V.",
                                          "Albert Jansen bestuurde Jaëlroh B.V."), "absent")

    def test_conflict_always_wins(self):
        self.assertEqual(decide_tier(card(name="full", city="match", employer="match", age="conflict"))[0], "unrelated")

    def test_strong_match_rules(self):
        self.assertEqual(decide_tier(card(name="full", city="match", employer="match"))[:2], ("confirmed", 3))
        self.assertEqual(decide_tier(card(name="full", city="match", age="match"))[:2], ("confirmed", 3))
        self.assertEqual(decide_tier(card(name="full", city="match"))[:2], ("possible", 2))
        self.assertEqual(decide_tier(card(name="partial", city="match", age="match"))[:2], ("possible", 2))
        self.assertEqual(decide_tier(card(name="partial", city="match", age="match", employer="match"))[:2], ("confirmed", 3))
        self.assertEqual(decide_tier(card(name="full"))[:2], ("possible", 1))
        self.assertEqual(decide_tier(card())[:2], ("unrelated", 0))


EU_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<export xmlns="http://eu.europa.ec/fpi/fsd/export">
 <sanctionEntity euReferenceNumber="EU.1.1">
  <regulation programme="TEST"><publicationUrl>https://eur-lex.example/1</publicationUrl></regulation>
  <subjectType code="person"/>
  <nameAlias wholeName="Alex Jansen"/><nameAlias wholeName="A. J. Alias"/>
  <birthdate year="1972"/>
 </sanctionEntity>
 <sanctionEntity euReferenceNumber="EU.2.2"><subjectType code="enterprise"/><nameAlias wholeName="Alex Jansen BV"/></sanctionEntity>
</export>"""


def ods(rows):
    cells = lambda row: "".join(
        f"<table:table-cell><text:p>{c}</text:p></table:table-cell>" if c else "<table:table-cell/>" for c in row)
    content = ('<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
               'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
               'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><table:table>'
               + "".join(f"<table:table-row>{cells(r)}</table:table-row>" for r in rows)
               + "</table:table></office:body></office:document-content>")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("content.xml", content)
    return buffer.getvalue()


class SanctionsTests(unittest.TestCase):
    def test_eu_list_keeps_people_only(self):
        entries = sanctions.parse_eu(EU_XML)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["birth_years"], [1972])

    def test_dutch_list_handles_empty_cells(self):
        entries = sanctions.parse_nl(ods([
            ["Personen en organisaties"], [],
            ["Achternaam", "Voornaam/namen", "Alias", "Geboortedatum (DD-MM-JJJJ)", "Geboorteplaats", "Datum", "Link"],
            ["Jansen", "Alex", "", "10-10-1980", "Utrecht", "1-1-2020", "Stcrt 1"],
        ]))
        self.assertEqual(entries[0]["names"], ["Alex Jansen"])
        self.assertEqual(entries[0]["birth_years"], [1980])

    def test_birth_year_decides_a_name_match(self):
        entries = sanctions.parse_eu(EU_XML)
        self.assertEqual(sanctions.match_entries(entries, "Alex Jansen", 1972)[0]["identity"], "confirmed")
        self.assertEqual(sanctions.match_entries(entries, "Alex Jansen", 1990)[0]["identity"], "unrelated")
        self.assertEqual(sanctions.match_entries(entries, "Alex Jansen", None)[0]["identity"], "possible")
        self.assertEqual(sanctions.match_entries(entries, "Maria Peters", None), [])


BIG_XML = b"""<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>
<ListHcpApprox4Result xmlns="http://services.cibg.nl/ExternalUser"><ListHcpApprox><ListHcpApprox4>
 <BirthSurname>Jansen</BirthSurname><MailingName>A. Jansen</MailingName><Initial>A.</Initial>
 <WorkAddress1><City>Utrecht</City><CountryCode>528</CountryCode></WorkAddress1>
 <ArticleRegistration><ArticleRegistrationExtApp><ArticleRegistrationNumber>123</ArticleRegistrationNumber></ArticleRegistrationExtApp></ArticleRegistration>
 <JudgmentProvision><JudgmentProvisionExtApp><PublicDescription>Berisping</PublicDescription><Public>true</Public></JudgmentProvisionExtApp></JudgmentProvision>
</ListHcpApprox4></ListHcpApprox></ListHcpApprox4Result></soap:Body></soap:Envelope>"""


class BigRegisterTests(unittest.TestCase):
    def test_measures_and_city_are_read(self):
        records = big_register.parse_response(BIG_XML)
        self.assertEqual(records[0]["measures"], ["Berisping"])
        hits = big_register.assess_records(records, "Alex Jansen", "Utrecht")
        self.assertEqual(hits[0]["identity"], "confirmed")
        self.assertEqual(big_register.assess_records(records, "Alex Jansen", "Zwolle")[0]["identity"], "possible")
        self.assertEqual(big_register.assess_records(records, "Bram Jansen", "Utrecht"), [])


if __name__ == "__main__":
    unittest.main()
