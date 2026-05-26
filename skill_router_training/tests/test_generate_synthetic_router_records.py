import unittest

from skill_router_training.scripts.generate_synthetic_router_records import (
    normalize_records,
    parse_json_array,
)


class GenerateSyntheticRouterRecordsTest(unittest.TestCase):
    def test_parse_plain_json_array(self):
        records = parse_json_array('[{"user_message":"a"},{"user_message":"b"}]')

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["user_message"], "a")

    def test_parse_fenced_json_array(self):
        records = parse_json_array('```json\n[{"user_message":"a"}]\n```')

        self.assertEqual(records, [{"user_message": "a"}])

    def test_parse_object_with_records_key(self):
        records = normalize_records({"records": [{"user_message": "a"}]})

        self.assertEqual(records, [{"user_message": "a"}])


if __name__ == "__main__":
    unittest.main()
