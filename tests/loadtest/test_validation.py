import copy
import hashlib
import unittest

from loadtest.validation import download, file_metadata, listing, verification

CONTENT = b"fixture content"
FIXTURE = {"id": "b1d620d5-df18-4165-bd20-a6b1b2bb3f12", "size": len(CONTENT),
           "sha256": hashlib.sha256(CONTENT).hexdigest()}


def good_verification():
    return {"id": FIXTURE["id"], "intact": True, "expected_sha256": FIXTURE["sha256"],
            "actual_sha256": FIXTURE["sha256"], "expected_size": len(CONTENT), "actual_size": len(CONTENT)}


class ValidationTests(unittest.TestCase):
    def test_valid_fixture_and_responses(self):
        self.assertEqual(listing([FIXTURE], True)[0], FIXTURE)
        verification(good_verification(), FIXTURE)
        download(CONTENT, FIXTURE)

    def test_empty_fixture_is_an_error_but_empty_list_is_valid(self):
        self.assertEqual(listing([]), [])
        with self.assertRaisesRegex(ValueError, "No fixture"):
            listing([], True)

    def test_list_must_be_array(self):
        with self.assertRaises(ValueError):
            listing({"detail": "error"})

    def test_invalid_metadata(self):
        for key, value in [("id", "bad"), ("sha256", "xyz"), ("size", -1), ("size", True), ("size", "15")]:
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    file_metadata({**FIXTURE, key: value})

    def test_false_or_truthy_string_is_not_integrity_success(self):
        for value in [False, "true", 1, None]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "intact"):
                    verification({**good_verification(), "intact": value}, FIXTURE)

    def test_wrong_file_id(self):
        value = good_verification()
        value["id"] = "00000000-0000-4000-8000-000000000000"
        with self.assertRaisesRegex(ValueError, "file ID"):
            verification(value, FIXTURE)

    def test_wrong_hash_even_when_intact_is_true(self):
        for key in ["expected_sha256", "actual_sha256"]:
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "hash"):
                    verification({**good_verification(), key: "0" * 64}, FIXTURE)

    def test_wrong_or_missing_size(self):
        for key in ["expected_size", "actual_size"]:
            for replacement in [0, True, None]:
                with self.subTest(key=key, replacement=replacement):
                    with self.assertRaisesRegex(ValueError, "size"):
                        verification({**good_verification(), key: replacement}, FIXTURE)

    def test_same_size_corruption_is_detected(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            download(b"X" * len(CONTENT), FIXTURE)

    def test_truncated_download_is_detected(self):
        with self.assertRaisesRegex(ValueError, "size"):
            download(CONTENT[:-1], FIXTURE)

    def test_empty_file_is_valid(self):
        download(b"", {**FIXTURE, "size": 0, "sha256": hashlib.sha256(b"").hexdigest()})

    def test_validators_do_not_change_fixture(self):
        before = copy.deepcopy(FIXTURE)
        verification(good_verification(), FIXTURE)
        download(CONTENT, FIXTURE)
        self.assertEqual(FIXTURE, before)


if __name__ == "__main__":
    unittest.main()
