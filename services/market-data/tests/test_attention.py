"""공시 분류 (네트워크 없이)."""
from datetime import date

from collectors import classify_report


def test_classify_report():
    assert classify_report("분기보고서 (2026.06)") == "실적"
    assert classify_report("연결재무제표기준영업(잠정)실적(공정공시)") == "실적"
    assert classify_report("단일판매ㆍ공급계약체결") == "계약"
    assert classify_report("유상증자결정") == "자금조달"
    assert classify_report("주요사항보고서(자기주식취득결정)") == "주요사항"
    assert classify_report("임원ㆍ주요주주특정증권등소유상황보고서") == "지분"
    assert classify_report("기업설명회(IR)개최(안내공시)") == "기타"

