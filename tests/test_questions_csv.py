from pathlib import Path

import pytest

from app.questions_csv import normalize_answer, parse_csv_bytes, parse_csv_text

HEADER = "question_id,question_content,question_cn_content,A,B,C,D,true_answer,CN_A,CN_B,CN_C,CN_D,detail_explain\r\n"


def test_sample_file_parses_without_errors():
    data = (Path(__file__).parent.parent / "data" / "questions.csv").read_bytes()
    result = parse_csv_bytes(data)
    assert result.errors == []
    assert len(result.questions) >= 3


def test_bom_is_removed():
    data = ("﻿" + HEADER + "001,Q,題目,(A)a,(B)b,(C)c,(D)d,B,,,,,\r\n").encode("utf-8")
    result = parse_csv_bytes(data)
    assert result.errors == []
    assert result.questions[0]["question_id"] == "001"


def test_comma_and_newline_inside_quotes():
    text = HEADER + '001,"Pick one, please","第一行\n第二行",a,"b, with comma",c,d,B,,,,,"line1\nline2"\r\n'
    q = parse_csv_text(text).questions[0]
    assert q["question_en"] == "Pick one, please"
    assert q["question_cn"] == "第一行\n第二行"
    assert q["options"][1] == {"key": "B", "en": "b, with comma", "cn": ""}
    assert q["explanation"] == "line1\nline2"


def test_option_prefix_is_stripped_and_values_trimmed():
    text = HEADER + "001, Q ,,(A)1 TB ,(B) 50 GB,(C)5 GB,(D)100 GB, d ,(A)一,,,,\r\n"
    q = parse_csv_text(text).questions[0]
    assert q["question_en"] == "Q"
    assert [o["en"] for o in q["options"]] == ["1 TB", "50 GB", "5 GB", "100 GB"]
    assert q["options"][0]["cn"] == "一"
    assert q["answer"] == "D"


def test_extra_options_e_and_f():
    header = "question_id,question_content,question_cn_content,A,B,C,D,E,F,true_answer,CN_E,CN_F\r\n"
    text = header + "001,Q,,a,b,c,d,e,f,\"E, C\",五,六\r\n" + "002,Q,,a,b,c,,,,A,,\r\n"
    result = parse_csv_text(text)
    assert result.errors == []
    first, second = result.questions
    assert [o["key"] for o in first["options"]] == ["A", "B", "C", "D", "E", "F"]
    assert first["options"][4] == {"key": "E", "en": "e", "cn": "五"}
    assert first["answer"] == "CE"
    # 空的選項不保留
    assert [o["key"] for o in second["options"]] == ["A", "B", "C"]


def test_bad_rows_are_skipped_and_reported():
    text = (
        HEADER
        + "001,Q,,a,b,c,d,A,,,,,\r\n"       # 正常
        + ",Q,,a,b,c,d,A,,,,,\r\n"          # 缺題號
        + "003,,,a,b,c,d,A,,,,,\r\n"        # 缺題目
        + "004,Q,,a,b,c,d,X,,,,,\r\n"       # 答案不是選項
        + "005,Q,,a,b,c,,D,,,,,\r\n"        # 答案是空的選項
        + "006,Q,,a,,,,A,,,,,\r\n"          # 選項不到兩個
        + "007,Q,,a,b,c,d,A,,,,,,extra\r\n"  # 多出欄位（逗號沒用雙引號包起來）
        + "a/b,Q,,a,b,c,d,A,,,,,\r\n"       # 題號含斜線
        + "009,Q,,a,b,c,d,B,,,,,\r\n"       # 正常
    )
    result = parse_csv_text(text)
    assert [q["question_id"] for q in result.questions] == ["001", "009"]
    assert [e.line for e in result.errors] == [3, 4, 5, 6, 7, 8, 9]


def test_missing_required_column_raises():
    with pytest.raises(ValueError, match="true_answer"):
        parse_csv_text("question_id,question_content,question_cn_content,A,B\r\n001,Q,,a,b\r\n")


def test_header_whitespace_is_tolerated():
    text = " question_id , question_content ,question_cn_content,A,B,true_answer\r\n001,Q,,a,b,B\r\n"
    assert parse_csv_text(text).questions[0]["answer"] == "B"


@pytest.mark.parametrize("raw, expected", [
    ("d", "D"), ("A,C", "AC"), ("C, A", "AC"), ("EC", "CE"), ("", ""), ("1", ""), ("A-B", ""),
])
def test_normalize_answer(raw, expected):
    assert normalize_answer(raw) == expected
