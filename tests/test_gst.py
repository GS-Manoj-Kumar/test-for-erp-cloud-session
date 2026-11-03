from cabinet_erp.utils.gst import STATES, gstin_error, normalize_gstin, state_from_gstin


def test_valid_gstins():
    for g in ["27AAPFU0939F1ZV", "29AAGCB7383J1Z4", "24AAACC1206D1ZM"]:
        assert gstin_error(g) is None, g


def test_lowercase_and_spaces_normalised():
    assert normalize_gstin(" 27aapfu0939f1zv ") == "27AAPFU0939F1ZV"
    assert gstin_error(" 27aapfu0939f1zv ") is None


def test_wrong_length():
    assert "15 characters" in gstin_error("27AAPFU0939F1Z")


def test_bad_format():
    assert "format" in gstin_error("27AAPFU0939F1AV")


def test_bad_check_digit():
    assert "check digit" in gstin_error("27AAPFU0939F1ZX")


def test_unknown_state_code():
    assert "state code" in gstin_error("99AAPFU0939F1ZV")


def test_state_from_gstin():
    assert state_from_gstin("27AAPFU0939F1ZV") == "Maharashtra"
    assert state_from_gstin("29AAGCB7383J1Z4") == "Karnataka"
    assert "Karnataka" in STATES
